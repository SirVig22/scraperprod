import subprocess
import time
import os

config_path = os.path.join(os.path.dirname(__file__), "mosquitto.conf")

broker = subprocess.Popen(["mosquitto", "-c", config_path])

print("Mosquitto broker running")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    broker.terminate()
    broker.wait()
