# Final, corrected implementation incoming. Let's patch this system completely.

import os
import cv2
import subprocess
import zlib
import reedsolo
from struct import pack, unpack
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from hash_util import get_sha3_hash, verify_hash
from utils import image_to_bytes, bytes_to_image, split_bytes, join_bytes
from dct_stego import embed_data_into_frame, extract_data_from_frame
from hashlib import sha256

# === CONFIG ===
BLOCK_SIZE = 16
KEY_SIZE = 32
REDUNDANCY = 5
IV_PROTECTION_REDUNDANCY = 9
POSITIONS = 3
IMAGE_SIZE = (120, 120)
HASH_LEN = 64
RS_ECC_BYTES = 128
rs = reedsolo.RSCodec(RS_ECC_BYTES)

# === PATHS ===
IMG_PATH = "assets/secret_image.png"
VIDEO_PATH = "assets/video.mp4"
FRAME_DIR = "assets/frames"
STEGO_VIDEO = "assets/stego_video.avi"
KEY_PATH = "aes_key.bin"
LEN_PATH = "payload_length.txt"
DECRYPTED_OUTPUT = "assets/decrypted_output.png"
DEBUG_ENCRYPTED = "debug/encrypted_payload.bin"
DEBUG_EXTRACTED = "debug/extracted_payload.bin"

os.makedirs("debug", exist_ok=True)

def generate_key():
    return get_random_bytes(KEY_SIZE)

def aes_encrypt(data, key):
    iv = get_random_bytes(BLOCK_SIZE)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return iv + cipher.encrypt(pad(data, BLOCK_SIZE))

def aes_decrypt(data, key):
    iv, enc = data[:BLOCK_SIZE], data[BLOCK_SIZE:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(enc), BLOCK_SIZE)

def extract_frame_dimensions():
    sample = cv2.imread(os.path.join(FRAME_DIR, "frame_0001.png"))
    return sample.shape[:2] if sample is not None else (0, 0)

