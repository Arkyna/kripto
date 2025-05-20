# === aes_dct_stego_secure.py ===
# Unified AES + QIM-DCT secure steganography (Hybrid Forge Edition)

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
from utils import image_to_bytes, bytes_to_image
from hashlib import sha256
import numpy as np
from scipy.fftpack import dct, idct

# === CONFIG ===
BLOCK_SIZE = 8
QIM_DELTA = 20
QIM_AC_COEFFS = 10
AES_BLOCK_SIZE = 16
KEY_SIZE = 32
IMAGE_SIZE = (75, 75)
HASH_LEN = 64
RS_ECC_BYTES = 128
rs = reedsolo.RSCodec(RS_ECC_BYTES)

# === PATHS ===
IMG_PATH = "assets/secret_image_small.png"
VIDEO_PATH = "new/cover_lossless.avi"
FRAME_DIR = "assets/frames"
STEGO_VIDEO = "assets/stego_compressed.mp4"
KEY_PATH = "aes_key.bin"
LEN_PATH = "payload_length.txt"
DECRYPTED_OUTPUT = "assets/decrypted_output.png"
DEBUG_ENCRYPTED = "debug/encrypted_payload.bin"
DEBUG_EXTRACTED = "debug/extracted_payload.bin"
STEGO_REFERENCE_FRAME = os.path.join(FRAME_DIR, "stego_frame_0001.png")

os.makedirs("debug", exist_ok=True)

# === QIM-DCT CORE ===
def qim_embed_bitstream(frame, bitstream):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    float_img = np.float32(gray)
    embedded = float_img.copy()
    idx = 0
    for y in range(0, h, BLOCK_SIZE):
        for x in range(0, w, BLOCK_SIZE):
            if idx >= len(bitstream):
                break
            block = float_img[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE]
            dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')
            for i in range(QIM_AC_COEFFS):
                coeff_idx = i + 1
                coeff = dct_block.flat[coeff_idx]
                b = int(bitstream[idx])
                q = int(round(coeff / QIM_DELTA))
                if q % 2 != b:
                    q += 1 if b == 1 else -1
                dct_block.flat[coeff_idx] = q * QIM_DELTA
                idx += 1
                if idx >= len(bitstream):
                    break
            idct_block = idct(idct(dct_block.T, norm='ortho').T, norm='ortho')
            embedded[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE] = idct_block
        if idx >= len(bitstream):
            break
    embedded = np.clip(embedded, 0, 255).astype(np.uint8)
    return cv2.cvtColor(embedded, cv2.COLOR_GRAY2BGR)

def qim_extract_bitstream(frame, length):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    float_img = np.float32(gray)
    bitstream = []
    idx = 0
    for y in range(0, h, BLOCK_SIZE):
        for x in range(0, w, BLOCK_SIZE):
            if idx >= length:
                break
            block = float_img[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE]
            dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')
            for i in range(QIM_AC_COEFFS):
                coeff_idx = i + 1
                coeff = dct_block.flat[coeff_idx]
                bit = int(round(coeff / QIM_DELTA)) % 2
                bitstream.append(str(bit))
                idx += 1
                if idx >= length:
                    break
        if idx >= length:
            break
    return ''.join(bitstream)

# === CRYPTO ===
def generate_key():
    return get_random_bytes(KEY_SIZE)

def aes_encrypt(data, key):
    iv = get_random_bytes(AES_BLOCK_SIZE)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return iv + cipher.encrypt(pad(data, AES_BLOCK_SIZE))

def aes_decrypt(data, key):
    iv, enc = data[:AES_BLOCK_SIZE], data[AES_BLOCK_SIZE:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(enc), AES_BLOCK_SIZE)

# === UTILITY ===
def extract_frame_list():
    return sorted(f for f in os.listdir(FRAME_DIR) if f.startswith("frame_"))

