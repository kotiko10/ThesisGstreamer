import gi
import time
import numpy as np
import cv2
import math

gi.require_version("Gst", "1.0")
gi.require_version("GstBase", "1.0")
from gi.repository import Gst, GstBase, GObject

CAPS_STR = "video/x-raw, format=(string)RGB, width=(int)[1, 2147483647], height=(int)[1, 2147483647], framerate=(fraction)[0/1, 2147483647/1]"

class GestureRecognizer(GstBase.BaseTransform):
    # GStreamer metadata requires: (Long-name, Classification, Description, Author)
    __gstmetadata__ = (
        "Hand Gesture Recognizer",
        "Filter/Effect/Video",
        "Detects hand gestures using OpenCV Convex Hull and convexity defects",
        "Konstantine Nebieridze 12",
    )

    __gsttemplates__ = (
    Gst.PadTemplate.new(
        "sink",
        Gst.PadDirection.SINK,
        Gst.PadPresence.ALWAYS,
        Gst.Caps.from_string(
            "video/x-raw,format=RGB,width=[1,4096],height=[1,2160],framerate=[0/1,120/1]"
            ),
        ),
    Gst.PadTemplate.new(
        "src",
        Gst.PadDirection.SRC,
        Gst.PadPresence.ALWAYS,
        Gst.Caps.from_string(
            "video/x-raw,format=RGB,width=[1,4096],height=[1,2160],framerate=[0/1,120/1]"
            ),
        ),
    )

    def __init__(self):
        super().__init__()
        self.cooldown = 1.0
        self.last_gesture_id = 0
        self.last_emit_time = 0.0
        self.width = 0
        self.height = 0

    def do_get_property(self, prop):
        if prop.name == "cooldown":
            return self.cooldown
        raise AttributeError("Unknown property")

    def do_set_property(self, prop, value):
        if prop.name == "cooldown":
            self.cooldown = value
        else:
            raise AttributeError("Unknown property")

    def do_set_caps(self, incaps, outcaps):
        s = incaps.get_structure(0)
        self.width = s.get_value("width")
        self.height = s.get_value("height")
        return True

    def _get_gesture_id(self, frame):
        # Convert RGB to Gray (GStreamer usually sends RGB)
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        blur = cv2.GaussianBlur(gray, (35, 35), 0)
        
        # Threshold to find hand (adjust if background is light)
        _, thresh = cv2.threshold(blur, 127, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return 0
            
        cnt = max(contours, key=lambda x: cv2.contourArea(x))
        if cv2.contourArea(cnt) < 5000:
            return 0

        hull_points = cv2.convexHull(cnt)
        hull_indices = cv2.convexHull(cnt, returnPoints=False)
        
        # We need at least 3 points for defects
        if len(hull_indices) < 3:
            return 0

        defects = cv2.convexityDefects(cnt, hull_indices)
        if defects is None:
            return 1 # Fist

        count_defects = 0
        for i in range(defects.shape[0]):
            s, e, f, d = defects[i, 0]
            start = tuple(cnt[s][0])
            end = tuple(cnt[e][0])
            far = tuple(cnt[f][0])

            a = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
            b = math.sqrt((far[0] - start[0])**2 + (far[1] - start[1])**2)
            c = math.sqrt((end[0] - far[0])**2 + (end[1] - far[1])**2)
            angle = math.acos((b**2 + c**2 - a**2) / (2*b*c)) * 57

            # Deep defects (valleys between fingers) usually have small angles
            if angle <= 90 and d > 1000: 
                count_defects += 1

        # Logic: N defects = N+1 fingers
        if count_defects == 0: return 1 # Fist
        if count_defects == 1: return 2 # Index/V
        if count_defects == 2: return 3 # Three fingers
        if count_defects == 3: return 4 # Four fingers
        if count_defects == 4: return 5 # Open Palm
        return 0

    def do_transform_ip(self, buffer):
        ok, map_info = buffer.map(Gst.MapFlags.READ | Gst.MapFlags.WRITE)
        if not ok:
            return Gst.FlowReturn.OK

        try:
            frame = np.ndarray(
                shape=(self.height, self.width, 3),
                dtype=np.uint8,
                buffer=map_info.data,
            )

            gesture_id = self._get_gesture_id(frame)

            now = time.time()
            if (gesture_id > 0 and gesture_id != self.last_gesture_id and 
                (now - self.last_emit_time) >= self.cooldown):
                self._emit_gesture(gesture_id)
                self.last_emit_time = now
                self.last_gesture_id = gesture_id

        finally:
            buffer.unmap(map_info)

        return Gst.FlowReturn.OK

    def _emit_gesture(self, gesture_id):
        bus = self.get_bus()
        if bus:
            s = Gst.Structure.new_empty("gesture")
            s.set_value("id", gesture_id)
            msg = Gst.Message.new_element(self, s)
            bus.post(msg)

# Registration logic
__gstplugin__ = (
    "gesture_recognizer",              # Plugin name
    "Hand gesture recognition plugin", # Description
    "1.0",                             # Version
    "LGPL",                            # License
    "gesture_recognizer",              # Source module
    "gesture_recognizer",              # Package
    "https://example.com",              # Origin
)

GObject.type_register(GestureRecognizer)
__gstelementfactory__ = (
    "gesture_recognizer",
    Gst.Rank.NONE,
    GestureRecognizer,
)