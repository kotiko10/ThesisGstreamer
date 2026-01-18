#!/bin/bash
set -e

PLUGIN_DIR="$HOME/.gstreamer-1.0/plugins/python"

mkdir -p "$PLUGIN_DIR"
rm -rf "$PLUGIN_DIR"/*
cp plugin/gesture_recognizer.py "$PLUGIN_DIR/"

# Clear GStreamer's "Failure Cache"
rm -rf ~/.cache/gstreamer-1.0

echo "Testing plugin registration..."

# NO PYTHONPATH EXPORT HERE!
gst-inspect-1.0 gesture_recognizer