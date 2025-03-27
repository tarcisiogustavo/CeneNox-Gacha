import discord
from discord.ext import commands
from typing import Callable
import asyncio
import botoptions
import pyautogui
import settings
import json
import time
import discordbot
import stations.stations as station
import task_manager

intents = discord.Intents.default()
pyautogui.FAILSAFE = False
bot = commands.Bot(command_prefix=settings.command_prefix, intents=intents)

running_tasks = []

def load_json(json_file:str):
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []  

def save_json(json_file:str,data):
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=4)

async def wait_queue():
    log_channel = bot.get_channel(settings.log_wait_queue)
    last_position = 0
    while True:
        
        with open("txt_files/wait.txt","r") as file:
            file.seek(last_position)
            queue = file.read()
            if queue:
                await log_channel.purge()
                await log_channel.send(queue)
                last_position = file.tell()
        await asyncio.sleep(5)

async def active_queue():
    log_channel = bot.get_channel(settings.log_active_queue)
    last_position = 0
    while True:
        
        with open("txt_files/active.txt","r") as file:
            file.seek(last_position)
            queue = file.read()
            if queue:
                await log_channel.purge()
                await log_channel.send(queue)
                last_position = file.tell()
        await asyncio.sleep(5)

async def send_new_logs():
    log_channel = bot.get_channel(settings.log_channel_gacha)
    last_position = 0
    
    while True:
        with open("txt_files/logs.txt", 'r') as file:
            file.seek(last_position)
            new_logs = file.read()
            if new_logs:
                await log_channel.send(f"New logs:\n```{new_logs}```")
                last_position = file.tell()
        await asyncio.sleep(5)

@bot.tree.command(name="add_gacha", description="add a new gacha station to the data")

async def add_gacha(interaction: discord.Interaction, name: str, teleporter: str, resource_type: str ,direction: str):
    data = load_json("json_files/gacha.json")

    for entry in data:
        if entry["name"] == name:
            await interaction.response.send_message(f"a gacha station with the name '{name}' already exists", ephemeral=True)
            return
        
    new_entry = {
        "name": name,
        "teleporter": teleporter,
        "resource_type": resource_type,
        "side" : direction
    }
    data.append(new_entry)

    save_json("json_files/gacha.json",data)

    await interaction.response.send_message(f"added new gacha station: {name}")

@bot.tree.command(name="list_gacha", description="list all gacha stations")
async def list_gacha(interaction: discord.Interaction):

    data = load_json("json_files/gacha.json")
    if not data:
        await interaction.response.send_message("no gacha stations found", ephemeral=True)
        return


    response = "gacha Stations:\n"
    for entry in data:
        response += f"- **{entry['name']}**: teleporter `{entry['teleporter']}`, resource `{entry['resource_type']} gacha on the `{entry['side']}` side `\n"

    await interaction.response.send_message(response)


@bot.tree.command(name="add_pego", description="add a new pego station to the data")

async def add_pego(interaction: discord.Interaction, name: str, teleporter: str, delay: int):
    data = load_json("json_files/pego.json")

    for entry in data:
        if entry["name"] == name:
            await interaction.response.send_message(f"a pego station with the name '{name}' already exists", ephemeral=True)
            return
        
    new_entry = {
        "name": name,
        "teleporter": teleporter,
        "delay": delay
    }
    data.append(new_entry)

    save_json("json_files/pego.json",data)

    await interaction.response.send_message(f"added new pego station: {name}")

@bot.tree.command(name="list_pego", description="list all pego stations")
async def list_pego(interaction: discord.Interaction):

    data = load_json("json_files/pego.json")
    if not data:
        await interaction.response.send_message("no pego stations found", ephemeral=True)
        return


    response = "pego Stations:\n"
    for entry in data:
        response += f"- **{entry['name']}**: teleporter `{entry['teleporter']}`, delay `{entry['delay']}`\n"

    await interaction.response.send_message(response)

@bot.tree.command(name="pause", description="sends the bot back to render bed for X amount of seconds")
async def reset(interaction: discord.Interaction,time:int):
    task = task_manager.scheduler
    pause = station.pause(time)
    task.add_task(pause)
    await interaction.response.send_message(f"pause task added will now pause for {time} seconds once the next task finishes")
    
async def embed_send(queue_type):
    log_channel = 0
    if queue_type == "active_queue":
        log_channel = bot.get_channel(settings.log_active_queue)
    else:
        log_channel = bot.get_channel(settings.log_wait_queue)
    while True:
        embed_msg = await discordbot.embed_create(queue_type)
        await log_channel.purge()
        await log_channel.send(embed = embed_msg)
        await asyncio.sleep(5)

@bot.tree.command()
async def start(interaction: discord.Interaction):

    logchn = bot.get_channel(settings.log_channel_gacha) 
    if logchn:
        await logchn.send(f'bot starting up now')
    
    # resetting log files
    with open("txt_files/logs.txt", 'w') as file:
        file.write(f"")
    with open("txt_files/wait.txt", 'w') as wait:
        wait.write(f"")
    with open("txt_files/active.txt", 'w') as active:
        active.write(f"")
    running_tasks.append(bot.loop.create_task(send_new_logs()))
    
    
    await interaction.response.send_message(f"starting up bot now you have 5 seconds before start")
    time.sleep(5)
    running_tasks.append(asyncio.create_task(botoptions.task_manager_start()))
    running_tasks.append(bot.loop.create_task(embed_send("active_queue")))
    running_tasks.append(bot.loop.create_task(embed_send("waiting_queue")))
    
@bot.event
async def on_ready():
    await bot.tree.sync()
    
    logchn = bot.get_channel(settings.log_channel_gacha) 
    if logchn:
        await logchn.send(f'bot ready to start')
    print (f'logged in as {bot.user}')

api_key = settings.discord_api_key

if __name__ =="__main__":
    if len(settings.discord_api_key) < 4:
        print("you need to have a valid discord API key for the bot to run")
        print("please follow the instructions in the discord server to get your api key")
        exit()
    bot.run(api_key)