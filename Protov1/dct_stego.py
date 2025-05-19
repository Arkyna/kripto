import cv2
import numpy as np
import os

BLOCK_SIZE = 8

def embed_data_to_video(data: bytes, video_path: str, output_path: str):
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"[!] Video input tidak ditemukan: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"[!] Gagal membuka video: {video_path}")

    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    assert width > 0 and height > 0, "[!] Resolusi video tidak valid."
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not out.isOpened():
        raise RuntimeError(f"[!] Gagal membuka VideoWriter. Periksa codec atau path: {output_path}")

    ret, frame = cap.read()
    if not ret:
        raise RuntimeError("[!] Gagal membaca frame pertama.")

    print("[*] Menyisipkan data ke frame pertama...")
    stego_frame = embed_data_into_frame(frame, data)
    out.write(stego_frame)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)

    cap.release()
    out.release()
    print("[✓] Proses embed selesai. Video disimpan ke:", output_path)

def embed_data_into_frame(frame, data: bytes):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gray.shape
    data_bits = ''.join(f'{byte:08b}' for byte in data)
    idx = 0

    for y in range(0, h, BLOCK_SIZE):
        for x in range(0, w, BLOCK_SIZE):
            if idx >= len(data_bits):
                break
            block = gray[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE]
            if block.shape != (BLOCK_SIZE, BLOCK_SIZE):
                continue

            dct_block = cv2.dct(block)
            bit = int(data_bits[idx])
            coeff = dct_block[4, 3]
            coeff = np.floor(coeff)
            if (int(coeff) % 2) != bit:
                coeff += 1 if bit == 1 else -1
            dct_block[4, 3] = coeff
            gray[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE] = cv2.idct(dct_block)
            idx += 1

    print(f"[*] Total bit disisipkan: {idx} dari {len(data_bits)}")
    result = cv2.cvtColor(np.clip(gray, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    return result

def extract_data_from_video(stego_video_path: str, num_bytes: int) -> bytes:
    cap = cv2.VideoCapture(stego_video_path)
    if not cap.isOpened():
        raise RuntimeError(f"[!] Gagal membuka video stego: {stego_video_path}")

    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError("[!] Gagal membaca frame pertama dari stego video.")

    return extract_data_from_frame(frame, num_bytes)

def extract_data_from_frame(frame, num_bytes: int) -> bytes:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gray.shape
    bits = ""
    needed_bits = num_bytes * 8
    idx = 0

    for y in range(0, h, BLOCK_SIZE):
        for x in range(0, w, BLOCK_SIZE):
            if idx >= needed_bits:
                break
            block = gray[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE]
            if block.shape != (BLOCK_SIZE, BLOCK_SIZE):
                continue

            dct_block = cv2.dct(block)
            coeff = dct_block[4, 3]
            bit = int(abs(coeff)) % 2
            bits += str(bit)
            idx += 1

    print(f"[*] Total bit diekstrak: {idx} dari {needed_bits}")
    return bytes([int(bits[i:i+8], 2) for i in range(0, len(bits), 8)])
