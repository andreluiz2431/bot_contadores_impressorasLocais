# Guia de Configuração e Execução do Bot Telegram

Este guia fornece as instruções para configurar, executar e empacotar o bot Telegram usando Python.

## 1. Instalação de Dependências

Para começar, instale as dependências necessárias para o projeto. Siga os passos abaixo:

### 1.1. Clonar o Repositório

Clone o repositório do projeto para o seu ambiente local:

bash
git clone <URL_DO_REPOSITORIO>
cd <NOME_DO_DIRETORIO>

### 1.3. Instalar Dependências

bash
pip install pysnmp==4.4.12
pip install python-telegram-bot
pip install python-dotenv

## 2. Configuração do Arquivo .env
Para proteger informações sensíveis, como o token do bot, usamos um arquivo .env.

### 2.1. Criar o Arquivo .env
Crie um arquivo chamado .env na raiz do projeto com o seguinte conteúdo:

dotenv
TELEGRAM_BOT_TOKEN=seu_token_aqui

Substitua seu_token_aqui pelo token do bot Telegram fornecido pelo BotFather.

### 2.2. Criar o Arquivo printers.json
Crie um arquivo chamado printers.json na raiz do projeto com o seguinte conteúdo (IP, Nome e Código):

{
    "192.168.0.000": ["Xxxxxxx", "000"],
    "192.168.0.000": ["Xxxxxxx", "000"],
    ...
}

Substitua seu_token_aqui pelo token do bot Telegram fornecido pelo BotFather.

## 3. Executar o Código
Após configurar as dependências e o arquivo .env, você pode executar o bot com o comando:

bash
python telegram_bot.py

O bot será iniciado e estará pronto para receber comandos no Telegram.

## 4. Empacotar o Projeto como Executável
Para facilitar a execução sem a necessidade de instalar o Python, você pode criar um executável com o PyInstaller.

### 4.1. Instalar o PyInstaller
Certifique-se de que o PyInstaller está instalado:

bash
pip install pyinstaller

### 4.2. Criar o Executável
Execute o PyInstaller para gerar um executável do script:

bash
pyinstaller --onefile telegram_bot.py

Este comando cria um executável único na pasta dist. O arquivo executável gerado será telegram_bot.exe no Windows ou telegram_bot no macOS/Linux.

### 4.3. Executar o Executável
Navegue até a pasta dist e execute o arquivo gerado:

bash
cd dist
./telegram_bot # No Windows: telegram_bot.exe

O bot será iniciado como um programa independente, sem a necessidade de um ambiente Python.

## 5. Resolução de Problemas
Token não encontrado: Verifique se o arquivo .env está corretamente configurado e se o nome da variável está correto (TELEGRAM_BOT_TOKEN).
Erros ao executar o PyInstaller: Verifique se todas as dependências estão corretamente instaladas e se o script não possui erros.
Para qualquer dúvida ou problema adicional, consulte a documentação oficial do python-telegram-bot e do PyInstaller.