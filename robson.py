import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import json
from datetime import datetime
import pytz
import asyncio

#env
load_dotenv()

#config bot
TOKEN = os.getenv('TOKEN')
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
client = discord.Client(intents=intents)

#pytz
FUSO_HORARIO = pytz.timezone('America/Sao_Paulo')

# Função para carregar atividades do JSON
def carregar_atividades():
    try:
        with open('atividades.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

# Função para salvar atividades no JSON
def salvar_atividades(atividades):
    with open('atividades.json', 'w', encoding='utf-8') as file:
        json.dump(atividades, file, ensure_ascii=False, indent=4)

def check_link(link):
    if link == 'n':
        return 'Sem link'
    if not link.startswith("https"):
        raise ValueError(f'Link **{link}** inválido. Caso não queira enviar um link, digite **n**.')
    return link

def check_data(data):
    try:
        datetime.strptime(data, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError(f'data **{data}** inválida. Use o formato **DD/MM/AAAA** (ex: 23/03/2025).')

@client.event
@bot.event
async def on_ready():
    print(f'Bot {bot.user} está online!')
    try:
        # Sincroniza os comandos com o Discord
        synced = await bot.tree.sync()
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")
    
    bot.loop.create_task(verificar_datas())

@bot.tree.command(name="adicionar-atividade", description="adicione uma atividade para a lista de atividades. Formato de data: DD/MM/AAAA")
async def adicionar_atividade(interaction: discord.Interaction, disciplina: str, descricao: str, data: str, link: str):
    try:
        # Validação da entrada do usuário
        link = check_link(link)  
        check_data(data)

        atividades = carregar_atividades()

        # Criação da nova atividade
        nova_atividade = {
            'Disciplina': disciplina,
            'Atividade': descricao,
            'Data': data,
            'Link': link
        }

        # Salvando a atividade no JSON
        atividades.append(nova_atividade)
        salvar_atividades(atividades)

        # Confirmação para o usuário
        await interaction.response.send_message(
            f"✅ **Atividade adicionada com sucesso!**\n\n"
            f"📌 **Disciplina:** {disciplina}\n"
            f"📝 **Atividade:** {descricao}\n"
            f"📅 **Data:** {data}\n"
            f"🔗 **Link:** {link}\n"
        )
    except ValueError as e:
        await interaction.response.send_message(str(e))

@bot.tree.command(name="visualizar-atividades", description="Exibe todas as atividades salvas.")
async def visualizar_atividades(interaction: discord.Interaction):
    atividades = carregar_atividades()

    if not atividades:
        await interaction.response.send_message("📂 Não há atividades cadastradas no momento.")
        return
    
    mensagem = "**📋 Lista de Atividades:**\n\n"
    for i, atividade in enumerate(atividades):
        mensagem += (
            f"🔢 **ID:** {i}\n"
            f"📌 **Disciplina:** {atividade['Disciplina']}\n"
            f"📝 **Atividade:** {atividade['Atividade']}\n"
            f"📅 **Data:** {atividade['Data']}\n"
            f"🔗 **Link:** {atividade['Link']}\n"
            "------------------------\n"
        )

    await interaction.response.send_message(mensagem)

async def verificar_datas():
    await bot.wait_until_ready()
    while not bot.is_closed():
        atividades = carregar_atividades()
        atividades_removidas = False
        channel = bot.get_channel(1341729776897097728)

        hoje = datetime.now(FUSO_HORARIO).date()

        for atividade in list(atividades):
            data_atividade = datetime.strptime(atividade['Data'], "%d/%m/%Y").date()
            dias_restantes = (data_atividade - hoje).days
            print(dias_restantes)
            
            if dias_restantes <= 0:
                atividades.remove(atividade)
                atividades_removidas = True
                if channel:
                    await channel.send(
                        f"🚫 **Atividade expirada!** 🚫\n\n"
                        f"**Disciplina:** {atividade['Disciplina']}\n"
                        f"**Atividade**   {atividade['Atividade']}\n"
                    )
                continue

            if dias_restantes in [40, 30, 20, 15, 10, 5, 3, 1]:
                mensagem = (
                    f"🚨 **Lembrete de Atividade!**\n\n"
                    f"📌 **Disciplina:** {atividade['Disciplina']}\n"
                    f"📝 **Atividade:** {atividade['Atividade']}\n"
                    f"📅 **Data:** {atividade['Data']}\n"
                    f"🔗 **Link:** {atividade['Link']}\n"
                    f"⏳ **Faltam {dias_restantes} dias!**\n"
                )
                if channel:
                    await channel.send(mensagem)

        if atividades_removidas:
            salvar_atividades(atividades)
            print("JSON atualizado com atividades removidas.")

        await asyncio.sleep(86400)  # 86400 segundos = 24 horas

bot.run(TOKEN)