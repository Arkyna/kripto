import os
import cv2
import subprocess
from struct import pack
from aes_crypto import generate_key_iv, aes_encrypt
from hash_util import get_sha3_hash
from utils import image_to_bytes, split_bytes
from dct_stego import embed_data_into_frame

# === PATH SETUP ===
IMG_PATH = "assets/secret_image.png"
VIDEO_PATH = "assets/video.mp4"
FRAME_DIR = "assets/frames"
STEGO_VIDEO = "assets/stego_video.avi"
PRIVATE_KEY_PATH = "assets/private_key.pem"

# === PREP ===
os.makedirs(FRAME_DIR, exist_ok=True)
print("[*] Loading qqqqimage and converting to bytes...")
image_bytes = image_to_bytes(IMG_PATH)
hash_str = get_sha3_hash(image_bytes)
combined_bytes = image_bytes + hash_str.encode()  # 14464 bytes

# === Tambahkan panjang data sebagai prefix (4-byte big-endian) ===
data_length = len(combined_bytes)
length_prefix = pack(">I", data_length)
final_payload = length_prefix + combined_bytes

print("[*] Generating AES key and IV...")
key, iv = generate_key_iv()
with open("aes_key.bin", "wb") as f:
    f.write(key)

print("[*] Encrypting image data with AES...")
encrypted_bytes = aes_encrypt(final_payload, key, iv)

with open("payload_length.txt", "w") as f:
    f.write(str(len(encrypted_bytes)))

with open("debug_encrypted_reference.bin", "wb") as f:
    f.write(encrypted_bytes)
print("[*] Saved encrypted reference for validation.")

# === FRAME EXTRACTION ===
print("[*] Extracting frames from video...")
subprocess.run([
    "ffmpeg", "-y", "-i", VIDEO_PATH, "-qscale:v", "1", f"{FRAME_DIR}/frame_%04d.png"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

frame_files = sorted([f for f in os.listdir(FRAME_DIR) if f.startswith("frame_")])
if not frame_files:
    raise RuntimeError("No frames found in the frame directory.")

first_frame = cv2.imread(os.path.join(FRAME_DIR, frame_files[0]))
if first_frame is None:
    raise RuntimeError("Failed to load the first frame.")

REDUNDANCY = 3  # Cocokkan dengan dct_stego.py
POSITIONS = 3

h, w = first_frame.shape[:2]
blocks_per_frame = (h // 8) * (w // 8)
bits_per_frame = blocks_per_frame // (REDUNDANCY * POSITIONS)
bytes_per_frame = bits_per_frame // 8
print(f"[*] Each frame can carry up to {bytes_per_frame} bytes using {POSITIONS} DCT positions with redundancy {REDUNDANCY}.")


# === SPLIT + EMBED ===
chunks = split_bytes(encrypted_bytes, bytes_per_frame)
if len(chunks) > len(frame_files):
    raise ValueError(f"Insufficient video frames: Need {len(chunks)}, have {len(frame_files)}.")

print("[*] Embedding encrypted data into frames...")
for i, chunk in enumerate(chunks):
    path = os.path.join(FRAME_DIR, frame_files[i])
    frame = cv2.imread(path)
    stego = embed_data_into_frame(frame, chunk)
    cv2.imwrite(path, stego)

print("[*] Rebuilding stego video...")
subprocess.run([
    "ffmpeg", "-y", "-framerate", "30", "-i", f"{FRAME_DIR}/frame_%04d.png",
    "-c:v", "ffv1", STEGO_VIDEO
])

print("[✓] Embedding complete. Output saved to:", STEGO_VIDEO)
