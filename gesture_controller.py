import mediapipe as mp
import numpy as np
import subprocess
import time
import sys
import cv2

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_CHANNELS = 3
FRAME_SIZE = FRAME_WIDTH * FRAME_HEIGHT * FRAME_CHANNELS

COOLDOWN_TIME = 1.0
last_gesture_action = None
last_gesture_time = 0

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
    max_num_hands=1
)

def execute_media_control(action_id):
    global last_gesture_action, last_gesture_time
    current_time = time.time()
    if action_id == last_gesture_action and (current_time - last_gesture_time) < COOLDOWN_TIME:
        return
    command = None
    if action_id == 1:
        command = "XF86AudioPlay"
    elif action_id == 2:
        command = "XF86AudioNext"
    elif action_id == 3:
        command = "XF86AudioPrev"
    elif action_id == 4:
        command = "XF86AudioRaiseVolume"
    elif action_id == 5:
        command = "XF86AudioLowerVolume"
    elif action_id == 6:
        command = "XF86AudioMute"
    if command:
        try:
            subprocess.run(["xdotool", "key", command], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            sys.stderr.write(f"[PYTHON CONTROL] Executed: {command}\n")
            last_gesture_action = action_id
            last_gesture_time = current_time
        except subprocess.CalledProcessError:
            sys.stderr.write(f"[PYTHON ERROR] xdotool failed for command: {command}\n")

def get_gesture_id(hand_landmarks):
    if not hand_landmarks:
        return 0
    def is_finger_extended(tip_landmark, pip_landmark):
        return hand_landmarks.landmark[tip_landmark].y < hand_landmarks.landmark[pip_landmark].y
    fingers_extended = [
        hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].x < hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_IP].x,
        is_finger_extended(mp_hands.HandLandmark.INDEX_FINGER_TIP, mp_hands.HandLandmark.INDEX_FINGER_PIP),
        is_finger_extended(mp_hands.HandLandmark.MIDDLE_FINGER_TIP, mp_hands.HandLandmark.MIDDLE_FINGER_PIP),
        is_finger_extended(mp_hands.HandLandmark.RING_FINGER_TIP, mp_hands.HandLandmark.RING_FINGER_PIP),
        is_finger_extended(mp_hands.HandLandmark.PINKY_TIP, mp_hands.HandLandmark.PINKY_PIP),
    ]
    extended_count = sum(fingers_extended)
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    distance_sq = (thumb_tip.x - index_tip.x)**2 + (thumb_tip.y - index_tip.y)**2
    if distance_sq < 0.0025 and extended_count >= 3:
         return 6
    if extended_count <= 1 and not fingers_extended[0]:
        return 1
    if extended_count == 2 and fingers_extended[1] and fingers_extended[2]:
        return 4
    if extended_count == 4 and not fingers_extended[0]:
        return 5
    if extended_count == 1 and fingers_extended[0] and not fingers_extended[1]:
        return 2
    if extended_count == 1 and fingers_extended[1] and not fingers_extended[0]:
        return 3
    return 0

def process_frame(raw_data):
    try:
        np_array = np.frombuffer(raw_data, dtype=np.uint8).copy()
        image = np_array.reshape((FRAME_HEIGHT, FRAME_WIDTH, FRAME_CHANNELS))
        image.flags.writeable = False
        results = hands.process(image)
        image.flags.writeable = True
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                action_id = get_gesture_id(hand_landmarks)
                if action_id > 0:
                    execute_media_control(action_id)
    except Exception as e:
        sys.stderr.write(f"[PYTHON ERROR] Error processing frame: {e}\n")

def main():
    sys.stderr.write("Python Gesture Recognizer started. Reading frames from stdin buffer...\n")
    sys.stderr.write(f"Expected frame size: {FRAME_SIZE} bytes.\n")
    sys.stderr.write("Use Ctrl+C to stop both processes in the terminal.\n")
    try:
        while True:
            raw_frame_data = sys.stdin.buffer.read(FRAME_SIZE)
            if not raw_frame_data or len(raw_frame_data) != FRAME_SIZE:
                sys.stderr.write(f"[PYTHON] EOF or incomplete read ({0 if not raw_frame_data else len(raw_frame_data)}/{FRAME_SIZE} bytes). Shutting down.\n")
                break
            process_frame(raw_frame_data)
    except KeyboardInterrupt:
        sys.stderr.write("\nShutting down Python script.\n")
    except Exception as e:
        sys.stderr.write(f"[PYTHON CRITICAL ERROR] {e}\n")
    finally:
        hands.close()

if __name__ == "__main__":
    main()
