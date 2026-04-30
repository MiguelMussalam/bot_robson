import os
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
from datetime import datetime, time
import pytz
import asyncio
import logging

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('bigas_droid')

#env
load_dotenv()

#config bot
TOKEN = os.getenv('TOKEN')
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

#pytz
FUSO_HORARIO = pytz.timezone('America/Sao_Paulo')
HORA_VERIFICACAO = time(hour=8, minute=0, tzinfo=FUSO_HORARIO)

# Lock global para evitar corrida
STATE_LOCK = asyncio.Lock()

# Função para carregar atividades do JSON
def carregar_atividades():
    try:
        with open('atividades.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

# Função para salvar atividades de forma atômica
def salvar_atividades(atividades, path='atividades.json'):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as file:
        json.dump(atividades, file, ensure_ascii=False, indent=4)
        file.flush()
        os.fsync(file.fileno())
    os.replace(tmp, path)

# Funções para disciplinas
def carregar_disciplinas():
    try:
        with open('disciplinas.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

def salvar_disciplinas(disciplinas, path='disciplinas.json'):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as file:
        json.dump(disciplinas, file, ensure_ascii=False, indent=4)
        file.flush()
        os.fsync(file.fileno())
    os.replace(tmp, path)

async def disciplina_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    disciplinas = carregar_disciplinas()
    return [app_commands.Choice(name=d, value=d) for d in disciplinas if current.lower() in d.lower()][:25]

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

@bot.event
async def on_ready():
    logger.info(f'Bot {bot.user} conectou com sucesso!')
    try:
        synced = await bot.tree.sync()
        logger.info(f"Comandos slash sincronizados: {len(synced)}")
    except Exception as e:
        logger.error(f"Erro ao sincronizar comandos: {e}")
    
    if not verificar_datas.is_running():
        verificar_datas.start()

@bot.tree.command(name="adicionar-atividade", description="adicione uma atividade para a lista de atividades. Formato de data: DD/MM/AAAA")
@app_commands.autocomplete(disciplina=disciplina_autocomplete)
async def adicionar_atividade(interaction: discord.Interaction, disciplina: str, descricao: str, data: str, link: str):
    try:
        link = check_link(link)  
        check_data(data)

        async with STATE_LOCK:
            atividades = carregar_atividades()
            nova_atividade = {
                'Disciplina': disciplina,
                'Atividade': descricao,
                'Data': data,
                'Link': link,
                'Check_dias_restantes': [40, 30, 20, 15, 10, 5, 3, 1]
            }
            atividades.append(nova_atividade)
            salvar_atividades(atividades)
            logger.info(f"Usuário {interaction.user} adicionou a atividade '{descricao}' para '{disciplina}'.")

        embed = discord.Embed(title="✅ Atividade adicionada com sucesso!", color=discord.Color.green())
        embed.add_field(name="Disciplina", value=disciplina, inline=False)
        embed.add_field(name="Atividade", value=descricao, inline=False)
        embed.add_field(name="Data", value=data, inline=False)
        if link != 'Sem link':
            embed.add_field(name="Link", value=f"[Acessar Link]({link})", inline=False)
        else:
            embed.add_field(name="Link", value="Sem link", inline=False)

        await interaction.response.send_message(embed=embed)
    except ValueError as e:
        await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)
        logger.warning(f"Usuário {interaction.user} tentou adicionar atividade com dados inválidos: {str(e)}")

@bot.tree.command(name="visualizar-atividades", description="Exibe todas as atividades salvas.")
async def visualizar_atividades(interaction: discord.Interaction):
    logger.info(f"Usuário {interaction.user} solicitou visualizar atividades.")
    async with STATE_LOCK:
        atividades = carregar_atividades()

    if not atividades:
        embed = discord.Embed(title="📂 Nenhuma atividade encontrada", description="Não há atividades cadastradas no momento.", color=discord.Color.light_grey())
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(title="📋 Lista de Atividades", color=discord.Color.blue())
    for i, atividade in enumerate(atividades):
        link_str = f"[Acessar]({atividade['Link']})" if atividade['Link'] != 'Sem link' else "Sem link"
        valor = f"**Atividade:** {atividade['Atividade']}\n**Data:** {atividade['Data']}\n**Link:** {link_str}"
        embed.add_field(name=f"ID: {i} | {atividade['Disciplina']}", value=valor, inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="remover-atividade", description="Remove uma atividade através do seu ID.")
async def remover_atividade(interaction: discord.Interaction, id_atividade: int):
    async with STATE_LOCK:
        atividades = carregar_atividades()
        
        if id_atividade < 0 or id_atividade >= len(atividades):
            await interaction.response.send_message("❌ **ID inválido.** Use `/visualizar-atividades` para conferir os IDs.", ephemeral=True)
            return
            
        removida = atividades.pop(id_atividade)
        salvar_atividades(atividades)
        logger.info(f"Usuário {interaction.user} removeu a atividade ID {id_atividade} ({removida['Disciplina']}).")
        
    embed = discord.Embed(title="🗑️ Atividade Removida", description=f"A atividade **{removida['Atividade']}** da disciplina **{removida['Disciplina']}** foi removida.", color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="editar-atividade", description="Edita os dados de uma atividade através do seu ID.")
@app_commands.autocomplete(disciplina=disciplina_autocomplete)
async def editar_atividade(interaction: discord.Interaction, id_atividade: int, disciplina: str = None, descricao: str = None, data: str = None, link: str = None):
    try:
        async with STATE_LOCK:
            atividades = carregar_atividades()
            
            if id_atividade < 0 or id_atividade >= len(atividades):
                await interaction.response.send_message("❌ **ID inválido.** Use `/visualizar-atividades` para conferir os IDs.", ephemeral=True)
                return
                
            atividade = atividades[id_atividade]
            
            if disciplina:
                atividade['Disciplina'] = disciplina
            if descricao:
                atividade['Atividade'] = descricao
            if data:
                check_data(data)
                atividade['Data'] = data
            if link:
                atividade['Link'] = check_link(link)
                
            salvar_atividades(atividades)
            logger.info(f"Usuário {interaction.user} editou a atividade ID {id_atividade}.")
            
        embed = discord.Embed(title="✏️ Atividade Atualizada", color=discord.Color.gold())
        embed.add_field(name="Disciplina", value=atividade['Disciplina'], inline=False)
        embed.add_field(name="Atividade", value=atividade['Atividade'], inline=False)
        embed.add_field(name="Data", value=atividade['Data'], inline=False)
        link_str = f"[Acessar]({atividade['Link']})" if atividade['Link'] != 'Sem link' else "Sem link"
        embed.add_field(name="Link", value=link_str, inline=False)
            
        await interaction.response.send_message(embed=embed)
    except ValueError as e:
        await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)

