import cv2
import mediapipe as mp
import time
import csv
import psutil
from datetime import datetime

mp_hands = mp.solutions.hands

def create_log_filename(prefix):
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{prefix}_{ts}.csv"

def log_setup(filename):
    f = open(filename, "w", newline="")
    writer = csv.writer(f)
    writer.writerow([
        "timestamp", "frame", "processing_ms", "fps",
        "cpu_percent", "ram_mb", "num_hands"
    ])
    return f, writer


def main():
    cap = cv2.VideoCapture(0)
    hands = mp_hands.Hands(
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    log_filename = create_log_filename("mediapipe_log")
    log_file, logger = log_setup(log_filename)
    print(f"Logging to: {log_filename}")

    frame_id = 0
    prev_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            start = time.time()
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)
            end = time.time()

            processing_ms = (end - start) * 1000
            now = time.time()
            fps = 1 / (now - prev_time)
            prev_time = now

            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().used / (1024 * 1024)
            num_hands = len(result.multi_hand_landmarks) if result.multi_hand_landmarks else 0

            logger.writerow([
                datetime.now().isoformat(),
                frame_id, round(processing_ms, 3), round(fps, 2),
                cpu, round(ram, 1), num_hands
            ])

            frame_id += 1

            cv2.imshow("MediaPipe Benchmark", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break

    finally:
        log_file.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
