#!/bin/bash -ex
# This is a shell script to set up the app on Linux

SCRIPT_DIR="$(dirname "$0")"

sudo apt install python3-tk # For tkinter
pip install -r "$SCRIPT_DIR/requirements_Linux.txt" --upgrade

python3 "$SCRIPT_DIR/setup.py"