def calculate_capacity(h, w, redundancy):
    return ((h // 8) * (w // 8)) // (redundancy * POSITIONS) // 8

def extract_frame_list():
    return sorted(f for f in os.listdir(FRAME_DIR) if f.startswith("frame_"))

def embed():
    os.makedirs(FRAME_DIR, exist_ok=True)
    img_bytes = image_to_bytes(IMG_PATH)
    hash_str = get_sha3_hash(img_bytes)
    combined = img_bytes + hash_str.encode()
    compressed = zlib.compress(combined)
    payload = pack(">I", len(compressed)) + compressed + sha256(compressed).digest()

    key = generate_key()
    with open(KEY_PATH, "wb") as f:
        f.write(key)
    encrypted = aes_encrypt(payload, key)

    iv = encrypted[:BLOCK_SIZE]
    encrypted_data = encrypted[BLOCK_SIZE:]
    ecc_encoded = bytes(rs.encode(encrypted_data))

    with open(DEBUG_ENCRYPTED, "wb") as f:
        f.write(iv + ecc_encoded)

    with open(LEN_PATH, "w") as f:
        f.write(str(len(ecc_encoded)))

    subprocess.run(["ffmpeg", "-y", "-i", VIDEO_PATH, "-qscale:v", "1", f"{FRAME_DIR}/frame_%04d.png"], stdout=subprocess.DEVNULL)

    iv_frame = cv2.imread(os.path.join(FRAME_DIR, 'frame_0001.png'))
    if iv_frame is None:
        print("[!] Failed to read frame_0001.png for IV.")
        return
    iv_embedded = embed_data_into_frame(iv_frame, iv, redundancy=IV_PROTECTION_REDUNDANCY)
    cv2.imwrite(os.path.join(FRAME_DIR, 'frame_0001.png'), iv_embedded)

    frames = extract_frame_list()
    h, w = extract_frame_dimensions()
    capacity = calculate_capacity(h, w, REDUNDANCY)
    for i, chunk in enumerate(split_bytes(ecc_encoded, capacity)):
        frame = cv2.imread(os.path.join(FRAME_DIR, frames[i + 1]))
        stego = embed_data_into_frame(frame, chunk, redundancy=REDUNDANCY)
        cv2.imwrite(os.path.join(FRAME_DIR, frames[i + 1]), stego)

    subprocess.run(["ffmpeg", "-y", "-framerate", "30", "-i", f"{FRAME_DIR}/frame_%04d.png", "-c:v", "ffv1", STEGO_VIDEO])
    print("[✓] Embedding complete.")

def extract():
    with open(KEY_PATH, "rb") as f:
        key = f.read()
    os.makedirs(FRAME_DIR, exist_ok=True)
    if not any(f.startswith("frame_") for f in os.listdir(FRAME_DIR)):
        subprocess.run(["ffmpeg", "-y", "-i", STEGO_VIDEO, f"{FRAME_DIR}/frame_%04d.png"], check=True)

    with open(LEN_PATH) as f:
        expected_len = int(f.read())

    iv_frame = cv2.imread(os.path.join(FRAME_DIR, 'frame_0001.png'))
    iv = extract_data_from_frame(iv_frame, length=BLOCK_SIZE, redundancy=IV_PROTECTION_REDUNDANCY)

    h, w = extract_frame_dimensions()
    capacity = calculate_capacity(h, w, REDUNDANCY)
    frames = extract_frame_list()
    ecc_chunks, collected = [], 0
    for f in frames[1:]:
        if collected >= expected_len:
            break
        frame = cv2.imread(os.path.join(FRAME_DIR, f))
        chunk = extract_data_from_frame(frame, length=capacity, redundancy=REDUNDANCY)
        take = min(expected_len - collected, len(chunk))
        ecc_chunks.append(chunk[:take])
        collected += take

    full_payload = join_bytes(ecc_chunks)
    with open(DEBUG_EXTRACTED, "wb") as f:
        f.write(full_payload)
    print("[DEBUG] Extracted length:", len(full_payload))

    try:
        ecc_decoded = rs.decode(full_payload)[0]
    except reedsolo.ReedSolomonError:
        print("[!] ECC decode failed — corrupted ciphertext.")
        return

    try:
        full_encrypted = iv + ecc_decoded
        decrypted = aes_decrypt(full_encrypted, key)
    except Exception as e:
        print("[!] AES decryption failed:", e)
        return

    data_len = unpack(">I", decrypted[:4])[0]
    compressed = decrypted[4:4 + data_len]
    checksum = decrypted[4 + data_len: 4 + data_len + 32]

    if sha256(compressed).digest() != checksum:
        print("[!] Checksum mismatch after ECC.")
        return

    try:
        combined = zlib.decompress(compressed)
    except zlib.error:
        print("[!] Decompression failed.")
        return

    if len(combined) < HASH_LEN:
        print("[!] Combined data too short.")
        return

    img_data = combined[:-HASH_LEN]
    hash_bytes = combined[-HASH_LEN:]

    try:
        hash_str = hash_bytes.decode("ascii")
    except UnicodeDecodeError:
        print("[!] Extracted hash is not valid ASCII.")
        return

    if not verify_hash(img_data, hash_str):
        print("[!] Hash check failed.")
        return

    print(f"[✓] SHA-3 Verified Hash: {hash_str}")
    print(f"[✓] Output saved to: {DECRYPTED_OUTPUT}")

    bytes_to_image(img_data, IMAGE_SIZE, DECRYPTED_OUTPUT)
    print("[✓] Image successfully recovered.")

if __name__ == "__main__":
    mode = input("[?] Mode (e=embed / x=extract): ").strip().lower()
    if mode == 'e':
        embed()
    elif mode == 'x':
        extract()
    else:
        print("[!] Invalid mode.")
