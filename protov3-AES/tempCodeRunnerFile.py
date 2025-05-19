# === aes_dct_stego_secure.py ===
# Unified AES + DCT-based secure steganography (Selective Shield Edition)

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

# CONFIGURATION
BLOCK_SIZE = 16
KEY_SIZE = 32
REDUNDANCY = 7
IV_PROTECTION_REDUNDANCY = 15
IV_PROTECTED_BYTES = 64  # bytes to shield at high redundancy
POSITIONS = 3
IMAGE_SIZE = (120, 120)
HASH_LEN = 64
RS_ECC_BYTES = 128
rs = reedsolo.RSCodec(RS_ECC_BYTES)

# PATHS
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

    # Generate the AES key and encrypt the payload
    key = generate_key()
    with open(KEY_PATH, "wb") as f:
        f.write(key)
    encrypted = aes_encrypt(payload, key)
    
    # Separate the IV from the encrypted data for special protection
    iv = encrypted[:BLOCK_SIZE]  # The IV is the first 16 bytes of the AES ciphertext
    encrypted_data = encrypted[BLOCK_SIZE:]

    # Create the ECC encoded payload
    ecc_encoded = bytes(rs.encode(encrypted_data))

    with open(LEN_PATH, "w") as f:
        f.write(str(len(ecc_encoded)))

    # Embed the IV with extra redundancy
    iv_frame = cv2.imread(os.path.join(FRAME_DIR, 'frame_0001.png'))  # Use a clean frame for IV
    iv_chunk = iv  # Already a bytes object  # Only the IV (16 bytes) will be embedded here with redundancy
    iv_embedded = embed_data_into_frame(iv_frame, iv_chunk, redundancy=15)
    cv2.imwrite(os.path.join(FRAME_DIR, 'frame_0001.png'), iv_embedded)

    # Embed the encrypted data with normal redundancy
    frames = extract_frame_list()
    data_index = 0
    for i, chunk in enumerate(split_bytes(ecc_encoded, calculate_capacity(*iv_frame.shape[:2], redundancy=7))):
        frame = cv2.imread(os.path.join(FRAME_DIR, frames[i+1]))  # Skip the first frame for IV
        stego = embed_data_into_frame(frame, chunk, redundancy=7)
        cv2.imwrite(os.path.join(FRAME_DIR, frames[i+1]), stego)

    subprocess.run(["ffmpeg", "-y", "-framerate", "30", "-i", f"{FRAME_DIR}/frame_%04d.png", "-c:v", "ffv1", STEGO_VIDEO])
    print("[✓] Embedding complete.")


def extract():
    os.makedirs(FRAME_DIR, exist_ok=True)
    if not any(f.startswith("frame_") for f in os.listdir(FRAME_DIR)):
        subprocess.run(["ffmpeg", "-y", "-i", STEGO_VIDEO, f"{FRAME_DIR}/frame_%04d.png"], check=True)

    with open(LEN_PATH) as f:
        expected_len = int(f.read())
    
    # Extract the IV from its isolated frame
    iv_frame = cv2.imread(os.path.join(FRAME_DIR, 'frame_0001.png'))
    iv_chunk = extract_data_from_frame(iv_frame, length=1, redundancy=15)
    iv = iv_chunk  # full 16 bytes restored

    # Now proceed with the extraction of the remaining data
    h, w = extract_frame_dimensions()
    frames = extract_frame_list()

    data_len = (expected_len - 1)  # One frame is already used for the IV
    ecc_chunks, collected = [], 0
    for f in frames[1:]:  # Skip the IV frame
        frame = cv2.imread(os.path.join(FRAME_DIR, f))
        chunk = extract_data_from_frame(frame, length=data_len, redundancy=7)
        ecc_chunks.append(chunk)
        collected += len(chunk)

        if collected >= data_len:
            break

    full_payload = join_bytes(ecc_chunks)

    with open(DEBUG_EXTRACTED, "wb") as f:
        f.write(full_payload)
    print("[DEBUG] Extracted length:", len(full_payload))

    # Now decode the ECC and AES decryption as normal
    try:
        ecc_decoded = rs.decode(full_payload)[0]
    except reedsolo.ReedSolomonError:
        print("[!] ECC decode failed — corrupted ciphertext.")
        return

    try:
        decrypted = aes_decrypt(ecc_decoded, iv)  # Use IV for decryption
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
