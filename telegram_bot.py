from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from pysnmp.hlapi import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
from dotenv import load_dotenv
import os

# Carrega as variáveis do arquivo .env
load_dotenv()

# Obtém o token do ambiente
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    raise ValueError("O token do bot não foi encontrado. Verifique seu arquivo .env.")


# Dicionário com IPs das impressoras, seus respectivos locais e NID
printers = {
    '192.168.x.x': ('XxxxxxxNome', 'XxxxxxxCódigo'),
    '192.168.x.x': ('XxxxxxxNome', 'XxxxxxCódigo'),
}

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
    await update.message.reply_text('Olá! Envie "/contadores" para executar a busca por contadores das impressoras.')

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

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('contadores', contadores))

    application.run_polling()

if __name__ == '__main__':
    main()
