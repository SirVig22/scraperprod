import json
import requests
import re
import os
from bs4 import BeautifulSoup
from tqdm import tqdm
import time

#from markuplm_launch import load_model

#processor, model = load_model()

import paho.mqtt.client as mqtt

client = mqtt.Client()
client.connect("localhost", 1883)

base_dir = os.path.dirname(os.path.abspath(__file__))

SEEN_FILE = os.path.join(base_dir, 'data', 'seen_ads.json')
BASE_STUFF = os.path.join(base_dir, 'data', 'basestuff.json')
WHITE_LIST = os.path.join(base_dir, 'data', 'white_list.json')
BLACK_LIST = os.path.join(base_dir, 'data', 'black_list.json')
PRICE_FILE = os.path.join(base_dir, 'data', 'price_ranges.json')

AGENT_REGISTRY = {
    "vatera": {"vatera.hu"},
    "hardverapro": {"hardverapro.hu"},
    "jofogas": {"jofogas.hu"}
}

def exrtData(file, default):
    if os.path.exists(file):
        with open(file, "r") as basefile:
            return json.load(basefile)
    else:
        file = set()
        with open(file, "w") as basefile:
            json.dump(list(default), basefile)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def normalize_platform(url):
    for platform, domains in AGENT_REGISTRY.items():
        for domain in domains:
            if str(domain) in url:
                return platform
    return "none"

def get_details(website):
    base_link = base_stuff[website]["base_link"]
    base_offset = base_stuff[website]["base_offset"]
    increment_offset = base_stuff[website]["increment_offset"]

    return base_link, base_offset, increment_offset

def is_candidate_listing(div):
    text = div.get_text(" ", strip=True)
    has_price = re.search(r"(Ft|€|\$)", text)
    has_link = div.find("a") is not None
    has_image = div.find("img") is not None
    return has_price and has_link

def build_url(base_link, base_offset, offset, search, site):
    if site == "hardverapro":
        url = f"{base_link}{search}&minprice={saved_price_ranges[search]['min_price']}&maxprice={saved_price_ranges[search]['max_price']}{base_offset}{offset}"
    elif site == "jofogas":
        url = f"{base_link}{search}&max_price={saved_price_ranges[search]['max_price']}&min_price={saved_price_ranges[search]['min_price']}{base_offset}{offset}"
    elif site == "vatera":
        #https://www.vatera.hu/listings/index.php?q=Thinkpad&p=3&p1=0&p2=100000&tmpsb=Sz%C5%B1r%C3%A9s
        url = f"{base_link}q={search}{base_offset}{offset}&p1={saved_price_ranges[search]['min_price']}&p2={saved_price_ranges[search]['max_price']}&tmpsb=Sz%C5%B1r%C3%A9s"

    return url


white_list = exrtData(WHITE_LIST, [])
seen_ads = set(exrtData(SEEN_FILE, []))
base_stuff = exrtData(BASE_STUFF, [])
blacklist_search_words = exrtData(BLACK_LIST, [])
saved_price_ranges = exrtData(PRICE_FILE, [])

new_ads = []
ads_to_save = []
lowercase_words = [word.lower() for word in white_list]
blacklist_lowercase_words = [word.lower() for word in blacklist_search_words]
searches = base_stuff["searchstuff"]
max_pages = 2
i = 0

scrapers = [k for k in base_stuff.keys() if k != "searchstuff"]

print(scrapers)

# ===== Main loop =====
while True:
    scraper = scrapers[i]
    j = 0

    while j < len(searches):
        search = searches[j]
        offset = 1
        ads_counted = 0
        current_page = 0

        # Ask for price range if missing
        if search not in saved_price_ranges:
            print(f"Unset search found: {search}")
            min_price = int(input(f"Min price for {search}: "))
            max_price = int(input(f"Max price for {search}: "))
            saved_price_ranges[search] = {"min_price": min_price, "max_price": max_price}
            save_json(PRICE_FILE, saved_price_ranges)

        while True:

            base_link, base_offset, increment_offset = get_details(scraper)

            url = build_url(base_link, base_offset, offset, search, scraper)
            print(f"Scraping {scraper}: {url}")
            response = requests.get(url, timeout=15)
            soup = BeautifulSoup(response.text, "html.parser")

            candidate_divs = [d for d in soup.find_all("div") if is_candidate_listing(d)]
            print(f"[+] Found {len(candidate_divs)} candidate divs")

            valid_listing_html = []

            for div in tqdm(candidate_divs):
                try:
                    html = str(div)
                    valid_listing_html.append({
                        "html": html,
                    })

                except Exception as e:
                    print("Skipped div:", e)


            #print(f"\n[+] Valid listings: {len(valid_listing_html)}\n")

            for idx, item in enumerate(valid_listing_html[:len(valid_listing_html)], 1):
                #print(f"===== LISTING {idx} =====")
                time.sleep(0.1)
                agent = normalize_platform(url)
                client.publish(f"router/{agent}/raw", item["html"][:1500])
                #print("=" * 60)s
                ads_counted += 1

            if current_page < max_pages:
                if ads_counted >= increment_offset:
                    offset += increment_offset
                    ads_counted = 0
                    current_page += 1
                    continue
                break
            break
        j += 1
        i = (i + 1) % len(scrapers)