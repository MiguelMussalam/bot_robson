import os
from flask import Flask, jsonify, request
from mangum import Mangum
from asgiref.wsgi import WsgiToAsgi
from discord_interactions import verify_key_decorator
import json
from datetime import datetime
import pytz

DISCORD_PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY")

app = Flask(__name__)
asgi_app = WsgiToAsgi(app)
handler = Mangum(asgi_app)

FUSO_HORARIO = pytz.timezone('America/Sao_Paulo')

@app.route("/", methods=["POST"])
async def interactions():
    print(f"👉 Request: {request.json}")
    raw_request = request.json
    return interact(raw_request)


@verify_key_decorator(DISCORD_PUBLIC_KEY)
def interact(raw_request):
    if raw_request["type"] == 1:  # PING
        response_data = {"type": 1}  # PONG
    else:
        data = raw_request["data"]
        command_name = data["name"]

        if command_name == "adicionar-atividade":
            try:
                disciplina = next(opt for opt in data["options"] if opt["name"] == "disciplina")["value"]
                descricao = next(opt for opt in data["options"] if opt["name"] == "descricao")["value"]
                data_str = next(opt for opt in data["options"] if opt["name"] == "data")["value"]
                link = next(opt for opt in data["options"] if opt["name"] == "link")["value"]

                # Validação
                link = check_link(link)
                check_data(data_str)

                atividades = carregar_atividades()
                nova_atividade = {
                    'Disciplina': disciplina,
                    'Atividade': descricao,
                    'Data': data_str,
                    'Link': link
                }
                atividades.append(nova_atividade)
                salvar_atividades(atividades)

                message_content = (
                    f"✅ **Atividade adicionada com sucesso!**\n\n"
                    f"📌 **Disciplina:** {disciplina}\n"
                    f"📝 **Atividade:** {descricao}\n"
                    f"📅 **Data:** {data_str}\n"
                    f"🔗 **Link:** {link}\n"
                )

            except ValueError as e:
                message_content = f"❌ Erro: {str(e)}"
        elif command_name == "visualizar atividades":
            atividades = carregar_atividades()
            if not atividades:
                message_content = "📂 Não há atividades cadastradas no momento."
            else:
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
                message_content = mensagem

        response_data = {
            "type": 4,
            "data": {"content": message_content},
        }

    return jsonify(response_data)

def carregar_atividades():
    try:
        with open('atividades.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

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

def salvar_atividades(atividades):
    with open('/tmp/atividades.json', 'w', encoding='utf-8') as file:
        json.dump(atividades, file, ensure_ascii=False, indent=4)

def verificar_datas():
    atividades = carregar_atividades()
    atividades_removidas = False
    hoje = datetime.now(FUSO_HORARIO).date()
    mensagens = []

    for atividade in list(atividades):
        data_atividade = datetime.strptime(atividade['Data'], "%d/%m/%Y").date()
        dias_restantes = (data_atividade - hoje).days

        if dias_restantes <= 0:
            atividades.remove(atividade)
            atividades_removidas = True
            mensagens.append(
                f"🚫 Expirada: {atividade['Disciplina']} - {atividade['Atividade']}"
            )
        elif dias_restantes in [40, 30, 20, 15, 10, 5, 3, 1]:
            mensagens.append(
                f"⏰ {dias_restantes} dias - {atividade['Disciplina']}: {atividade['Atividade']}"
            )

    if atividades_removidas:
        salvar_atividades(atividades)

    return mensagens

if __name__ == "__main__":
    app.run(debug=True)