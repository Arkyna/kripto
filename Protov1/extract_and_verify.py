from ecc_crypto import ecc_decrypt
from hash_util import get_sha3_hash, verify_hash
from utils import bytes_to_image
from dct_stego import extract_data_from_video
from ecdsa import SigningKey

# Konfigurasi input/output
STEGO_VIDEO_PATH = "assets/stego_output.avi"
DECRYPTED_IMAGE_PATH = "assets/decrypted_image.png"
PRIVATE_KEY_PATH = "assets/private_key.pem"
IMAGE_SHAPE = (48, 48)
ENCRYPTED_DATA_LENGTH = 48 * 48
HASH_LENGTH = 64  # Panjang karakter SHA-3 hash saat di-encode

def main():
    print("[*] Mengekstrak data dari stego video...")
    total_bytes = ENCRYPTED_DATA_LENGTH + HASH_LENGTH
    extracted = extract_data_from_video(STEGO_VIDEO_PATH, total_bytes)

    encrypted_data = extracted[:ENCRYPTED_DATA_LENGTH]
    received_hash_bytes = extracted[ENCRYPTED_DATA_LENGTH:]
    received_hash = received_hash_bytes.decode(errors='ignore')

    print(f"[*] Hash yang diterima: {received_hash}")
    print(f"[*] Hash yang seharusnya: {get_sha3_hash(encrypted_data)}")

    # Simpan hasil ekstraksi mentah untuk diperiksa
    with open("assets/debug_extracted.bin", "wb") as f:
        f.write(encrypted_data)

    print(f"[*] 10 byte pertama hasil ekstraksi: {list(encrypted_data[:10])}")


    # Verifikasi integritas
    print("[*] Verifikasi integritas data...")
    if not verify_hash(encrypted_data, received_hash):
        print("[!] VERIFIKASI GAGAL: Data telah dimodifikasi atau rusak!")
        return
    print("[✓] Hash cocok. Data valid.")

    # Load private key dari file
    print("[*] Memuat private key...")
    with open(PRIVATE_KEY_PATH, "rb") as f:
        private_key = SigningKey.from_pem(f.read())

    # Dekripsi dan simpan gambar
    print("[*] Mendekripsi data dan menyimpan gambar...")
    decrypted = ecc_decrypt(encrypted_data, private_key)
    bytes_to_image(decrypted, IMAGE_SHAPE, DECRYPTED_IMAGE_PATH)
    print("[✓] Gambar berhasil didekripsi dan disimpan.")

if __name__ == "__main__":
    main()
