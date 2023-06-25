#!/bin/bash -ex
# This is a shell script to set up the app on Linux

SCRIPT_DIR="$(dirname "$0")"

sudo apt update
sudo apt install xclip tesseract-ocr python3 python3-tk
pip install -r "$SCRIPT_DIR/requirements_Linux.txt" --upgrade

python3 "$SCRIPT_DIR/setup.py"