import cv2
from ecc_crypto import ecc_decrypt
from hash_util import get_sha3_hash, verify_hash
from utils import bytes_to_image
from dct_stego import extract_data_from_frame
from ecdsa import SigningKey

STEGO_FRAME = "assets/frames/frame_0000.png"
PRIVATE_KEY_FILE = "assets/private_key.pem"
IMAGE_SHAPE = (48, 48)
HASH_LEN = 64  # SHA3-256 hex
ENC_LEN = IMAGE_SHAPE[0] * IMAGE_SHAPE[1]
TOTAL = ENC_LEN + HASH_LEN

def main():
    print("[*] Load frame...")
    frame = cv2.imread(STEGO_FRAME)
    extracted = extract_data_from_frame(frame, TOTAL)

    encrypted = extracted[:ENC_LEN]
    hash_received = extracted[ENC_LEN:].decode(errors="ignore")

    print("[*] Hash ditemukan:", hash_received)
    print("[*] Hash dihitung :", get_sha3_hash(encrypted))

    if not verify_hash(encrypted, hash_received):
        print("[!] VERIFIKASI GAGAL: Data rusak.")
        return

    print("[*] Hash cocok. Memuat kunci privat...")
    with open(PRIVATE_KEY_FILE, "rb") as f:
        private_key = SigningKey.from_pem(f.read())

    decrypted = ecc_decrypt(encrypted, private_key)
    bytes_to_image(decrypted, IMAGE_SHAPE, "assets/decrypted_output.png")

    print("[✓] Gambar berhasil didekripsi dan disimpan.")

if __name__ == "__main__":
    main()
