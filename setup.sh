#!/bin/bash -ex
# This is a shell script to set up the app on Linux

SCRIPT_DIR="$(dirname "$0")"

sudo apt-get update
sudo apt-get install xclip tesseract-ocr python3
pip install -r "$SCRIPT_DIR/requirements_Linux.txt" --upgrade

python3 "$SCRIPT_DIR/setup.py"