# === EMBED ===
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
    iv = encrypted[:AES_BLOCK_SIZE]
    encrypted_data = encrypted[AES_BLOCK_SIZE:]
    ecc_encoded = bytes(rs.encode(encrypted_data))
    with open(DEBUG_ENCRYPTED, "wb") as f:
        f.write(iv + ecc_encoded)
    with open(LEN_PATH, "w") as f:
        f.write(str(len(ecc_encoded)))
    subprocess.run(["ffmpeg", "-y", "-i", VIDEO_PATH, "-qscale:v", "1", f"{FRAME_DIR}/frame_%04d.png"], stdout=subprocess.DEVNULL)
    frames = extract_frame_list()
    payload_stream = iv + ecc_encoded
    bitstream = ''.join(format(b, '08b') for b in payload_stream)
    chunk_size = (BLOCK_SIZE**2 - 1) * QIM_AC_COEFFS
    for i, fname in enumerate(frames):
        start = i * chunk_size
        end = start + chunk_size
        if start >= len(bitstream):
            break
        bits = bitstream[start:end]
        frame_path = os.path.join(FRAME_DIR, fname)
        frame = cv2.imread(frame_path)
        stego = qim_embed_bitstream(frame, bits)
        cv2.imwrite(frame_path, stego)
        if i == 0:
            cv2.imwrite(STEGO_REFERENCE_FRAME, stego)  # Save reference for PSNR
    subprocess.run(["ffmpeg", "-y", "-framerate", "30", "-i", f"{FRAME_DIR}/frame_%04d.png", "-c:v", "ffv1", STEGO_VIDEO])
    print(f"[✓] Embedding complete. Total embedded bits: {len(bitstream)} (~{len(bitstream)//8} bytes)")

    # Optional: simulate compression for robustness testing
    compressed_video = "assets/stego_compressed.mp4"
    subprocess.run(["ffmpeg", "-y", "-i", STEGO_VIDEO, "-vcodec", "libx264", "-crf", "20", compressed_video], stdout=subprocess.DEVNULL)
    print(f"[Robustness] Compressed video saved as: {compressed_video}")

# === EXTRACT ===
def extract():
    print("[*] Starting extraction...")
    with open(KEY_PATH, "rb") as f:
        key = f.read()
    os.makedirs(FRAME_DIR, exist_ok=True)
    if not any(f.startswith("frame_") for f in os.listdir(FRAME_DIR)):
        subprocess.run(["ffmpeg", "-y", "-i", STEGO_VIDEO, f"{FRAME_DIR}/frame_%04d.png"], check=True)
    with open(LEN_PATH) as f:
        expected_len = int(f.read())
    total_bits = (AES_BLOCK_SIZE + expected_len) * 8
    frames = extract_frame_list()
    bitstream = ''
    for fname in frames:
        if len(bitstream) >= total_bits:
            break
        frame = cv2.imread(os.path.join(FRAME_DIR, fname))
        bits_needed = min((BLOCK_SIZE**2 - 1) * QIM_AC_COEFFS, total_bits - len(bitstream))
        bits = qim_extract_bitstream(frame, bits_needed)
        bitstream += bits
    if len(bitstream) < total_bits:
        print(f"[!] Only {len(bitstream)}/{total_bits} bits extracted — potential data loss.")
    byte_data = bytes(int(bitstream[i:i+8], 2) for i in range(0, len(bitstream), 8))
    iv = byte_data[:AES_BLOCK_SIZE]
    full_payload = byte_data[AES_BLOCK_SIZE:AES_BLOCK_SIZE + expected_len]
    with open(DEBUG_EXTRACTED, "wb") as f:
        f.write(full_payload)
    try:
        ecc_decoded = rs.decode(full_payload)[0]
    except reedsolo.ReedSolomonError:
        print("[!] ECC decode failed — corrupted ciphertext.")
        return
    try:
        decrypted = aes_decrypt(iv + ecc_decoded, key)
    except Exception as e:
        print("[!] AES decryption failed:", e)
        return
    data_len = unpack(">I", decrypted[:4])[0]
    compressed = decrypted[4:4 + data_len]
    checksum = decrypted[4 + data_len: 4 + data_len + 32]
    if sha256(compressed).digest() != checksum:
        print("[!] Checksum mismatch.")
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
        print("[!] Hash verification failed.")
        return
    print(f"[✓] SHA-3 Verified Hash: {hash_str}")
    bytes_to_image(img_data, IMAGE_SIZE, DECRYPTED_OUTPUT)
    print(f"[✓] Output saved to: {DECRYPTED_OUTPUT}")

if __name__ == "__main__":
    mode = input("[?] Mode (e=embed / x=extract): ").strip().lower()
    if mode == 'e':
        embed()
    elif mode == 'x':
        extract()
    else:
        print("[!] Invalid mode.")
