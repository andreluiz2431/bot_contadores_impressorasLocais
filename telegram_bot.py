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
    """Mensagem de boas-vindas e instruções sobre os comandos disponíveis."""
    await update.message.reply_text(
        "Olá! Bem-vindo ao bot de gerenciamento de impressoras. Aqui estão os comandos disponíveis:\n\n"
        "/contadores - Mostra os contadores de todas as impressoras.\n"
        "/contador ip:<IP> - Mostra o contador de uma impressora específica com o endereço IP informado. Exemplo: /contador ip:192.168.0.222\n"
        "/contador NID:<NID> - Mostra o contador de uma impressora específica com o NID informado. Exemplo: /contador NID:1234\n\n"
        "**Atualizações de Impressoras:**\n"
        "/atualizarNID NID:<NID_ATUAL> PARA:<NOVO_NID> - Atualiza o NID de uma impressora. Exemplo: /atualizarNID NID:1234 PARA:5678\n"
        "/atualizarIP NID:<NID> PARA_IP:<NOVO_IP> - Atualiza o IP de uma impressora. Exemplo: /atualizarIP NID:1234 PARA_IP:192.168.0.123\n"
        "/atualizarSetor NID:<NID> PARA_SETOR:<NOVO_SETOR> - Atualiza o setor de uma impressora. Exemplo: /atualizarSetor NID:1234 PARA_SETOR:Novo Setor\n"
    )
    
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

async def atualizar_nid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Usa expressão regular para capturar os valores YYYY (NID atual) e XXXX (novo NID)
        match = re.search(r'NID:(\d+)\s+PARA:(\d+)', update.message.text)
        if match:
            old_nid = match.group(1)  # NID atual
            new_nid = match.group(2)  # Novo NID
            
            # Encontrar a impressora correspondente ao NID atual
            matching_printers = {ip: (location, nid) for ip, (location, nid) in printers.items() if nid == old_nid}
            
            if matching_printers:
                # Atualiza o NID no dicionário
                ip, (location, _) = next(iter(matching_printers.items()))
                printers[ip] = (location, new_nid)
                
                # Escreve a atualização de volta para o arquivo JSON
                with open('printers.json', 'w') as file:
                    json.dump(printers, file, indent=4)
                
                # Confirmação de atualização
                await update.message.reply_text(f"O NID da impressora em {location} (IP: {ip}) foi atualizado de {old_nid} para {new_nid}.")
            else:
                await update.message.reply_text(f"NID {old_nid} não encontrado na lista de impressoras.")
        else:
            await update.message.reply_text("Comando inválido. Use o formato '/atualizarNID NID:YYYY PARA:XXXX'.")
    except Exception as e:
        await update.message.reply_text(f"Ocorreu um erro ao executar o comando: {e}")

async def atualizar_ip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Usa expressão regular para capturar o NID e o novo IP
        match = re.search(r'NID:(\d+)\s+PARA_IP:(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', update.message.text)
        if match:
            nid = match.group(1)  # NID atual
            new_ip = match.group(2)  # Novo IP
            
            # Encontrar a impressora correspondente ao NID
            matching_printers = {ip: (location, nid_in_file) for ip, (location, nid_in_file) in printers.items() if nid_in_file == nid}
            
            if matching_printers:
                # Pega o IP atual e atualiza no dicionário
                old_ip, (location, _) = next(iter(matching_printers.items()))
                printers[new_ip] = (location, nid)
                # Remove a entrada antiga
                del printers[old_ip]
                
                # Escreve a atualização de volta para o arquivo JSON
                with open('printers.json', 'w') as file:
                    json.dump(printers, file, indent=4)
                
                # Confirmação de atualização
                await update.message.reply_text(f"O IP da impressora NID {nid} em {location} foi atualizado de {old_ip} para {new_ip}.")
            else:
                await update.message.reply_text(f"NID {nid} não encontrado na lista de impressoras.")
        else:
            await update.message.reply_text("Comando inválido. Use o formato '/atualizarIP NID:YYYY PARA_IP:XXX.XXX.XXX.XXX'.")
    except Exception as e:
        await update.message.reply_text(f"Ocorreu um erro ao executar o comando: {e}")

async def atualizar_setor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Usa expressão regular para capturar o NID e o novo setor
        match = re.search(r'NID:(\d+)\s+PARA_SETOR:(.+)', update.message.text)
        if match:
            nid = match.group(1)  # NID atual
            new_location = match.group(2)  # Novo setor
            
            # Encontrar a impressora correspondente ao NID
            matching_printers = {ip: (location, nid_in_file) for ip, (location, nid_in_file) in printers.items() if nid_in_file == nid}
            
            if matching_printers:
                # Pega o IP e atualiza o setor (localização) no dicionário
                ip, (_, _) = next(iter(matching_printers.items()))
                printers[ip] = (new_location, nid)
                
                # Escreve a atualização de volta para o arquivo JSON
                with open('printers.json', 'w') as file:
                    json.dump(printers, file, indent=4)
                
                # Confirmação de atualização
                await update.message.reply_text(f"O setor da impressora NID {nid} com IP {ip} foi atualizado para {new_location}.")
            else:
                await update.message.reply_text(f"NID {nid} não encontrado na lista de impressoras.")
        else:
            await update.message.reply_text("Comando inválido. Use o formato '/atualizarSetor NID:YYYY PARA_SETOR:Novo Setor'.")
    except Exception as e:
        await update.message.reply_text(f"Ocorreu um erro ao executar o comando: {e}")

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('contadores', contadores))
    application.add_handler(CommandHandler('contador', contador))
    application.add_handler(CommandHandler('atualizarNID', atualizar_nid))
    application.add_handler(CommandHandler('atualizarIP', atualizar_ip))
    application.add_handler(CommandHandler('atualizarSetor', atualizar_setor))

    application.run_polling()

if __name__ == '__main__':
    main()