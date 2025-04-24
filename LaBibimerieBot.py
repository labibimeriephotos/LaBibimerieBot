import os
import random
import datetime
import asyncio
import tempfile
from flask import Flask
from threading import Thread
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# === CONFIGURATION ===
TELEGRAM_BOT_TOKEN = "8100815907:AAG5HMoCSD1GBdhM2XWN5F5-kyLu42szEfU"
CHAT_ID = "7991646583"
GDRIVE_FOLDER_NAME = "Shooting Malou"
CREDENTIALS_FILE = "credentials.json"

# === FLASK POUR RENDER ===
app = Flask(__name__)
@app.route("/")
def index():
    return "Bot is running!"

# === HORAIRES ===
def get_opening_hours():
    today = datetime.datetime.now().strftime("%A")
    hours = {
        "Monday": "12h - 14h30 / 19h - 22h",
        "Tuesday": "12h - 14h30 / 19h - 22h",
        "Wednesday": "12h - 14h30 / 19h - 22h",
        "Thursday": "12h - 14h30 / 19h - 22h",
        "Friday": "12h - 14h30 / 19h - 22h30",
        "Saturday": "12h - 15h / 19h - 22h30",
        "Sunday": "12h - 15h"
    }
    return hours.get(today, "Fermé")

# === GOOGLE DRIVE ===
def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=creds)

def get_all_media_files():
    service = get_drive_service()
    folder_id_resp = service.files().list(
        q=f"name='{GDRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces='drive'
    ).execute()
    folder_id = folder_id_resp['files'][0]['id']

    all_files = []

    def explore_folder(folder_id):
        response = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType)"
        ).execute()
        for file in response.get('files', []):
            if file['mimeType'] == 'application/vnd.google-apps.folder':
                explore_folder(file['id'])  # récursif
            elif 'image/' in file['mimeType'] or 'video/' in file['mimeType']:
                all_files.append(file)

    explore_folder(folder_id)
    return all_files

def download_drive_file(file):
    service = get_drive_service()
    request = service.files().get_media(fileId=file['id'])
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    fh = io.FileIO(temp_file.name, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return temp_file.name, file['mimeType']

# === ENVOI DES MESSAGES ===
async def send_stories():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    # Story 1 : messages séparés
    await bot.send_message(chat_id=CHAT_ID, text="🇰🇷 bonjour 🇫🇷 open")
    await bot.send_message(chat_id=CHAT_ID, text=get_opening_hours())
    await bot.send_message(chat_id=CHAT_ID, text="https://la-bibimerie.bykomdab.com/?booking=true")
    await bot.send_message(chat_id=CHAT_ID, text="réserver / book a table")

    # Story 2
    await bot.send_message(chat_id=CHAT_ID, text="https://wiicmenu-qrcode.com/app/offre.php?resto=848")
    await bot.send_message(chat_id=CHAT_ID, text="menu")

    # Story 3 : 3 médias
    media_files = get_all_media_files()
    selected = random.sample(media_files, 3)
    for file in selected:
        path, mime_type = download_drive_file(file)
        with open(path, "rb") as f:
            if "video" in mime_type:
                await bot.send_video(chat_id=CHAT_ID, video=f)
            else:
                await bot.send_photo(chat_id=CHAT_ID, photo=f)
        os.remove(path)

# === HANDLER ===
async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="📩 Commande reçue, les stories arrivent...")
    await send_stories()

# === LANCEMENT DU BOT ===
def start_bot():
    app_telegram = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("run", run_command))
    app_telegram.add_handler(CommandHandler("rerun", run_command))
    app_telegram.run_polling()

# === MAIN ===
if __name__ == "__main__":
    # Lancer le bot Telegram dans un thread
    Thread(target=start_bot).start()
    # Lancer le serveur Flask pour Render
    app.run(host="0.0.0.0", port=10000)
