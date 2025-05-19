from PIL import Image
import numpy as np
import os
import cv2

def resize_image(input_path, output_path, size=(48, 48)):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img = Image.open(input_path).convert("L")  # grayscale
    img_resized = img.resize(size)
    img_resized.save(output_path)
    print(f"[✓] Gambar dikonversi dan disimpan ke {output_path} dengan ukuran {size}")

def create_dummy_frame(path, size=(1248, 1248)):
    dummy = np.full((size[1], size[0], 3), 128, dtype=np.uint8)  # abu2
    cv2.imwrite(path, dummy)
    print(f"[✓] Dummy frame disimpan ke {path}")

if __name__ == "__main__":
    resize_image("assets/secret_image.png", "assets/secret_image_48.png")
    create_dummy_frame("assets/dummy_host_frame.png")  # <--- ini penting
