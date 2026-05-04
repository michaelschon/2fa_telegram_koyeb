import telebot
import pyotp
import os
import socket
import subprocess
from datetime import timedelta
import requests

# Substitua pelo token do seu bot, obtido do BotFather no Telegram
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN') # O Render vai injetar isso
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set.")
    
SECRET_KEY = os.environ.get('TELEGRAM_SECRET_KEY') # O Render vai injetar isso
if not SECRET_KEY:
    raise ValueError("TELEGRAM_SECRET_KEY environment variable not set.")


bot = telebot.TeleBot(BOT_TOKEN)

AUTHORIZED_GROUPS = [-4753161233, -1001287387567]  # IDs dos grupos autorizados

def get_system_info():
    # Tipo de processador e frequência
    processor = "Informação não disponível"
    cpu_frequency = "Informação não disponível"
    try:
        # Não precisa de sudo para ler /proc/cpuinfo
        result = subprocess.run(['cat', '/proc/cpuinfo'], capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        processor = next((line.split(": ")[1].strip() for line in lines if "model name" in line), "Informação não disponível")
        cpu_frequency = next((line.split(": ")[1].strip() + " MHz" for line in lines if "cpu MHz" in line), "Informação não disponível")
    except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
        print(f"Erro ao obter info do processador: {e}")

    # Quantidade de memória
    total_memory = "Informação não disponível"
    try:
        # Não precisa de sudo para ler /proc/meminfo
        result = subprocess.run(['cat', '/proc/meminfo'], capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        mem_total_kb = next((int(line.split(":")[1].strip().split()[0]) for line in lines if "MemTotal" in line), 0)
        total_memory = f"{mem_total_kb / (1024 ** 2):.2f} GB"
    except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
        print(f"Erro ao obter info de memória: {e}")

    # Versão do kernel
    kernel_version = "Informação não disponível"
    try:
        # Não precisa de sudo para uname -r
        result = subprocess.run(['uname', '-r'], capture_output=True, text=True, check=True)
        kernel_version = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
        print(f"Erro ao obter versão do kernel: {e}")

    # Hostname
    hostname = socket.gethostname()

    # IP
    ip_address = "Não disponível"
    try:
        # socket.gethostbyname geralmente funciona sem problemas de permissão
        ip_address = socket.gethostbyname(hostname)
    except socket.gaierror as e:
        print(f"Erro ao obter IP: {e}")

    # Tamanho do disco e espaço livre
    total_disk = "Informação não disponível"
    free_disk = "Informação não disponível"
    try:
        # os.statvfs não precisa de sudo
        statvfs = os.statvfs('/')
        total_disk = f"{(statvfs.f_blocks * statvfs.f_frsize) / (1024 ** 3):.2f} GB"
        free_disk = f"{(statvfs.f_bfree * statvfs.f_frsize) / (1024 ** 3):.2f} GB"
    except OSError as e:
        print(f"Erro ao obter info de disco: {e}")

    # Uptime
    uptime = "Informação não disponível"
    try:
        # Não precisa de sudo para ler /proc/uptime
        result = subprocess.run(['cat', '/proc/uptime'], capture_output=True, text=True, check=True)
        uptime_seconds = float(result.stdout.split()[0])
        uptime = str(timedelta(seconds=uptime_seconds)).split('.')[0]  # Remover os milissegundos
    except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
        print(f"Erro ao obter uptime: {e}")

    return {
        "Hostname": hostname,
        "IP Address": ip_address,
        "Processor": processor,
        "CPU Frequency": cpu_frequency,
        "Total Memory": total_memory,
        "Kernel Version": kernel_version,
        "Total Disk Size": total_disk,
        "Free Disk Space": free_disk,
        "Uptime": uptime,
    }
   

def get_2fa_code(secret):
    """Gera um código 2FA com base na chave secreta."""
    totp = pyotp.TOTP(secret.replace(" ", ""))  # Remove espaços da chave secreta
    return totp.now()

@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() in ["2fa", "codigo"])
def send_2fa_code(message):
    if message.chat.id in AUTHORIZED_GROUPS:
        try:
            code = get_2fa_code(SECRET_KEY)
            bot.reply_to(message, f"Seu código 2FA é: **{code}**", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"Erro ao gerar o código 2FA: {str(e)}")
    else:
        bot.reply_to(message, "O código 2FA só pode ser exibido em grupos autorizados.")

@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() in ["server", "server_info"])
def send_server_info(message):
    if message.chat.id in AUTHORIZED_GROUPS:
        try:
            info = get_system_info()
            info_message = "\n".join([f"{key}: {value}" for key, value in info.items()])
            bot.reply_to(message, f"{info_message}", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"Erro ao mostrar informações do Servidor de Hospedagem: {str(e)}")
    else:
        bot.reply_to(message, "As informações do servidor só podem exibidas em grupos autorizados.")

@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() in ["cadastro", "cad"])
def send_registration_info(message):
    if message.chat.id in AUTHORIZED_GROUPS:
        try:
            code = get_2fa_code(SECRET_KEY)
            email = "cadveracruzv6club@gmail.com"
            senha = "YRZ_wUgTG2WR9mHaXfBM"
            response = (
                f"Informações de Login para o cadastro:\n\n"
                f"- Email: {email}\n"
                f"- Senha: {senha}\n"
                f"- 2FA:   {code}\n"
            )
            bot.reply_to(message, response)
        except Exception as e:
            bot.reply_to(message, f"Erro ao obter informações de cadastro: {str(e)}")
    else:
        bot.reply_to(message, "O comando 'cadastro' só pode ser usado em grupos autorizados.")

@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() in ["info_grupo", "informacao_grupo", "info"])
def send_group_info(message):
    try:
        chat = message.chat
        info = (
            f"Informações do grupo:\n"
            f"- Nome: {chat.title}\n"
            f"- ID: {chat.id}\n"
            f"- Tipo: {chat.type}\n"
        )
        bot.reply_to(message, info)
    except Exception as e:
        bot.reply_to(message, f"Erro ao obter informações do grupo: {str(e)}")

if __name__ == "__main__":
    print("Bot está funcionando...")
    bot.infinity_polling(timeout=20, long_polling_timeout=20)
