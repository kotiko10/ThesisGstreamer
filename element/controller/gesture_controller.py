import gi
import json
import subprocess
import time

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib

Gst.init(None)

CONFIG_FILE = "config.json"
COOLDOWN_TIME = 0.5

class GestureController:
    def __init__(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print(f"Error: {CONFIG_FILE} not found. Please create it.")
            self.config = {}

        self.last_action = None
        self.last_time = 0.0

        # FIXED PIPELINE: Added explicit caps and a second converter
        # v4l2src often needs a videoconvert before the filter to handle raw camera formats
        pipeline_str = (
            "v4l2src device=/dev/video0 ! videoconvert ! "
            "video/x-raw,format=RGB ! gesture_recognizer name=gr ! fakesink"
        )
        

        
        print(f"Launching pipeline: {pipeline_str}")
        self.pipeline = Gst.parse_launch(pipeline_str)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::element", self.on_element_message)
        bus.connect("message::error", self.on_error)

    def on_error(self, bus, message):
        err, debug = message.parse_error()
        print(f"GStreamer Error: {err.message}")
        print(f"Debug Info: {debug}")

    def on_element_message(self, bus, message):
        s = message.get_structure()
        if not s or s.get_name() != "gesture":
            return

        gesture_id = str(s.get_value("id"))
        action = self.config.get(gesture_id)

        if not action:
            return

        now = time.time()
        # Only trigger if action changed OR cooldown passed
        if action == self.last_action and (now - self.last_time) < COOLDOWN_TIME:
            return

        self.trigger_action(action)
        self.last_action = action
        self.last_time = now

    def trigger_action(self, action):
        key_map = {
            "Play/Pause": "XF86AudioPlay",
            "Next": "XF86AudioNext",
            "Previous": "XF86AudioPrev",
            "Volume Up": "XF86AudioRaiseVolume",
            "Volume Down": "XF86AudioLowerVolume",
            "Mute": "XF86AudioMute",
        }

        key = key_map.get(action)
        if not key:
            print(f"[UNKNOWN ACTION] {action}")
            return

        # check=False is good to prevent script crash if xdotool fails
        subprocess.run(["xdotool", "key", key], check=False)
        print(f"[ACTION] {action}")

    def run(self):
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("ERROR: Unable to set the pipeline to the playing state.")
            return

        print("Controller is running. Show your hand to the camera!")
        loop = GLib.MainLoop()
        try:
            loop.run()
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            self.pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    GestureController().run()