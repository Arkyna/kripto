from PIL import Image
import numpy as np

def image_to_bytes(image_path: str) -> bytes:
    """Load gambar dan ubah ke bytes (grayscale)."""
    img = Image.open(image_path).convert("L")  # convert ke grayscale
    return np.array(img).tobytes()

def bytes_to_image(byte_data: bytes, shape: tuple, output_path: str):
    """Ubah bytes menjadi gambar dan simpan."""
    arr = np.frombuffer(byte_data, dtype=np.uint8).reshape(shape)
    img = Image.fromarray(arr, mode="L")
    img.save(output_path)
