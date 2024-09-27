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
    
# Lista global para armazenar impressoras com erro
impressoras_com_erro = []

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
        "/atualizarIP NID:<NID> PARA:<NOVO_IP> - Atualiza o IP de uma impressora. Exemplo: /atualizarIP NID:1234 PARA:192.168.0.123\n"
        "/atualizarSetor NID:<NID> PARA:<NOVO_SETOR> - Atualiza o setor de uma impressora. Exemplo: /atualizarSetor NID:1234 PARA:Novo Setor\n\n"
        "**Novos Comandos:**\n"
        "/adicionar NID:<NID> IP:<IP> SETOR:<SETOR> - Adiciona uma nova impressora ao sistema. Exemplo: /adicionar NID:5678 IP:192.168.0.123 SETOR:Administração\n"
        "/buscar <SETOR> - Busca impressoras por setor ou parte do nome do setor. Exemplo: /buscar adm\n"
        "/buscarErro - Lista todas as impressoras que apresentaram erro ao tentar exibir os contadores."
        "/comandos - Lista todos os coamdos disponíveis no bot, com exemplos."
        "/remover NID:<NID> - Remove uma impressora da lista de impressoras com base no NID"
        "/removerIP IP:<IP> - Remove uma impressora da lista de impressoras com base no IP"
    )
    
