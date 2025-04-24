import os
import random
import datetime
import tempfile
import io
import asyncio
from flask import Flask
from telegram import Bot, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# === CONFIGURATION ===
TELEGRAM_BOT_TOKEN = "8100815907:AAG5HMoCSD1GBdhM2XWN5F5-kyLu42szEfU"
CHAT_ID = "7991646583"
GDRIVE_FOLDER_NAME = "Shooting Malou"
CREDENTIALS_FILE = "credentials.json"

# === FLASK POUR RENDER ===
app = Flask(__name__)
@app.route("/")
def home():
    return "LaBibimerieBot est en ligne !"

# === HORAIRES PAR JOUR ===
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

# === RÉCUPÉRER TOUS LES FICHIERS MÉDIA ===
def get_all_media_files():
    service = get_drive_service()
    folder_resp = service.files().list(
        q=f"name='{GDRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder'",
        spaces='drive'
    ).execute()
    folder_id = folder_resp['files'][0]['id']

    all_files = []

    def explore(folder_id):
        response = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType)"
        ).execute()
        for file in response.get('files', []):
            if file['mimeType'] == 'application/vnd.google-apps.folder':
                explore(file['id'])
            elif 'image/' in file['mimeType'] or 'video/' in file['mimeType']:
                all_files.append(file)

    explore(folder_id)
    return all_files

# === TÉLÉCHARGER UN FICHIER DE DRIVE ===
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

# === ENVOYER LES STORIES ===
async def send_stories():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    # Texte 1 : ouverture
    await bot.send_message(chat_id=CHAT_ID, text="🇰🇷 bonjour 🇫🇷 open")
    await bot.send_message(chat_id=CHAT_ID, text=get_opening_hours())
    await bot.send_message(chat_id=CHAT_ID, text="https://la-bibimerie.bykomdab.com/?booking=true")
    await bot.send_message(chat_id=CHAT_ID, text="réserver / book a table")

    # Texte 2 : menu
    await bot.send_message(chat_id=CHAT
