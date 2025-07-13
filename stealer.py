def decrypt_password(password, key):
    """Расшифровывает пароль"""
    try:
        # Если значение пустое, сразу возвращаем пустую строку
        if not password:
            return ""
            
        # Попробуем расшифровать через DPAPI (для старых версий)
        if platform.system() == "Windows" and HAS_WIN32CRYPT:
            try:
                decrypted = win32crypt.CryptUnprotectData(password, None, None, None, 0)[1]
                if decrypted:
                    return decrypted.decode('utf-8', errors='ignore')
            except:
                pass
        
        # Для новых версий с AES-GCM
        if key and isinstance(password, bytes) and len(password) > 15:
            try:
                iv = password[3:15]
                payload = password[15:]
                cipher = AES.new(key, AES.MODE_GCM, iv)
                decrypted_pass = cipher.decrypt(payload)[:-16].decode('utf-8', errors='ignore')
                return decrypted_pass
            except:
                pass
        
        # Если ничего не сработало, вернем как есть (если это строка)
        if isinstance(password, str):
            return password
