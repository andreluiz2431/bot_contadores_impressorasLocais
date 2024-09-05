from pysnmp.hlapi import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity

# Dicionário com IPs das impressoras, seus respectivos locais e NID
printers = {
    '192.168.2.158': ('DC Caixa Central', '1017'),
    '192.168.2.159': ('DC Tintas e Ferragens', '1333'),
    '192.168.2.160': ('DC Coopservice', '1001'),
    '192.168.2.161': ('Desconhecido', ''),
    '192.168.2.162': ('DC Lançamento Notas', '1005'),
    '192.168.2.164': ('DC Balcão de Peças - esq', '177'),
    '192.168.2.163': ('DC Balcão de Peças - dir', '184'),
    '192.168.2.22': ('DC Agroelétrica', '1036'),
    '192.168.2.24': ('DC Compras', '195'),
    '192.168.2.241': ('DC Depósito de Ração', '1016'),
    '192.168.2.88': ('DC Veterinária', '1229'),
    '192.168.3.147': ('BR Fabrica de Ração', '1270'),
    '192.168.3.148': ('BR Usina', '1404'),
    '192.168.3.149': ('BR Portaria', '193'),
    '192.168.3.150': ('BR Balança', '1172'),
    '192.168.3.151': ('BR Almoxarifado', '1202'),
    '192.168.3.152': ('BR Expedição', '1349'),
    '192.168.3.153': ('BR Ambulatório', '1271'),
    '192.168.3.156': ('BR Audiometria', '605'),
    '192.168.3.154': ('BR Administração', '967'),
    '192.168.3.155': ('BR SESMT', '59'),
    '192.168.3.157': ('BR Secagem', '643'),
    '192.168.3.159': ('BR Manutenção', '281'),
    '192.168.3.160': ('BR Refeitório', '535'),
    '192.168.3.190': ('BR Afuncaal', '1040'),
    '192.168.3.192': ('BR Sementeiro', '187'),
    '192.168.4.155': ('MR Balança', '2378'),
    '192.168.4.156': ('MR Unitec', '149'),
    '192.168.4.157': ('MR Insumos', '181'),
    '192.168.5.202': ('VA Contabilidade', '3210'),
    '192.168.5.204': ('VA Associados', '2625'),
    '192.168.5.205': ('VA Recursos Humanos', '3305'),
    '192.168.5.206': ('VA Jurídico', '1364'),
    '192.168.5.210': ('VA Marketing', '3156'),
    '192.168.5.230': ('VA Informática', '285'),
    '192.168.6.35': ('RSM Balança', '54')
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

def main():
    for ip, (location, nid) in printers.items():
        contador = get_snmp_data(ip, page_counter_oid)
        if contador is not None:
            print(f"{location} ({ip}, NID: {nid}) - Contador: {contador}")
        else:
            print(f"Não foi possível obter o contador para a impressora em {location} ({ip}, NID: {nid})")

if __name__ == "__main__":
    main()
