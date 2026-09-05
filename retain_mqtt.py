import paho.mqtt.client as mqtt
import asyncio
import time
import json
from threading import Lock
import subprocess
import os
import threading
import uuid

TIMEOUT = 120
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
lock = Lock()

agent_list = {
    "hardverapro": False,
    "jofogas": False,
    "vatera": False
}

agent_last_seen = {
    "hardverapro": 0,
    "jofogas": 0,
    "vatera": 0
}

client = mqtt.Client(client_id=f"retain_mqtt-{uuid.uuid4()}")

def run_agent(agent):
    print(f"Starting {agent}.py...")
    subprocess.Popen(["python", os.path.join(BASE_DIR, f"{agent}.py")])

def on_message(client, userdata, msg):
    data = msg.payload.decode().strip()

    if msg.topic == "status":
        with lock:
            if data in agent_list:
                agent_list[data] = True
                agent_last_seen[data] = time.time()

    elif msg.topic == "status/request":
        with lock:
            client.publish("report", str(agent_list))

    elif msg.topic == "restart":
        threading.Thread(target=run_agent, args=(data,), daemon=True).start()

async def timer():
    while True:
        now = time.time()
        with lock:
            for agent, last_seen in agent_last_seen.items():
                if last_seen is None:
                    continue
                if now - last_seen > TIMEOUT:
                    agent_list[agent] = False
        await asyncio.sleep(1)


async def main():
    asyncio.create_task(timer())
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, input, f"{__file__} running\n")

client.on_message = on_message
client.connect("localhost", 1883)
client.subscribe("status")
client.subscribe("status/request")
client.subscribe("restart")
client.loop_forever()
asyncio.run(main())