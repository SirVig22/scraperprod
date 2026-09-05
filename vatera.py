import paho.mqtt.client as mqtt
import re
import os
import json
from bs4 import BeautifulSoup
import sys
import uuid
import time
import signal

base_dir = os.path.dirname(os.path.abspath(__file__))
client = mqtt.Client(client_id=f"vatera-{uuid.uuid4()}")
valid_listing_html = []

SEEN_FILE = os.path.join(base_dir, 'data', 'seen_ads.json')
BASE_STUFF = os.path.join(base_dir, 'data', 'basestuff.json')
WHITE_LIST = os.path.join(base_dir, 'data', 'white_list.json')
BLACK_LIST = os.path.join(base_dir, 'data', 'black_list.json')
PRICE_FILE = os.path.join(base_dir, 'data', 'price_ranges.json')

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

white_list = exrtData(WHITE_LIST, [])
blacklist_search_words = exrtData(BLACK_LIST, [])
blacklist_lowercase_words = [w.lower() for w in blacklist_search_words]
lowercase_words = [w.lower() for w in white_list]

def extract_title(div):
        a = div.find("a")
        if not a:
            return "None"

        candidates = []

        text = a.get_text(strip=True)
        if text:
            candidates.append(text)

        for attr in ("title", "aria-label"):
            if a.get(attr):
                candidates.append(a[attr])

        img = a.find("img")
        if img and img.get("alt"):
            candidates.append(img["alt"])

        if not candidates:
            return "None"

        for candidate in candidates:
            lower = candidate.lower()

            if lowercase_words and not any(w in lower for w in lowercase_words):
                continue

            if any(w in lower for w in blacklist_lowercase_words):
                continue

            return candidate

        return "None"

def extract_price(div):
    selectors = [
        '[data-testid*="price"]',
        '.uad-price',
        ".ar",
        None 
    ]

    for selector in selectors:
        if selector:
            price_container = div.select_one(selector)
            if not price_container:
                continue
            text = price_container.get_text(" ", strip=True)
        else:
            text = div.get_text(" ", strip=True)

        match = re.search(r'(\d[\d\s\xa0]*)\s*Ft\b', text)
        if match:
            number_clean = int(re.sub(r"[^\d]", "", match.group(1)))
            return str(number_clean)

    return None

def extract_link(div):
    a = div.find("a")
    return a["href"] if a and a.get("href") else "None"

def on_connect(client, userdata, flags, rc):
    client.subscribe("router/vatera/raw")
    client.subscribe("kill/vatera")
    client.publish("status", "vatera")

def close_conn():
    client.disconnect()
    time.sleep(0.1)
    os.kill(os.getpid(), signal.SIGTERM)

def on_message(client, userdata, msg):
    if msg.topic == "kill/vatera":
        close_conn()
        return

    client.publish("status", "vatera")

    soup = BeautifulSoup(msg.payload.decode("utf-8"), "html.parser")
    valid_listing_html.append({
        "title": extract_title(soup),
        "price": extract_price(soup),
        "link": extract_link(soup),
    })

    for item in valid_listing_html:
        client.publish("router/filter", str(item))

client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883)

client.loop_forever()
