import cv2
import numpy as np

BLOCK_SIZE = 8
REDUNDANCY = 3  # Jumlah blok per posisi per bit
DCT_POSITIONS = [(3, 3), (4, 2), (2, 4)]  # Total 3 posisi → 9 blok per bit

def embed_data_into_frame(frame, data: bytes):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gray.shape
    data_bits = ''.join(f'{byte:08b}' for byte in data)
    idx = 0
    yx_iter = ((y, x) for y in range(0, h, BLOCK_SIZE) for x in range(0, w, BLOCK_SIZE))

    for bit in data_bits:
        bit = int(bit)
        for pos in DCT_POSITIONS:
            for _ in range(REDUNDANCY):
                try:
                    y, x = next(yx_iter)
                except StopIteration:
                    return cv2.cvtColor(np.clip(gray, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)

                block = gray[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE]
                if block.shape != (BLOCK_SIZE, BLOCK_SIZE):
                    continue
                dct = cv2.dct(block)
                coeff = np.floor(dct[pos])
                if int(coeff) % 2 != bit:
                    coeff += 1 if bit == 1 else -1
                dct[pos] = coeff
                gray[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE] = cv2.idct(dct)

        idx += 1

    return cv2.cvtColor(np.clip(gray, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)

def extract_data_from_frame(frame, num_bytes: int) -> bytes:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gray.shape
    total_bits = num_bytes * 8
    yx_iter = ((y, x) for y in range(0, h, BLOCK_SIZE) for x in range(0, w, BLOCK_SIZE))
    bits = []

    for _ in range(total_bits):
        position_votes = []
        for pos in DCT_POSITIONS:
            bit_votes = []
            for _ in range(REDUNDANCY):
                try:
                    y, x = next(yx_iter)
                except StopIteration:
                    break
                block = gray[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE]
                if block.shape != (BLOCK_SIZE, BLOCK_SIZE):
                    continue
                dct = cv2.dct(block)
                bit_votes.append(int(abs(dct[pos])) % 2)
            if bit_votes:
                vote = 1 if bit_votes.count(1) > bit_votes.count(0) else 0
                position_votes.append(vote)
        if position_votes:
            final_bit = 1 if position_votes.count(1) > position_votes.count(0) else 0
            bits.append(str(final_bit))

    return bytes([int(''.join(bits[i:i+8]), 2) for i in range(0, len(bits), 8)])
