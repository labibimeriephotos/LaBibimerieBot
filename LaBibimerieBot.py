import os
import random
import datetime
import asyncio
import tempfile
import threading
import io
from flask import Flask

from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# === CONFIGURATION ===
TELEGRAM_BOT_TOKEN = "8100815907:AAHYEmZqMpLoZnfWAvqGBLyxSOWU_pDHXfg"
CHAT_ID = "7991646583"
GDRIVE_FOLDER_NAME = "Shooting Malou"
CREDENTIALS_FILE = "credentials.json"

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

# === GOOGLE DRIVE SETUP ===
def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=creds)

# === RETRIEVE MEDIA FROM GOOGLE DRIVE (incl. subfolders) ===
def get_random_drive_files():
    service = get_drive_service()

    # Get root folder ID
    response = service.files().list(q=f"name='{GDRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder'",
                                     spaces='drive').execute()
    folder_id = response['files'][0]['id']

    all_files = []

    def explore_folder(fid):
        response = service.files().list(
            q=f"'{fid}' in parents and trashed=false",
            fields="files(id, name, mimeType)",
            spaces='drive'
        ).execute()
        for file in response['files']:
            if file['mimeType'] == 'application/vnd.google-apps.folder':
                explore_folder(file['id'])
            elif "image" in file['mimeType'] or "video" in file['mimeType']:
                all_files.append(file)

    explore_folder(folder_id)
    return random.sample(all_files, min(3, len(all_files)))

# === DOWNLOAD FILE FROM GOOGLE DRIVE ===
def download_drive_file(file):
    service = get_drive_service()
    request = service.files().get_media(fileId=file['id'])
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    fh = io.FileIO(temp_file.name, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return temp_file.name, file['mimeType']

# === ENVOI DES STORIES ===
async def send_stories():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    await bot.send_message(chat_id=CHAT_ID, text="🇰🇷 bonjour 🇫🇷 open")
    await bot.send_message(chat_id=CHAT_ID, text=get_opening_hours())
    await bot.send_message(chat_id=CHAT_ID, text="https://la-bibimerie.bykomdab.com/?booking=true")
    await bot.send_message(chat_id=CHAT_ID, text="réserver / book a table")
    await bot.send_message(chat_id=CHAT_ID, text="https://wiicmenu-qrcode.com/app/offre.php?resto=848")
    await bot.send_message(chat_id=CHAT_ID, text="menu")

    media_files = get_random_drive_files()
    for file in media_files:
        path, mime_type = download_drive_file(file)
        with open(path, "rb") as f:
            if "video" in mime_type:
                await bot.send_video(chat_id=CHAT_ID, video=f)
            else:
                await bot.send_photo(chat_id=CHAT_ID, photo=f)
        os.remove(path)

# === COMMANDES /run ET /rerun ===
async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_stories()

# === LANCEMENT DU BOT TELEGRAM ===
def start_bot():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("run", run_command))
    application.add_handler(CommandHandler("rerun", run_command))
    print(f"Bot started at {datetime.datetime.now()}")
    application.run_polling()

# === MINI SERVEUR FLASK POUR RENDER ===
app = Flask(__name__)

@app.route("/")
@app.route("/healthz")
def healthz():
    return "OK", 200

# === MAIN ===
if __name__ == "__main__":
    threading.Thread(target=start_bot).start()
    app.run(host="0.0.0.0", port=10000)
