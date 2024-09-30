import os
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity
from aiohttp import web
from dotenv import load_dotenv
import json
import re
from pysnmp.hlapi import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity

# Carrega as variáveis do arquivo .env
load_dotenv()

# Obtém as credenciais do bot registradas no Azure
APP_ID = os.getenv("MICROSOFT_APP_ID")
APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD")

# Carregar as impressoras do arquivo JSON
with open('printers.json', 'r') as file:
    printers = json.load(file)

page_counter_oid = '1.3.6.1.2.1.43.10.2.1.4.1.1'  # OID do contador de páginas

# Configuração do bot
settings = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
adapter = BotFrameworkAdapter(settings)

# Lista global para armazenar impressoras com erro
impressoras_com_erro = []

async def handle_messages(request: web.Request) -> web.Response:
    """Recebe mensagens do Teams e processa."""
    body = await request.json()
    activity = Activity().deserialize(body)
    auth_header = request.headers["Authorization"] if "Authorization" in request.headers else ""

    async def aux_func(turn_context: TurnContext):
        # Identificar a mensagem recebida e responder de acordo
        if activity.text.startswith("/contadores"):
            await contadores(turn_context)
        elif activity.text.startswith("/contador"):
            await contador(turn_context)
        else:
            await turn_context.send_activity("Comando não reconhecido. Use /contadores ou /contador.")

    await adapter.process_activity(activity, auth_header, aux_func)
    return web.Response(status=200)

# Funções para manipular impressoras (equivalentes às que você tem)
async def contadores(turn_context: TurnContext):
    try:
        for ip, (location, nid) in printers.items():
            contador = get_snmp_data(ip, page_counter_oid)
            if contador is not None:
                await turn_context.send_activity(f"{location} ({ip}, NID: {nid}) - Contador: {contador}")
            else:
                impressoras_com_erro.append(ip)
                await turn_context.send_activity(f"Erro ao obter o contador da impressora em {location} ({ip}, NID: {nid})")
    except Exception as e:
        await turn_context.send_activity(f"Ocorreu um erro: {e}")

async def contador(turn_context: TurnContext):
    message_text = turn_context.activity.text
    match_ip = re.search(r'ip:(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', message_text)
    match_nid = re.search(r'NID:(\d+)', message_text)

    try:
        if match_ip:
            ip = match_ip.group(1)
            if ip in printers:
                location, nid = printers[ip]
                contador = get_snmp_data(ip, page_counter_oid)
                if contador is not None:
                    await turn_context.send_activity(f"{location} ({ip}, NID: {nid}) - Contador: {contador}")
                else:
                    impressoras_com_erro.append(ip)
                    await turn_context.send_activity(f"Erro ao obter o contador da impressora em {location} ({ip}, NID: {nid})")
            else:
                await turn_context.send_activity(f"IP {ip} não encontrado.")
        elif match_nid:
            nid = match_nid.group(1)
            matching_printers = {ip: (location, printer_nid) for ip, (location, printer_nid) in printers.items() if printer_nid == nid}
            if matching_printers:
                ip, (location, _) = next(iter(matching_printers.items()))
                contador = get_snmp_data(ip, page_counter_oid)
                if contador is not None:
                    await turn_context.send_activity(f"{location} ({ip}, NID: {nid}) - Contador: {contador}")
                else:
                    impressoras_com_erro.append(ip)
                    await turn_context.send_activity(f"Erro ao obter o contador da impressora em {location} ({ip}, NID: {nid})")
            else:
                await turn_context.send_activity(f"NID {nid} não encontrado.")
        else:
            await turn_context.send_activity("Comando inválido. Use '/contador ip:<IP>' ou '/contador NID:<NID>'.")
    except Exception as e:
        await turn_context.send_activity(f"Ocorreu um erro: {e}")

def get_snmp_data(ip, oid):
    """Função para coletar dados SNMP da impressora."""
    try:
        iterator = getCmd(
            SnmpEngine(),
            CommunityData('public', mpModel=0),
            UdpTransportTarget((ip, 161)),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        if errorIndication:
            return None
        elif errorStatus:
            return None
        else:
            for varBind in varBinds:
                return varBind[1]
    except Exception:
        return None

# Configuração do servidor
app = web.Application()
app.router.add_post("/api/messages", handle_messages)

if __name__ == "__main__":
    web.run_app(app, host="localhost", port=3978)
