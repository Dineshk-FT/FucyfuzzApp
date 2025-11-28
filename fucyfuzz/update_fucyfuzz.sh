#!/bin/bash
# update_fucyfuzz.sh - Update Fucyfuzz after code changes

PROJECT_DIR="/home/fucy-can/FUCY/FucyFuzz/fucyfuzz"
cd "$PROJECT_DIR"

echo "🔄 Updating Fucyfuzz..."

# Activate virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  Virtual environment not found, using system Python"
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ *.spec

# Rebuild the executable
echo "Building new executable..."
pyinstaller --onefile \
    --name "Fucyfuzz" \
    --icon="fucyfuzzicon.png" \
    --console \
    --clean \
    test.py

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "📦 New executable: dist/Fucyfuzz"
    echo "📏 Size: $(ls -lh dist/Fucyfuzz | awk '{print $5}')"
    
    # Test the new executable
    echo "🧪 Testing new version..."
    ./dist/Fucyfuzz --help
else
    echo "❌ Build failed!"
    exit 1
fi
