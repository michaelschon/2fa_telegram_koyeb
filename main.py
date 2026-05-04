import telebot
import pyotp
import os
import socket
import subprocess
import threading
from datetime import timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── Variáveis de ambiente ─────────────────────────────────
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN nao definido.")

SECRET_KEY = os.environ.get('TELEGRAM_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("TELEGRAM_SECRET_KEY nao definido.")

# Mova estas para variáveis de ambiente também!
CAD_EMAIL = os.environ.get('CAD_EMAIL', '')
CAD_SENHA = os.environ.get('CAD_SENHA', '')

# ── Bot ───────────────────────────────────────────────────
bot = telebot.TeleBot(BOT_TOKEN)

AUTHORIZED_GROUPS = [-4753161233, -1001287387567]


def get_system_info():
    processor = cpu_frequency = total_memory = kernel_version = "N/A"
    total_disk = free_disk = uptime = "N/A"
    try:
        result = subprocess.run(['cat', '/proc/cpuinfo'], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        processor = next((l.split(": ")[1].strip() for l in lines if "model name" in l), "N/A")
        cpu_frequency = next((l.split(": ")[1].strip() + " MHz" for l in lines if "cpu MHz" in l), "N/A")
    except Exception: pass
    try:
        result = subprocess.run(['cat', '/proc/meminfo'], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        kb = next((int(l.split(":")[1].strip().split()[0]) for l in lines if "MemTotal" in l), 0)
        total_memory = f"{kb / (1024**2):.2f} GB"
    except Exception: pass
    try:
        result = subprocess.run(['uname', '-r'], capture_output=True, text=True)
        kernel_version = result.stdout.strip()
    except Exception: pass
    try:
        sv = os.statvfs('/')
        total_disk = f"{(sv.f_blocks * sv.f_frsize) / (1024**3):.2f} GB"
        free_disk  = f"{(sv.f_bfree  * sv.f_frsize) / (1024**3):.2f} GB"
    except Exception: pass
    try:
        result = subprocess.run(['cat', '/proc/uptime'], capture_output=True, text=True)
        secs = float(result.stdout.split()[0])
        uptime = str(timedelta(seconds=secs)).split('.')[0]
    except Exception: pass

    hostname   = socket.gethostname()
    try:    ip = socket.gethostbyname(hostname)
    except: ip = "N/A"

    return {
        "Hostname": hostname, "IP": ip,
        "Processador": processor, "Freq. CPU": cpu_frequency,
        "Memoria Total": total_memory, "Kernel": kernel_version,
        "Disco Total": total_disk, "Disco Livre": free_disk,
        "Uptime": uptime,
    }


def get_2fa_code():
    totp = pyotp.TOTP(SECRET_KEY.replace(" ", ""))
    return totp.now()


@bot.message_handler(func=lambda m: m.text and m.text.strip().lower() in ["2fa", "codigo"])
def send_2fa_code(message):
    if message.chat.id in AUTHORIZED_GROUPS:
        try:
            code = get_2fa_code()
            bot.reply_to(message, f"O código 2FA é: `{code}`", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"Erro: {e}")
    else:
        bot.reply_to(message, "Grupo não autorizado.")


@bot.message_handler(func=lambda m: m.text and m.text.strip().lower() in ["server", "server_info"])
def send_server_info(message):
    if message.chat.id in AUTHORIZED_GROUPS:
        try:
            info = get_system_info()
            text = "\n".join(f"*{k}:* {v}" for k, v in info.items())
            bot.reply_to(message, text, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"Erro: {e}")
    else:
        bot.reply_to(message, "Grupo não autorizado.")


@bot.message_handler(func=lambda m: m.text and m.text.strip().lower() in ["cadastro", "cad"])
def send_registration_info(message):
    if message.chat.id in AUTHORIZED_GROUPS:
        try:
            code = get_2fa_code()
            response = (
                f"*Informações de Login:*\n\n"
                f"- Email: `{CAD_EMAIL}`\n"
                f"- Senha: `{CAD_SENHA}`\n"
                f"- 2FA: `{code}`\n"
            )
            bot.reply_to(message, response, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"Erro: {e}")
    else:
        bot.reply_to(message, "Grupo não autorizado.")


@bot.message_handler(func=lambda m: m.text and m.text.strip().lower() in ["info_grupo", "info"])
def send_group_info(message):
    try:
        chat = message.chat
        bot.reply_to(message, f"Nome: {chat.title}\nID: `{chat.id}`\nTipo: {chat.type}", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"Erro: {e}")


# ── Health check HTTP — necessário para Koyeb free tier ──
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args): pass  # silencia logs do servidor


def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


# ── Main ──────────────────────────────────────────────────
if __name__ == "__main__":
    # Inicia o servidor HTTP em thread separada
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()
    print(f"Health server rodando...")
    print("Bot iniciado...")
    bot.infinity_polling(timeout=20, long_polling_timeout=20)
