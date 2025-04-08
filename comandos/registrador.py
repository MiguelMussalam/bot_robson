import os
import requests
import yaml
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
APPLICATION_ID = os.getenv("APPLICATION_ID")
BASE_URL = os.getenv("DISCORD_API_URL")
URL = f"{BASE_URL}/{APPLICATION_ID}/commands"

# Lê o YAML com os comandos
with open("comandos.yaml", "r", encoding="utf-8") as file:
    comandos_bot = yaml.safe_load(file)

headers = {
    "Authorization": f"Bot {TOKEN}",
    "Content-Type": "application/json"
}

for comando in comandos_bot:
    response = requests.post(URL, json=comando, headers=headers)
    print(f"[{comando['name']}] → {response.status_code} - {response.text}")
