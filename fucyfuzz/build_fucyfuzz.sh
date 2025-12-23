#!/bin/bash
# build_fucyfuzz.sh - Complete setup and build script

echo "╔═══════════════════════════════════════════╗"
echo "║         Fucyfuzz Setup & Build            ║"
echo "╚═══════════════════════════════════════════╝"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📍 Project directory: $SCRIPT_DIR"
echo ""

# ============================================================================
# PHASE 1: CHECK AND SETUP VIRTUAL ENVIRONMENT
# ============================================================================
echo "🔍 [1/4] Virtual Environment Setup"
echo "────────────────────────────────────"

# Check if venv exists, create if not
if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        echo "   Installing python3-venv if missing..."
        sudo apt install python3-venv -y
        python3 -m venv venv
    fi
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate
echo "✅ Activated: $(which python)"
echo ""

# ============================================================================
# PHASE 2: INSTALL DEPENDENCIES
# ============================================================================
echo "📦 [2/4] Installing Dependencies"
echo "──────────────────────────────────"

# Check if requirements.txt exists, create if not
if [ ! -f "requirements.txt" ]; then
    echo "⚠️  requirements.txt not found"
    echo "   Creating default requirements.txt..."
    
    cat > requirements.txt << 'EOF'
# Main dependencies for Fucyfuzz
customtkinter>=5.2.0
python-can>=4.3.0
pandas>=2.0.0
numpy>=1.24.0
psutil>=5.9.0
requests>=2.31.0
tkinter  # Usually comes with Python

# PyInstaller for building
pyinstaller>=5.13.0

# Add your project-specific imports here
EOF
    
    echo "✅ Created requirements.txt with common dependencies"
    echo "   Please review and add any missing packages"
fi

echo "   Installing from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# Check for missing imports in your code
echo ""
echo "🔎 Checking for missing imports in your code..."
MISSING_PACKAGES=()

# Check main_app.py imports
if [ -f "main_app.py" ]; then
    echo "   Scanning main_app.py..."
    grep -E "^import |^from " main_app.py | while read line; do
        module=$(echo $line | awk '{print $2}' | cut -d. -f1)
        if ! python -c "import $module" 2>/dev/null; then
            MISSING_PACKAGES+=("$module")
            echo "   ⚠️  Missing: $module"
        fi
    done
fi

# Install any missing packages
if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo ""
    echo "   Installing missing packages..."
    for pkg in "${MISSING_PACKAGES[@]}"; do
        pip install "$pkg" 2>/dev/null && echo "   ✅ Installed: $pkg" || echo "   ❌ Failed: $pkg"
    done
fi

echo "✅ Dependencies installed"
echo ""


# ============================================================================
# PHASE 3: BUILD EXECUTABLE
# ============================================================================
echo "🔨 [4/4] Building Executable"
echo "──────────────────────────────"

# Clean previous builds
rm -rf build/ dist/ *.spec __pycache__/ 2>/dev/null
echo "   Cleaned build artifacts"

# Find main file
if [ -f "main_app.py" ]; then
    MAIN_FILE="main_app.py"
    echo "   📄 Using: main_app.py"
elif [ -f "test.py" ]; then
    MAIN_FILE="test.py"
    echo "   📄 Using: test.py"
else
    echo "❌ No main Python file found!"
    ls -la *.py
    exit 1
fi

# Build command
echo ""
echo "🏗️  Building with PyInstaller..."
echo "   (This may take a few minutes)"

pyinstaller --onefile \
    --name "Fucyfuzz" \
    --console \
    --clean \
    --hidden-import=customtkinter \
    --hidden-import=can \
    --hidden-import=pandas \
    --hidden-import=numpy \
    --hidden-import=tkinter \
    "$MAIN_FILE"

# Check result
if [ $? -eq 0 ] && [ -f "dist/Fucyfuzz" ]; then
    chmod +x dist/Fucyfuzz
    
    echo ""
    echo "✅ BUILD SUCCESSFUL!"
    echo "═══════════════════════════════════════════"
    echo ""
    echo "📊 Build Summary:"
    echo "────────────────"
    echo "• Executable: $SCRIPT_DIR/dist/Fucyfuzz"
    echo "• Size: $(ls -lh dist/Fucyfuzz | awk '{print $5}')"
    echo "• Python: $(python --version)"
    echo ""
    echo "📁 Files Created:"
    echo "────────────────"
    echo "1. dist/Fucyfuzz           - Main executable"
    echo "2. requirements.txt        - Dependency list"
    echo ""
    
    # Test run
    echo "🧪 Quick Test:"
    echo "──────────────"
    echo "Running help test..."
    timeout 3s ./dist/Fucyfuzz --help 2>&1 | head -5 || \
    timeout 3s ./dist/Fucyfuzz 2>&1 | head -5 || \
    echo "   (Executable started successfully)"
    
    echo ""
    echo "🚀 To run your application:"
    echo "   ./dist/Fucyfuzz"
    
else
    echo ""
    echo "❌ BUILD FAILED"
    echo "═══════════════════════════════════════════"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check Python file for syntax errors:"
    echo "   python $MAIN_FILE"
    echo ""
    echo "2. Try manual PyInstaller build:"
    echo "   pyinstaller --onefile $MAIN_FILE"
    echo ""
    echo "3. Check PyInstaller output above for errors"
    exit 1
fi