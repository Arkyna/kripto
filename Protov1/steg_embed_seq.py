import os
import cv2
from ecc_crypto import generate_keys, ecc_encrypt
from hash_util import get_sha3_hash
from utils import image_to_bytes
from dct_stego import embed_data_into_frame
import numpy as np

IMG_PATH = "assets/secret_image_48.png"
HOST_FRAME = "assets/dummy_host_frame.png"
FRAMES_DIR = "assets/frames"
FRAME_OUT_FMT = os.path.join(FRAMES_DIR, "frame_%04d.png")
FRAME_COUNT = 1  # kita hanya butuh 1 frame

def main():
    print("[*] Membuat direktori frame...")
    os.makedirs(FRAMES_DIR, exist_ok=True)

    print("[*] Load dan enkripsi gambar...")
    data = image_to_bytes(IMG_PATH)
    priv, pub = generate_keys()
    encrypted = ecc_encrypt(data, pub)
    data_hash = get_sha3_hash(encrypted).encode()
    payload = encrypted + data_hash

    print("[*] Menyisipkan ke frame...")
    host = cv2.imread(HOST_FRAME)
    stego = embed_data_into_frame(host, payload)

    print("[*] Menyimpan frame...")
    for i in range(FRAME_COUNT):
        frame_path = FRAME_OUT_FMT % i
        cv2.imwrite(frame_path, stego)

    print("[*] Simpan private key...")
    with open("assets/private_key.pem", "wb") as f:
        f.write(priv.to_pem())

    print("[✓] Selesai. Jalankan ffmpeg untuk gabung frame jadi video.")

if __name__ == "__main__":
    main()
