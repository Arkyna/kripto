from ecc_crypto import generate_keys, ecc_encrypt
from hash_util import get_sha3_hash
from utils import image_to_bytes
from dct_stego import embed_data_to_video

# Path input/output
IMG_PATH = "assets/secret_image_48.png"
VIDEO_PATH = "assets/video_clean.avi"
STEGO_VIDEO_OUT = "assets/stego_output.avi"

def main():
    # 1. Load and convert image to bytes
    print("[*] Loading and converting image...")
    image_bytes = image_to_bytes(IMG_PATH)

    # 2. Generate ECC key pair
    print("[*] Generating ECC key pair...")
    private_key, public_key = generate_keys()

    # Save private key to file
    with open("assets/private_key.pem", "wb") as f:
        f.write(private_key.to_pem())

    # (opsional) save public key kalau mau verifikasi lintas sistem
    with open("assets/public_key.pem", "wb") as f:
        f.write(public_key.to_pem())

    # 3. Encrypt image bytes
    print("[*] Encrypting image with ECC...")
    encrypted_bytes = ecc_encrypt(image_bytes, public_key)

    # 4. Hash encrypted data
    print("[*] Hashing encrypted data with SHA-3...")
    data_hash = get_sha3_hash(encrypted_bytes)

    # 5. Embed encrypted data + hash into video using DCT
    print("[*] Embedding data into video using DCT...")
    embed_data_to_video(encrypted_bytes + data_hash.encode(), VIDEO_PATH, STEGO_VIDEO_OUT)

    print("[✓] Embedding complete.")

        # Simpan encrypted_bytes ke file untuk pembanding
    with open("assets/debug_encrypted.bin", "wb") as f:
        f.write(encrypted_bytes)

    print(f"[*] 10 byte pertama hasil enkripsi: {list(encrypted_bytes[:10])}")


if __name__ == "__main__":
    main()
