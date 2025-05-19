import cv2
from utils import split_bytes, join_bytes
from dct_stego import embed_data_into_frame, extract_data_from_frame

TEST_IMAGE = "assets/frames/frame_0001.png"
FRAME_OUT = "assets/frame_test_stego.png"
TEST_BYTES = b"THIS_IS_A_TEST" * 50  # small enough to avoid edge case
CAPACITY = len(TEST_BYTES)

# Load base image
frame = cv2.imread(TEST_IMAGE)
assert frame is not None, "Failed to load test image"

# Embed
stego_frame = embed_data_into_frame(frame.copy(), TEST_BYTES)
cv2.imwrite(FRAME_OUT, stego_frame)

# Extract
stego_loaded = cv2.imread(FRAME_OUT)
recovered = extract_data_from_frame(stego_loaded, CAPACITY)

if recovered[:len(TEST_BYTES)] == TEST_BYTES:
    print("[✓] Stego test passed")
else:
    print("[!] Stego test FAILED")
    for i in range(len(TEST_BYTES)):
        if recovered[i] != TEST_BYTES[i]:
            print(f"Mismatch at byte {i}: {recovered[i]} != {TEST_BYTES[i]}")
            break
