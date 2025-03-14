from dotenv import load_dotenv
import os
import discord

load_dotenv()
TOKEN = os.getenv('TOKEN')
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Bot {client.user} está online!')

@client.event
async def on_message(message):
    if message.content.startswith('!comando'):
        info = message.content.split(' ')[1]
        print(f'Informação recebida: {info}')
        await message.reply(f'Informação "{info}" recebida e armazenada!')

client.run(TOKEN)