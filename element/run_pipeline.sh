#!/bin/bash

GST_DEBUG=2 gst-launch-1.0 \
  v4l2src ! videoconvert ! video/x-raw,format=RGB ! \
  gesture_recognizer cooldown=1.0 ! \
  fakesink