@bot.tree.command(name="adicionar-disciplina", description="Adiciona uma nova disciplina na base de dados para ser usada como categoria.")
async def adicionar_disciplina(interaction: discord.Interaction, nome: str):
    async with STATE_LOCK:
        disciplinas = carregar_disciplinas()
        if nome in disciplinas:
            await interaction.response.send_message(f"⚠️ A disciplina **{nome}** já existe!", ephemeral=True)
            return
            
        disciplinas.append(nome)
        salvar_disciplinas(disciplinas)
        
    logger.info(f"Usuário {interaction.user} adicionou a disciplina '{nome}'.")
    embed = discord.Embed(title="📚 Disciplina Adicionada", description=f"**{nome}** agora está disponível para seleção.", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="remover-disciplina", description="Remove uma disciplina da base de dados.")
@app_commands.autocomplete(nome=disciplina_autocomplete)
async def remover_disciplina(interaction: discord.Interaction, nome: str):
    async with STATE_LOCK:
        disciplinas = carregar_disciplinas()
        if nome not in disciplinas:
            await interaction.response.send_message(f"❌ A disciplina **{nome}** não foi encontrada.", ephemeral=True)
            return
            
        disciplinas.remove(nome)
        salvar_disciplinas(disciplinas)
        
    logger.info(f"Usuário {interaction.user} removeu a disciplina '{nome}'.")
    embed = discord.Embed(title="🗑️ Disciplina Removida", description=f"**{nome}** foi removida da lista.", color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="listar-disciplinas", description="Exibe todas as disciplinas cadastradas.")
