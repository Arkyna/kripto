import cv2
import os

def reencode_video(input_path, output_path):
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"[!] Tidak bisa membuka: {input_path}")

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if width <= 0 or height <= 0:
        raise ValueError(f"[!] Resolusi tidak valid: {width}x{height}")

    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print(f"[*] Re-encoding {input_path} -> {output_path} @ {width}x{height}, {fps} FPS")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)

    cap.release()
    out.release()
    print("[✓] Re-encoding selesai.")

if __name__ == "__main__":
    os.makedirs("assets", exist_ok=True)
    reencode_video("assets/video.mp4", "assets/video_clean.avi")
