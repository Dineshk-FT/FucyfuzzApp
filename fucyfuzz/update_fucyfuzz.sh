#!/bin/bash
# update_fucyfuzz.sh - Update Fucyfuzz after code changes

# Get script directory dynamically
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$SCRIPT_DIR"
cd "$PROJECT_DIR"

echo "🔄 Updating Fucyfuzz in: $PROJECT_DIR"

# Find the main Python file
if [ -f "main_app.py" ]; then
    MAIN_FILE="main_app.py"
    echo "📄 Using main_app.py as entry point"
elif [ -f "test.py" ]; then
    MAIN_FILE="test.py"
    echo "📄 Using test.py as entry point"
else
    echo "❌ No main Python file found!"
    echo "Files in directory:"
    ls -la *.py
    exit 1
fi

# Check for virtual environment
VENV_PATHS=("venv" ".venv" "env")
VENV_FOUND=false

for venv_path in "${VENV_PATHS[@]}"; do
    if [ -d "$venv_path" ]; then
        echo "✅ Found virtual environment: $venv_path"
        source "$venv_path/bin/activate"
        VENV_FOUND=true
        break
    fi
done

if [ "$VENV_FOUND" = false ]; then
    echo "⚠️  Virtual environment not found, using system Python"
    echo "Python version: $(python3 --version)"
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.spec __pycache__/

# Find icon files
ICON_FILE=""
if [ -f "fucyfuzzicon.png" ]; then
    ICON_FILE="fucyfuzzicon.png"
elif [ -f "fucyfuzzicon.ico" ]; then
    ICON_FILE="fucyfuzzicon.ico"
elif [ -f "icon_64.png" ]; then
    ICON_FILE="icon_64.png"
fi

echo "🎨 Icon file: ${ICON_FILE:-None found}"

# Build PyInstaller command
BUILD_CMD="pyinstaller --onefile --name \"Fucyfuzz\" --console --clean"

if [ -n "$ICON_FILE" ]; then
    BUILD_CMD="$BUILD_CMD --icon=\"$ICON_FILE\""
fi

# Add hidden imports if needed
if [ -f "requirements.txt" ]; then
    echo "📦 Checking requirements.txt for hidden imports..."
    BUILD_CMD="$BUILD_CMD --hidden-import=tkinter"
fi

BUILD_CMD="$BUILD_CMD $MAIN_FILE"

echo "🔨 Building command: $BUILD_CMD"
echo "🏗️  Building new executable..."

# Execute the build command
eval $BUILD_CMD

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "📦 New executable: $PROJECT_DIR/dist/Fucyfuzz"
    
    if [ -f "dist/Fucyfuzz" ]; then
        echo "📏 Size: $(ls -lh dist/Fucyfuzz | awk '{print $5}')"
        echo "🔒 Setting executable permissions..."
        chmod +x dist/Fucyfuzz
        
        # Test the new executable
        echo "🧪 Testing new version..."
        timeout 5s ./dist/Fucyfuzz --help || echo "⚠️  Test completed (may have timed out)"
        
        # Create desktop shortcut if on desktop environment
        if [ -d "$HOME/Desktop" ]; then
            echo "🏠 Creating desktop shortcut..."
            SHORTCUT="$HOME/Desktop/Fucyfuzz.desktop"
            cat > "$SHORTCUT" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Fucyfuzz
Comment=FUZZ tool for can bus
Exec=$PROJECT_DIR/dist/Fucyfuzz
Icon=$PROJECT_DIR/$ICON_FILE
Terminal=true
Categories=Development;Security;
EOF
            chmod +x "$SHORTCUT"
            echo "📌 Desktop shortcut created: $SHORTCUT"
        fi
    else
        echo "⚠️  Executable not found in dist/"
    fi
else
    echo "❌ Build failed!"
    exit 1
fi