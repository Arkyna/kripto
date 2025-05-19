from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

BLOCK_SIZE = 16  # AES block size

def generate_key_iv():
    key = get_random_bytes(32)  # AES-256
    iv = get_random_bytes(BLOCK_SIZE)
    return key, iv

def aes_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(data, BLOCK_SIZE))
    return iv + encrypted  # prepend IV for decryption

with open("debug_aes_input.bin", "wb") as f:
    f.write(full_data)

def aes_decrypt(data: bytes, key: bytes) -> bytes:
    iv = data[:BLOCK_SIZE]
    encrypted = data[BLOCK_SIZE:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(encrypted), BLOCK_SIZE)
    return decrypted