async def contadores(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        for ip, (location, nid) in printers.items():
            contador = get_snmp_data(ip, page_counter_oid)
            if contador is not None:
                print(f"{location} ({ip}, NID: {nid}) - Contador: {contador}")
                await update.message.reply_text(f"{location} ({ip}, NID: {nid}) - Contador: {contador}")
            else:
                # Armazena o IP da impressora que apresentou erro
                impressoras_com_erro.append(ip)
                await update.message.reply_text(f"Não foi possível obter o contador para a impressora em {location} ({ip}, NID: {nid})")
    except Exception as e:
        await update.message.reply_text(f'Ocorreu um erro ao executar o comando: {e}')

async def contador(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
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
                    # Armazena o IP da impressora que apresentou erro
                    impressoras_com_erro.append(ip)
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
                    # Armazena o IP da impressora que apresentou erro
                    impressoras_com_erro.append(ip)
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
        match = re.search(r'NID:(\d+)\s+PARA:(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', update.message.text)
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
            await update.message.reply_text("Comando inválido. Use o formato '/atualizarIP NID:YYYY PARA:XXX.XXX.XXX.XXX'.")
    except Exception as e:
        await update.message.reply_text(f"Ocorreu um erro ao executar o comando: {e}")

async def atualizar_setor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Usa expressão regular para capturar o NID e o novo setor
        match = re.search(r'NID:(\d+)\s+PARA:(.+)', update.message.text)
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
            await update.message.reply_text("Comando inválido. Use o formato '/atualizarSetor NID:YYYY PARA:Novo Setor'.")
    except Exception as e:
        await update.message.reply_text(f"Ocorreu um erro ao executar o comando: {e}")

async def comandos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista todos os comandos disponíveis no bot, enviando um por mensagem."""
    
    # Lista de comandos com suas descrições e exemplos
    comandos_list = [
        ("/contadores", "Mostra os contadores de todas as impressoras."),
        ("/contador ip:<IP>", "Mostra o contador de uma impressora específica com o endereço IP informado. Exemplo: ", 
            "/contador ip:192.168.0.222"),
        ("/contador NID:<NID>", "Mostra o contador de uma impressora específica com o NID informado. Exemplo: ", 
            "/contador NID:1234"),
        ("/atualizarNID NID:<NID_ATUAL> PARA:<NOVO_NID>", "Atualiza o NID de uma impressora. Exemplo: ", 
            "/atualizarNID NID:1234 PARA:5678"),
        ("/atualizarIP NID:<NID> PARA:<NOVO_IP>", "Atualiza o IP de uma impressora. Exemplo: ", 
            "/atualizarIP NID:1234 PARA:192.168.0.123"),
        ("/atualizarSetor NID:<NID> PARA:<NOVO_SETOR>", "Atualiza o setor de uma impressora. Exemplo: ", 
            "/atualizarSetor NID:1234 PARA:Novo Setor"),
        ("/adicionar NID:<NID> IP:<IP> SETOR:<SETOR>", "Adiciona uma nova impressora ao sistema. Exemplo: ", 
            "/adicionar NID:5678 IP:192.168.0.123 SETOR:Administração"),
        ("/buscar <SETOR>", "Busca impressoras por setor ou parte do nome do setor. Exemplo: ", 
            "/buscar adm"),
        ("/buscarErro", "Lista todas as impressoras que apresentaram erro ao tentar exibir os contadores.")
        ("/comandos", "Lista todos os comandos disponíveis no bot, com exemplos."),
        ("/remover NID:<NID>", "Remove uma impressora da lista de impressoras com base no NID"),
        ("/removerIP IP:<IP>", "Remove uma impressora da lista de impressoras com base no IP"),
    ]

    # Enviar cada comando e descrição em uma mensagem separada
    for comando in comandos_list:
        if len(comando) == 2:
            await update.message.reply_text(f"{comando[0]} - {comando[1]}")
        elif len(comando) == 3:
            await update.message.reply_text(f"{comando[0]} - {comando[1]}")
            await update.message.reply_text(f"{comando[2]}")

async def adicionar_impressora(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adiciona uma nova impressora ao arquivo printers.json."""
    try:
        # Extrair os parâmetros NID, IP e SETOR do comando
        match_nid = re.search(r'NID:(\d+)', update.message.text)
        match_ip = re.search(r'IP:(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', update.message.text)
        match_setor = re.search(r'SETOR:(\w+)', update.message.text)

        # Validar os parâmetros
        if not match_nid or not match_ip or not match_setor:
            await update.message.reply_text("Comando inválido. Use o formato: /adicionar NID:<NID> IP:<IP> SETOR:<SETOR>")
            return

        nid = match_nid.group(1)
        ip = match_ip.group(1)
        setor = match_setor.group(1)

        # Verificar se o IP já está cadastrado
        if ip in printers:
            await update.message.reply_text(f"Já existe uma impressora cadastrada com o IP {ip}.")
            return

        # Verificar se o NID já está cadastrado
        for _, (existing_setor, existing_nid) in printers.items():
            if existing_nid == nid:
                await update.message.reply_text(f"Já existe uma impressora cadastrada com o NID {nid}.")
                return

        # Adicionar a nova impressora ao dicionário
        printers[ip] = (setor, nid)

        # Atualizar o arquivo printers.json com a nova impressora
        with open('printers.json', 'w') as file:
            json.dump(printers, file, indent=4)

        await update.message.reply_text(f"Impressora adicionada com sucesso:\nNID: {nid}\nIP: {ip}\nSetor: {setor}")

    except Exception as e:
        await update.message.reply_text(f"Ocorreu um erro ao adicionar a impressora: {e}")

async def buscar_setor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Busca impressoras pelo setor (ou parte dele) e retorna os dados correspondentes."""
    try:
        # Extrair o texto após o comando "/buscar"
        setor = ' '.join(context.args).strip()

        # Validar o parâmetro
        if not setor:
            await update.message.reply_text("Comando inválido. Use o formato: /buscar <SETOR>")
            return

        # Buscar impressoras que contenham parte do nome do setor
        resultados = [
            f"Setor: {info[0]}, NID: {info[1]}, IP: {ip}"
            for ip, info in printers.items() if setor.lower() in info[0].lower()
        ]

        # Verificar se encontrou impressoras
        if resultados:
            await update.message.reply_text("\n\n".join(resultados))
        else:
            await update.message.reply_text(f"Nenhuma impressora encontrada no setor com '{setor}'.")

    except Exception as e:
        await update.message.reply_text(f"Ocorreu um erro ao buscar impressoras: {e}")

async def buscar_erro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista as impressoras que apresentaram problemas ao exibir os contadores."""
    try:
        if impressoras_com_erro:
            # Monta uma mensagem com as impressoras que apresentaram erro
            mensagens = []
            for ip in impressoras_com_erro:
                setor, nid = printers[ip]
                mensagens.append(f"Setor: {setor}, NID: {nid}, IP: {ip}")
            
            # Responde com a lista de impressoras com erro
            await update.message.reply_text("\n\n".join(mensagens))
        else:
            await update.message.reply_text("Nenhuma impressora apresentou problemas recentemente.")
    
    except Exception as e:
        await update.message.reply_text(f"Ocorreu um erro ao buscar impressoras com problema: {e}")

async def remover_impressora(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove uma impressora da lista de impressoras com base no NID ou IP."""
    try:
        # Extrair o parâmetro NID ou IP do comando
        match_nid = re.search(r'NID:(\d+)', update.message.text)
        match_ip = re.search(r'IP:(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', update.message.text)

        if match_nid:
            nid = match_nid.group(1)

            # Procurar e remover a impressora pelo NID
            printer_to_remove = None
            for ip, (location, printer_nid) in list(printers.items()):
                if printer_nid == nid:
                    printer_to_remove = ip
                    break

            if printer_to_remove:
                del printers[printer_to_remove]
                with open('printers.json', 'w') as file:
                    json.dump(printers, file, indent=4)
                await update.message.reply_text(f"Impressora com NID {nid} removida com sucesso.")
            else:
                await update.message.reply_text(f"Impressora com NID {nid} não encontrada.")
        
        elif match_ip:
            ip = match_ip.group(1)

            # Procurar e remover a impressora pelo IP
            if ip in printers:
                del printers[ip]
                with open('printers.json', 'w') as file:
                    json.dump(printers, file, indent=4)
                await update.message.reply_text(f"Impressora com IP {ip} removida com sucesso.")
            else:
                await update.message.reply_text(f"Impressora com IP {ip} não encontrada.")
        else:
            await update.message.reply_text("Comando inválido. Use o formato: /remover NID:<NID> ou /remover IP:<IP>")
    
    except Exception as e:
        await update.message.reply_text(f"Ocorreu um erro ao remover a impressora: {e}")

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Handlers para comandos
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('comandos', comandos))
    application.add_handler(CommandHandler('contadores', contadores))
    application.add_handler(CommandHandler('contador', contador))
    application.add_handler(CommandHandler('atualizarNID', atualizar_nid))
    application.add_handler(CommandHandler('atualizarIP', atualizar_ip))
    application.add_handler(CommandHandler('atualizarSetor', atualizar_setor))
    application.add_handler(CommandHandler('adicionar', adicionar_impressora))
    application.add_handler(CommandHandler('buscar', buscar_setor))
    application.add_handler(CommandHandler('buscarErro', buscar_erro))
    application.add_handler(CommandHandler('remover', remover_impressora))

    application.run_polling()

if __name__ == '__main__':
    main()