async def listar_disciplinas(interaction: discord.Interaction):
    disciplinas = carregar_disciplinas()
    if not disciplinas:
        await interaction.response.send_message("📂 Nenhuma disciplina cadastrada.", ephemeral=True)
        return
        
    lista = "\n".join([f"• {d}" for d in disciplinas])
    embed = discord.Embed(title="📚 Disciplinas Disponíveis", description=lista, color=discord.Color.blue())
    await interaction.response.send_message(embed=embed)

@tasks.loop(time=HORA_VERIFICACAO)
async def verificar_datas():
    logger.info("Iniciando rotina diária de verificação de datas...")
    channel_id_str = os.getenv('CHANNEL_ID')
    if not channel_id_str:
        logger.warning("CHANNEL_ID não definido no arquivo .env. Lembretes automáticos não serão enviados.")
        return
    
    try:
        channel = bot.get_channel(int(channel_id_str))
    except ValueError:
        logger.error("CHANNEL_ID inválido. Deve ser um número numérico.")
        return

    hoje = datetime.now(FUSO_HORARIO).date()
    atividades_removidas = False
    modificadas = False

    async with STATE_LOCK:
        atividades = carregar_atividades()

        for atividade in list(atividades):
            try:
                data_atividade = datetime.strptime(atividade['Data'], "%d/%m/%Y").date()
            except ValueError:
                logger.error(f"Data inválida ignorada na atividade: {atividade['Disciplina']}")
                continue
                
            dias_restantes = (data_atividade - hoje).days
            logger.info(f"Verificando '{atividade['Disciplina']}': faltam {dias_restantes} dias.")
            
            if dias_restantes <= 0:
                atividades.remove(atividade)
                atividades_removidas = True
                if channel:
                    embed = discord.Embed(title="🚫 Atividade Expirada!", color=discord.Color.red())
                    embed.add_field(name="Disciplina", value=atividade['Disciplina'], inline=False)
                    embed.add_field(name="Atividade", value=atividade['Atividade'], inline=False)
                    await channel.send(embed=embed)
                continue

            if dias_restantes in atividade['Check_dias_restantes']:
                atividade['Check_dias_restantes'].remove(dias_restantes)
                modificadas = True

                if channel:
                    embed = discord.Embed(title="🚨 Lembrete de Atividade!", color=discord.Color.orange())
                    embed.add_field(name="Disciplina", value=atividade['Disciplina'], inline=False)
                    embed.add_field(name="Atividade", value=atividade['Atividade'], inline=False)
                    embed.add_field(name="Data", value=atividade['Data'], inline=False)
                    if atividade['Link'] != 'Sem link':
                        embed.add_field(name="Link", value=f"[Acessar Link]({atividade['Link']})", inline=False)
                    else:
                        embed.add_field(name="Link", value="Sem link", inline=False)
                    embed.set_footer(text=f"Faltam {dias_restantes} dias!")
                    await channel.send(embed=embed)

        if atividades_removidas or modificadas:
            salvar_atividades(atividades)
            logger.info("Base de dados de atividades (JSON) atualizada após verificação diária.")
        else:
            logger.info("Verificação diária concluída. Nenhuma modificação foi necessária.")

@verificar_datas.before_loop
async def before_verificar_datas():
    await bot.wait_until_ready()

bot.run(TOKEN)
