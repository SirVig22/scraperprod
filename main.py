import os
import subprocess
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS = [
    "broker.py",
    "bot.py",
    "filter.py",
    "vatera.py",
    "hardverapro.py",
    "jofogas.py",
    "retain_mqtt.py",
    "scraper.py"
]

def run_process(script):
    path = os.path.join(BASE_DIR, script)
    print(f"Starting {script}...")
    return subprocess.Popen(["python", path])

processes = []

for script in SCRIPTS:
    proc = run_process(script)
    processes.append(proc)
    time.sleep(1)

while True:
    time.sleep(5)
