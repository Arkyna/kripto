import cv2
from dct_stego import embed_data_into_frame, extract_data_from_frame
from ecc_crypto import generate_keys, ecc_encrypt
from hash_util import get_sha3_hash
from utils import image_to_bytes, bytes_to_image
import os

IMG_PATH = "assets/secret_image_48.png"
STEGO_PNG = "assets/stego_frame.png"
DECRYPTED_OUT = "assets/decrypted_image.png"
IMAGE_SHAPE = (48, 48)

def main():
    # 1. Load dan convert gambar
    print("[*] Load image...")
    image_bytes = image_to_bytes(IMG_PATH)

    # 2. Enkripsi dengan ECC
    print("[*] Encrypting...")
    private_key, public_key = generate_keys()
    encrypted = ecc_encrypt(image_bytes, public_key)
    hashed = get_sha3_hash(encrypted).encode()
    payload = encrypted + hashed

    # 3. Load frame kosong dari PNG dummy
    dummy = cv2.imread("assets/dummy_host_frame.png")  # Buat gambar blank dengan resolusi tinggi
    stego = embed_data_into_frame(dummy, payload)

    # 4. Simpan stego ke PNG lossless
    os.makedirs("assets", exist_ok=True)
    cv2.imwrite(STEGO_PNG, stego)
    print("[✓] Stego frame saved.")

    # 5. Load kembali dan ekstrak
    print("[*] Re-loading and extracting...")
    reloaded = cv2.imread(STEGO_PNG)
    extracted = extract_data_from_frame(reloaded, len(payload))

    enc_out = extracted[:len(encrypted)]
    hash_out = extracted[len(encrypted):].decode(errors="ignore")

    print("[*] Hash expected:", get_sha3_hash(enc_out))
    print("[*] Hash found:   ", hash_out)

    if get_sha3_hash(enc_out) == hash_out:
        print("[✓] SUCCESS: Hash matches. Data intact.")
    else:
        print("[!] FAIL: Hash mismatch. Data corrupted.")

if __name__ == "__main__":
    main()
