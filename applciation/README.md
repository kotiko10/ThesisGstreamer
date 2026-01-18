# 🎮 GStreamer + MediaPipe Gesture Controller

This project connects a **C-based GStreamer video capture application** with a **Python-based gesture recognizer** built using **MediaPipe**.  
The system captures live webcam frames with GStreamer, pipes them into Python via `stdin`, and executes **media control commands** (Play/Pause, Next, Previous, Volume Up/Down, Mute) based on detected hand gestures.

---

## 🧩 Project Overview

- **C Program (`gstreamer_controller.c`)**
  - Uses GStreamer to capture frames from the webcam (`v4l2src`)
  - Converts video frames to RGB
  - Sends raw frames to `stdout` (pipe) for the Python program
  - Optionally displays a live preview window

- **Python Program (`gesture_controller.py`)**
  - Reads raw RGB frames from `stdin`
  - Uses MediaPipe Hands to detect gestures
  - Maps gestures to media control actions
  - Executes system media keys via `xdotool`

---

## 🛠️ Requirements

### 🐧 Platform
- **Linux (tested on Arch & Ubuntu)**  
  (Windows and macOS are not supported due to the use of `xdotool` and GStreamer pipeline specifics.)

---

## ⚙️ Dependencies

### System Packages
Install the following dependencies:

#### **Arch Linux**
```bash
sudo pacman -S base-devel gcc gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-libav glib2
yay -S python-mediapipe python-opencv xdotool

```

### ubuntu and debian based distors

```bash
sudo apt update
sudo apt install -y build-essential gcc \
    gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad gstreamer1.0-libav libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev libglib2.0-dev python3-opencv xdotool python3-pip
pip install mediapipe numpy
```

## compile the C program to capture webcam input
wanring make sure you have the gstremaer installed with all dependacies
```bash
gcc gstreamer_controller.c -o app $(pkg-config --cflags --libs gstreamer-1.0 gstreamer-app-1.0 gstreamer-video-1.0 glib-2.0)
```
This will generate an executable named app.

## Running the Application
Run both programs in a single command pipeline:

```bash
./app | python3 gesture_controller.py
```

the output should look like this

```bash
GStreamer Controller running with preview. Framesize: 921600 bytes.
[GSTREAMER INFO] Pipeline is now playing.
Python Gesture Recognizer started. Reading frames from stdin buffer...
Expected frame size: 921600 bytes.
```


TODO add gesture table what each gestrue does in the begineing wihtou modifications from the user