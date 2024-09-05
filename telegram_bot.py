from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from pysnmp.hlapi import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
from dotenv import load_dotenv
import os
import re
import json

# Carrega as variáveis do arquivo .env
load_dotenv()

# Obtém o token do ambiente
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    raise ValueError("O token do bot não foi encontrado. Verifique seu arquivo .env.")


# Dicionário com IPs das impressoras, seus respectivos locais e NID
# Load printers from an external JSON file
with open('printers.json', 'r') as file:
    printers = json.load(file)


# OID para o contador de páginas (verifique a OID correta para sua impressora)
page_counter_oid = '1.3.6.1.2.1.43.10.2.1.4.1.1'  # Exemplo comum, pode variar de acordo com a MIB da impressora

def get_snmp_data(ip, oid):
    """Função para coletar dados SNMP de uma impressora Samsung."""
    try:
        iterator = getCmd(
            SnmpEngine(),
            CommunityData('public', mpModel=0),  # Utilize a comunidade correta ('public' é padrão para leitura)
            UdpTransportTarget((ip, 161)),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )

        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

        if errorIndication:
            print(f"Erro na impressora {ip}: {errorIndication}")
            return None
        elif errorStatus:
            print(f"Erro no status SNMP na impressora {ip} - {errorStatus.prettyPrint()}")
            return None
        else:
            for varBind in varBinds:
                return varBind[1]  # Retorna o valor da OID
    except Exception as e:
        print(f"Falha ao conectar com a impressora {ip}: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Olá! Envie "/contadores" para executar a busca por contadores das impressoras. /contador ip:<ip> ou /contador nid:<NID> para uma impressora específica. Exemplo: /contadores ip:192.168.0.222 ou /contadores nid:1234')

async def contadores(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        for ip, (location, nid) in printers.items():
            contador = get_snmp_data(ip, page_counter_oid)
            if contador is not None:
                print(f"{location} ({ip}, NID: {nid}) - Contador: {contador}")
                await update.message.reply_text(f"{location} ({ip}, NID: {nid}) - Contador: {contador}")
            else:
                await update.message.reply_text(f"Não foi possível obter o contador para a impressora em {location} ({ip}, NID: {nid})")
    except Exception as e:
        await update.message.reply_text(f'Ocorreu um erro ao executar o comando: {e}')

async def contador(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Extract the IP or NID from the command
        match_ip = re.search(r'ip:(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', update.message.text)
        match_nid = re.search(r'NID:(\d+)', update.message.text)

        if match_ip:
            ip = match_ip.group(1)
            if ip in printers:
                location, nid = printers[ip]
                contador = get_snmp_data(ip, page_counter_oid)
                if contador is not None:
                    print(f"{location} ({ip}, NID: {nid}) - Contador: {contador}")
                    await update.message.reply_text(f"{location} ({ip}, NID: {nid}) - Contador: {contador}")
                else:
                    await update.message.reply_text(f"Não foi possível obter o contador para a impressora em {location} ({ip}, NID: {nid})")
            else:
                await update.message.reply_text(f"IP {ip} não encontrado na lista de impressoras.")
        elif match_nid:
            nid = match_nid.group(1)

            # Find the printer with the matching NID
            matching_printers = {ip: (location, printer_nid) for ip, (location, printer_nid) in printers.items() if printer_nid == nid}

            if matching_printers:
                ip, (location, _) = next(iter(matching_printers.items()))
                contador = get_snmp_data(ip, page_counter_oid)
                if contador is not None:
                    print(f"{location} ({ip}, NID: {nid}) - Contador: {contador}")
                    await update.message.reply_text(f"{location} ({ip}, NID: {nid}) - Contador: {contador}")
                else:
                    await update.message.reply_text(f"Não foi possível obter o contador para a impressora em {location} ({ip}, NID: {nid})")
            else:
                await update.message.reply_text(f"NID {nid} não encontrado na lista de impressoras.")
        else:
            await update.message.reply_text("Comando inválido. Use '/contador ip:xxx.xxx.xxx.xxx' ou '/contador NID:xxxx'.")
    except Exception as e:
        await update.message.reply_text(f'Ocorreu um erro ao executar o comando: {e}')

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('contadores', contadores))
    # Adiciona o novo manipulador de comando
    application.add_handler(CommandHandler('contador', contador))

    application.run_polling()

if __name__ == '__main__':
    main()
