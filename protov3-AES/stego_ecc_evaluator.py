# === stego_ecc_evaluator.py ===
# Evaluation tool for AES + ECC + DCT-based steganography

import os
import cv2
import time
import numpy as np
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad
from hashlib import sha256
from scipy.fftpack import dct, idct
from math import log10
from ecc_crypto import generate_keys, ecc_encrypt
from utils import image_to_bytes

# === CONFIG ===
BLOCK_SIZE = 8
QIM_AC_COEFFS = 10
AES_BLOCK_SIZE = 16
KEY_SIZE = 32

OUTPUT_REPORT = "assets/evaluation_report.txt"

def log(msg):
    print(msg)
    with open(OUTPUT_REPORT, "a") as f:
        f.write(msg + "\n")

def clear_report():
    if os.path.exists(OUTPUT_REPORT):
        os.remove(OUTPUT_REPORT)

def measure_ecc_security():
    log("\n=== ECC SECURITY EVALUATION ===")
    attempts = 1000
    start = time.perf_counter()
    for _ in range(attempts):
        generate_keys()
    end = time.perf_counter()
    avg_time = (end - start) / attempts
    estimated_years = (2**256 * avg_time) / (3600 * 24 * 365)
    log(f"[ECC] Avg keygen time: {avg_time:.6f} sec")
    log(f"[ECC] Brute-force resistance: {estimated_years:.2e} years")

def measure_encryption_timing(data):
    log("\n=== ENCRYPTION TIMING ===")
    key = get_random_bytes(KEY_SIZE)
    start = time.perf_counter()
    aes = AES.new(key, AES.MODE_CBC)
    ciphertext = aes.encrypt(pad(data, AES_BLOCK_SIZE))
    end = time.perf_counter()
    aes_time = end - start

    ecc_pub, _ = generate_keys()
    start = time.perf_counter()
    ecc_encrypt(ciphertext, ecc_pub)
    end = time.perf_counter()
    ecc_time = end - start

    log(f"[Timing] AES Encryption : {aes_time:.6f} sec")
    log(f"[Timing] ECC Encryption : {ecc_time:.6f} sec")

def psnr(original, stego):
    mse = np.mean((original - stego) ** 2)
    return float('inf') if mse == 0 else 10 * log10(255.0 ** 2 / mse)

def evaluate_psnr(original_path, stego_path):
    log("\n=== PSNR ANALYSIS ===")
    original = cv2.imread(original_path, cv2.IMREAD_GRAYSCALE)
    stego = cv2.imread(stego_path, cv2.IMREAD_GRAYSCALE)

    if original is None:
        log(f"[ERROR] Cannot read: {original_path}")
        return
    if stego is None:
        log(f"[ERROR] Cannot read: {stego_path}")
        return

    value = psnr(original, stego)
    log(f"[PSNR] Value: {value:.2f} dB")

def estimate_capacity(frame_size):
    log("\n=== CAPACITY ESTIMATION ===")
    h, w = frame_size
    blocks = (h // BLOCK_SIZE) * (w // BLOCK_SIZE)
    capacity = blocks * QIM_AC_COEFFS
    log(f"[Capacity] {capacity} bits per frame (~{capacity // 8} bytes)")

def test_robustness(input_video, output_video, quality=20):
    log("\n=== ROBUSTNESS TEST ===")
    os.system(f"ffmpeg -y -i {input_video} -vcodec libx264 -crf {quality} {output_video} >nul 2>&1")
    log(f"[Robustness] Compressed saved to: {output_video}")

if __name__ == "__main__":
    clear_report()
    img_path = "assets/secret_image.png"
    original_frame = "assets/frames/frame_0001.png"
    stego_frame = "assets/frames/stego_frame_0001.png"

    image_data = image_to_bytes(img_path)

    measure_ecc_security()
    measure_encryption_timing(image_data)
    evaluate_psnr(original_frame, stego_frame)
    estimate_capacity((720, 1280))
    test_robustness("assets/stego_video.avi", "assets/stego_compressed.mp4")
    log("\n=== EVALUATION COMPLETE ===")
