#!/bin/bash -ex
# This is a shell script to run the app on Linux

SCRIPT_DIR="$(dirname "$0")"
python3 "$SCRIPT_DIR/run.py"
