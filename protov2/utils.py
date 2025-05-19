from PIL import Image
import numpy as np

def image_to_bytes(path: str) -> bytes:
    img = Image.open(path).convert("L")
    return img.tobytes()

def bytes_to_image(data: bytes, size: tuple, out_path: str):
    img = Image.frombytes("L", size, data)
    img.save(out_path)

def split_bytes(data: bytes, chunk_size: int) -> list:
    return [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]

def join_bytes(chunks: list) -> bytes:
    return b''.join(chunks)
