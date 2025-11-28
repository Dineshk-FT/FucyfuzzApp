#!/bin/bash
# simple_build.sh

cd /home/fucy-can/FUCY/fucyfuzz
source venv/bin/activate

echo "Building Fucyfuzz..."
pyinstaller --onefile \
    --name "Fucyfuzz" \
    --icon="fucyfuzzicon.ico" \
    --console \
    --clean \
    test.py

echo "Build complete! Check dist/Fucyfuzz"