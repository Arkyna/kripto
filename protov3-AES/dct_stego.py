# === dct_stego.py ===
# Refined DCT-based steganography with better precision and diagnostics

import numpy as np
import cv2
from scipy.fftpack import dct, idct

BLOCK_SIZE = 8
EMBED_POS = [10, 20, 30]  # safer mid-band DCT indices

# --- DCT Helpers ---
def _block_dct(channel):
    return dct(dct(channel.T, norm='ortho').T, norm='ortho')

def _block_idct(channel):
    return idct(idct(channel.T, norm='ortho').T, norm='ortho')

def _embed_byte_in_block(block, byte):
    flat = block.flatten()
    flat = flat.astype(np.float64)  # higher precision for stability

    flat[EMBED_POS[0]] = (int(flat[EMBED_POS[0]]) & ~0x07) | (byte & 0x07)
    flat[EMBED_POS[1]] = (int(flat[EMBED_POS[1]]) & ~0x07) | ((byte >> 3) & 0x07)
    flat[EMBED_POS[2]] = (int(flat[EMBED_POS[2]]) & ~0x03) | ((byte >> 6) & 0x03)

    return flat.reshape((BLOCK_SIZE, BLOCK_SIZE))

def _extract_byte_from_block(block):
    flat = block.flatten()
    b0 = int(flat[EMBED_POS[0]]) & 0x07
    b1 = (int(flat[EMBED_POS[1]]) & 0x07) << 3
    b2 = (int(flat[EMBED_POS[2]]) & 0x03) << 6
    return b0 | b1 | b2

# --- Core Functions ---
def embed_data_into_frame(frame, data, redundancy=3):
    height, width, _ = frame.shape
    blocks_y = height // BLOCK_SIZE
    blocks_x = width // BLOCK_SIZE
    total_blocks = blocks_y * blocks_x

    if len(data) * redundancy > total_blocks:
        raise ValueError("Data too large for frame")

    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    y_channel = ycrcb[:, :, 0].astype(np.float32)

    data_index = 0
    for i in range(blocks_y):
        for j in range(blocks_x):
            if data_index // redundancy >= len(data):
                break
            block = y_channel[i*BLOCK_SIZE:(i+1)*BLOCK_SIZE, j*BLOCK_SIZE:(j+1)*BLOCK_SIZE]
            dct_block = _block_dct(block)
            byte = data[data_index // redundancy]
            embedded = _embed_byte_in_block(dct_block, byte)
            y_channel[i*BLOCK_SIZE:(i+1)*BLOCK_SIZE, j*BLOCK_SIZE:(j+1)*BLOCK_SIZE] = _block_idct(embedded)
            data_index += 1

    y_channel = np.clip(y_channel, 0, 255).astype(np.uint8)
    ycrcb[:, :, 0] = y_channel
    return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

def extract_data_from_frame(frame, length, redundancy=3):
    height, width, _ = frame.shape
    blocks_y = height // BLOCK_SIZE
    blocks_x = width // BLOCK_SIZE
    total_blocks = blocks_y * blocks_x

    if length * redundancy > total_blocks:
        raise ValueError("Requested length too large for frame")

    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    y_channel = ycrcb[:, :, 0].astype(np.float32)

    extracted = []
    for i in range(blocks_y):
        for j in range(blocks_x):
            block = y_channel[i*BLOCK_SIZE:(i+1)*BLOCK_SIZE, j*BLOCK_SIZE:(j+1)*BLOCK_SIZE]
            dct_block = _block_dct(block)
            extracted.append(_extract_byte_from_block(dct_block))
            if len(extracted) == length * redundancy:
                break
        if len(extracted) == length * redundancy:
            break

    majority = []
    for i in range(length):
        group = extracted[i*redundancy:(i+1)*redundancy]
        vote = max(set(group), key=group.count)
        majority.append(vote)

    return bytes(majority)
