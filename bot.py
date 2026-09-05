import discord
from discord.ext import tasks, commands
import time
import asyncio
from discord.ext import tasks
import os
import json
import paho.mqtt.client as mqtt
import ast
import uuid
from dotenv import load_dotenv

load_dotenv()
base_dir = os.path.dirname(os.path.abspath(__file__))
SEEN_FILE = os.path.join(base_dir, 'data', 'seen_ads.json')

BOT = commands.Bot(command_prefix="!", intents=discord.Intents.all())
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")


known_agents = {"vatera", "hardverapro", "jofogas"}

agent_list = {}

start_time = time.time()

async def post_new_ad(details):
    channel = BOT.get_channel(1409826525821407313)
    if channel is None:
        print("Channel not found")
        return

    message = (
        "@everyone\n"
        "**New ad found!**\n"
        f"**Title:** {details['title']}\n"
        f"**Price:** {details['price']} Ft\n"
        f"**Link:** {details['link']}"
    )

    await channel.send(message)


def on_message(client, userdata, msg):
    global agent_list
    print("Received:", msg.topic, msg.payload.decode("utf-8"))
    if msg.topic == "report":
        agent_list = ast.literal_eval(msg.payload.decode("utf-8"))
        return

    data = ast.literal_eval(msg.payload.decode("utf-8"))
    asyncio.run_coroutine_threadsafe(
        post_new_ad(data),
        BOT.loop
    )


MQTTclient = mqtt.Client(client_id=f"dcbot-{uuid.uuid4()}")
MQTTclient.on_message = on_message

MQTTclient.connect("localhost", 1883)
MQTTclient.subscribe("router/done")
MQTTclient.subscribe("report")
MQTTclient.loop_start()

#EVENTS
@BOT.event
async def on_ready():
    print(f"Logged in as {BOT.user}")
    channel_id = 1409826525821407313
    channel = BOT.get_channel(channel_id)
    if channel:
        await channel.send("Online!")
    else:
        print("Channel was not found")

#COMMANDS
@BOT.command()
async def uptime(ctx):
    uptime = int(time.time() - start_time)
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    await ctx.send(f"Uptime: {hours}h {minutes}m {seconds}s")

@BOT.command()
async def wipelinks(ctx):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list([]), f, ensure_ascii=False, indent=2)
    
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as file:
            seen_ads = json.load(file)
    
    await ctx.send(f"Wiped, JSON Content: {seen_ads}")

@BOT.command()
async def ping(ctx):
    await ctx.send("@everyone :money_mouth:")

@BOT.command()
async def status(ctx):
    MQTTclient.publish("status/request", "ping")
    await asyncio.sleep(0.5)

    for agent, is_online in agent_list.items():
        if is_online:
            await ctx.send(f"🟢 {agent} is ONLINE")
        else:
            await ctx.send(f"🔴 {agent} is OFFLINE")


@BOT.command()
async def kill(ctx, agent: str):
    if agent not in known_agents:
        await ctx.send(f"Couldn't terminate: {agent} agent, check if it exists")
        return

    MQTTclient.publish(f"kill/{agent}", "kill")
    await ctx.send(f"{agent} terminated")

@BOT.command()
#@commands.has_role("Admin")
async def restart(ctx, agent: str):
    if agent not in known_agents:
        await ctx.send(f"Couldn't terminate: {agent} agent, check if it exists")
        return
    
    MQTTclient.publish(f"restart", f"{agent}")
    await ctx.send(f"Restarting {agent}...")


#START
async def start_servers():
    await BOT.start("MTQwOTg4NDY3NDk4OTIyODE3Mw.G5Qzit.FB3TQga6fKU6PTnXKtYZA-GKQqJsNydlWAwKc0")

asyncio.run(start_servers())