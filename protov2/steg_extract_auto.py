import os
import cv2
import subprocess
from struct import unpack
from ecc_crypto import ecc_decrypt
from hash_util import verify_hash
from utils import join_bytes, bytes_to_image
from dct_stego import extract_data_from_frame
from ecdsa import SigningKey

# --- Configuration ---
FRAME_DIR = "assets/frames"
STEGO_VIDEO = "assets/stego_video.avi"
PRIVATE_KEY_PATH = "assets/private_key.pem"
DECRYPTED_IMAGE_PATH = "assets/decrypted_output.png"
IMAGE_SIZE = (120, 120)  # Must match original image
HASH_LEN = 64  # SHA3-256 hash = 64 ASCII characters

# --- Step 1: Ensure frame directory exists ---
os.makedirs(FRAME_DIR, exist_ok=True)

# --- Step 2: Extract frames from video if not already done ---
if not any(fname.startswith("frame_") for fname in os.listdir(FRAME_DIR)):
    print("[*] Extracting frames from stego video...")
    subprocess.run([
        "ffmpeg", "-y", "-i", STEGO_VIDEO, f"{FRAME_DIR}/frame_%04d.png"
    ], check=True)

# --- Step 3: Load first frame to get capacity info ---
print("[*] Loading frames...")
frame_files = sorted([f for f in os.listdir(FRAME_DIR) if f.startswith("frame_")])
if not frame_files:
    raise RuntimeError("No frames found in frame directory.")

first_frame = cv2.imread(os.path.join(FRAME_DIR, frame_files[0]))
if first_frame is None:
    raise RuntimeError("Failed to load the first frame.")

REDUNDANCY = 3  # Sesuai dengan dct_stego.py baru
POSITIONS = 3   # Jumlah posisi DCT yang digunakan

h, w = first_frame.shape[:2]
blocks_per_frame = (h // 8) * (w // 8)
bits_per_frame = blocks_per_frame // (REDUNDANCY * POSITIONS)
bytes_per_frame = bits_per_frame // 8
print(f"[*] Each frame can carry up to {bytes_per_frame} bytes using {POSITIONS} DCT positions with redundancy {REDUNDANCY}.")

# --- Step 4: Extract embedded data from frames ---
print("[*] Extracting embedded data from frames...")

with open("payload_length.txt", "r") as f:
    expected_len = int(f.read())

chunks = []
collected = 0
for f in frame_files:
    path = os.path.join(FRAME_DIR, f)
    frame = cv2.imread(path)
    if frame is None:
        continue
    chunk = extract_data_from_frame(frame, bytes_per_frame)

    needed = expected_len - collected
    if needed <= 0:
        break

    chunk = chunk[:needed]
    chunks.append(chunk)
    collected += len(chunk)

full_data = join_bytes(chunks)

with open("debug_extracted.bin", "wb") as f:
    f.write(full_data)

# --- Step 5: Decrypt using ECC ---
print("[*] Decrypting with ECC...")
with open(PRIVATE_KEY_PATH, "rb") as f:
    private_key = SigningKey.from_pem(f.read())

try:
    decrypted = ecc_decrypt(full_data, private_key)
except Exception as e:
    print(f"[!] ECC decryption failed: {e}")
    exit(1)

# --- Debugging output after decryption ---
with open("debug_decrypted.bin", "wb") as f:
    f.write(decrypted)
print(f"[*] Decrypted data length: {len(decrypted)} bytes")

# --- Step 6: Parse decrypted data ---
data_len = unpack(">I", decrypted[:4])[0]
combined = decrypted[4:4 + data_len]
image_data = combined[:-HASH_LEN]
hash_bytes = combined[-HASH_LEN:]

try:
    hash_str = hash_bytes.decode("ascii")
except UnicodeDecodeError:
    print("[!] ERROR: Extracted hash is not valid ASCII.")
    exit(1)

# --- Step 7: Verify hash ---
print("[*] Verifying hash...")
if not verify_hash(image_data, hash_str):
    print("[!] ERROR: Data integrity check failed.")
    exit(1)

print("[✓] Hash verified.")

# --- Step 8: Reconstruct image ---
print("[*] Reconstructing image...")
bytes_to_image(image_data, IMAGE_SIZE, DECRYPTED_IMAGE_PATH)
print("[✓] Image recovered:", DECRYPTED_IMAGE_PATH)
