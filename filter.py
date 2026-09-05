import paho.mqtt.client as mqtt
import os
import json
import ast
import uuid

base_dir = os.path.dirname(os.path.abspath(__file__))
client = mqtt.Client(client_id=f"filter-{uuid.uuid4()}")

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
seen_ads = set(exrtData(SEEN_FILE, []))
base_stuff = exrtData(BASE_STUFF, [])
blacklist_search_words = exrtData(BLACK_LIST, [])
saved_price_ranges = exrtData(PRICE_FILE, [])

new_ads = []
ads_to_save = []
lowercase_words = [word.lower() for word in white_list]
blacklist_lowercase_words = [word.lower() for word in blacklist_search_words]

def on_message(client, userdata, msg):
    data = ast.literal_eval(msg.payload.decode("utf-8"))
    title, price, full_url = data["title"], data["price"], data["link"]


    # FILTERS
    if price == "Keresem":
        return
    if price == "None":
        return
    if price == None:
        return
    if full_url in seen_ads:
        return
    if not any(w in title.lower() for w in lowercase_words):
        return
    if any(w in title.lower() for w in blacklist_lowercase_words):
        return
        
    print(f"New ad found: {title} | {price} | {full_url}")
    ads_to_save.append(data)
    seen_ads.add(full_url)
    new_ads.append(full_url)
    client.publish(f"router/done", str(data))

    save_json(SEEN_FILE, list(seen_ads))


client.on_message = on_message
client.connect("localhost", 1883)
client.subscribe("router/filter")
client.loop_forever()