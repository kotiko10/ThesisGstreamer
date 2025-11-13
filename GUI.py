import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import json
import time
import os
import sys

CONFIG_FILE = "config.json"
C_APP_PATH = "./app"
PYTHON_SCRIPT = "gesture_controller.py"

GESTURE_NAMES = [
    "Fist",
    "Thumb Up",
    "Index Point",
    "Two Fingers",
    "Four Fingers",
    "OK Sign"
]

AVAILABLE_ACTIONS = [
    "Play/Pause",
    "Next",
    "Previous",
    "Volume Up",
    "Volume Down",
    "Mute",
    "None"
]


class GestureGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gesture Controller GUI")
        self.root.geometry("900x650")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.c_process = None
        self.py_process = None
        self.running = False

        self.config = self.load_config()
        self.create_widgets()

        self.stop_event = threading.Event()
        self.log_thread = None

    def create_widgets(self):
        frame_top = tk.Frame(self.root)
        frame_top.pack(pady=10)

        self.btn_start = tk.Button(frame_top, text=" Start System", command=self.start_system, width=15)
        self.btn_start.grid(row=0, column=0, padx=5)

        self.btn_stop = tk.Button(frame_top, text=" Stop System", command=self.stop_system, width=15, state=tk.DISABLED)
        self.btn_stop.grid(row=0, column=1, padx=5)

        self.btn_save = tk.Button(frame_top, text=" Save Config", command=self.save_config, width=15)
        self.btn_save.grid(row=0, column=2, padx=5)

        # Gesture mappings
        mapping_frame = tk.LabelFrame(self.root, text=" Gesture Mappings", padx=10, pady=10)
        mapping_frame.pack(padx=10, pady=10, fill="x")

        self.dropdown_vars = []
        for i, gesture in enumerate(GESTURE_NAMES):
            tk.Label(mapping_frame, text=gesture, width=20, anchor="w").grid(row=i, column=0, sticky="w")
            var = tk.StringVar(value=self.config.get(gesture, "None"))
            dropdown = ttk.Combobox(mapping_frame, textvariable=var, values=AVAILABLE_ACTIONS, width=20, state="readonly")
            dropdown.grid(row=i, column=1, padx=10, pady=3)
            self.dropdown_vars.append((gesture, var))

        # Logs
        log_frame = tk.LabelFrame(self.root, text="Logs", padx=10, pady=10)
        log_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.log_text = tk.Text(log_frame, wrap="word", height=15, bg="#111", fg="#0f0")
        self.log_text.pack(fill="both", expand=True)
        self.log_text.insert(tk.END, "[INFO] Ready.\n")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_config(self):
        config_data = {gesture: var.get() for gesture, var in self.dropdown_vars}
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=2)
        self.log("[CONFIG] Saved gesture mappings.")

    def start_system(self):
        if self.running:
            self.log("[WARN] System already running.")
            return

        self.save_config()
        self.stop_event.clear()

        try:
            # Only local webcam, no remote option
            self.log("[INFO] Camera Source: LOCAL WEBCAM")

            self.c_process = subprocess.Popen(
                [C_APP_PATH],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0)

            time.sleep(1)

            self.py_process = subprocess.Popen(
                [sys.executable, PYTHON_SCRIPT],
                stdin=self.c_process.stdout,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                bufsize=0
            )

            self.running = True
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            self.log("[SYSTEM] Started C app and Python recognizer.")

            self.log_thread = threading.Thread(target=self.capture_logs, daemon=True)
            self.log_thread.start()

        except Exception as e:
            self.log(f"[ERROR] Failed to start system: {e}")

    def stop_system(self):
        self.stop_event.set()
        if self.py_process:
            self.py_process.terminate()
            self.py_process = None
        if self.c_process:
            self.c_process.terminate()
            self.c_process = None
        self.running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.log("[SYSTEM] Stopped all processes.")

    def on_close(self):
        self.stop_system()
        self.root.destroy()

    def capture_logs(self):
        def read_stream(stream, prefix):
            for line in iter(stream.readline, b''):
                if self.stop_event.is_set():
                    break
                try:
                    msg = line.decode(errors="ignore").strip()
                    if msg:
                        self.log(f"{prefix} {msg}")
                except Exception:
                    pass

        threads = []
        if self.c_process:
            threads.append(threading.Thread(target=read_stream, args=(self.c_process.stderr, "[C]"), daemon=True))
        if self.py_process:
            threads.append(threading.Thread(target=read_stream, args=(self.py_process.stderr, "[PY]"), daemon=True))
        for t in threads:
            t.start()

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        print(msg)


if __name__ == "__main__":
    root = tk.Tk()
    app = GestureGUI(root)
    root.mainloop()
