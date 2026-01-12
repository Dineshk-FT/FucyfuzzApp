#!/bin/bash
# build_both_desktop.sh - Build both executables as desktop applications

echo "╔══════════════════════════════════════════════════════╗"
echo "║   Build Desktop Apps: Fucyfuzz & Simulator           ║"
echo "╚══════════════════════════════════════════════════════╝"

# Get current directory
EXTERNAL_DIR="$(pwd)"
echo "📍 Current directory: $EXTERNAL_DIR"

# ============================================================================
# CONFIGURATION - UPDATED TO MATCH YOUR STRUCTURE
# ============================================================================
# Based on your directory listing:
# FucyFuzz/        <- Current directory (EXTERNAL_DIR)
#   ├── fucyfuzz/  <- Contains build_fucyfuzz.sh and main_app.py
#   └── Simulator/ <- Contains build_simulator.sh and dashboard.py

FUCFUZZ_DIR="./fucyfuzz"
SIMULATOR_DIR="./Simulator"

# App names (for desktop entries)
APP_NAMES=("Fucyfuzz" "Simulator")
APP_COMMENTS=("CAN Bus Fuzzing Tool" "Vehicle Simulator")
APP_CATEGORIES=("Utility;Network;" "Utility;Education;")

# ============================================================================
# FUNCTION: Create desktop entry
# ============================================================================
create_desktop_entry() {
    local APP_NAME="$1"
    local EXEC_PATH="$2"
    local COMMENT="$3"
    local CATEGORIES="$4"
    local PROJECT_DIR="$5"
    
    echo "🖥️  Creating desktop entry for $APP_NAME..."
    
    # Find icon
    local ICON_PATH=""
    local ICON_FILES=("icon.png" "icon.ico" "icon.svg" "app_icon.png" "logo.png" "fucyfuzzicon.png" "simulator.png")
    
    for icon in "${ICON_FILES[@]}"; do
        if [ -f "$PROJECT_DIR/$icon" ]; then
            ICON_PATH="$PROJECT_DIR/$icon"
            echo "   Using icon: $icon"
            break
        fi
    done
    
    if [ -z "$ICON_PATH" ]; then
        echo "   ⚠️  No icon found, using default"
        ICON_PATH="utilities-terminal"  # Default system icon
    fi
    
    # Create .desktop file for Linux
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        DESKTOP_DIR="$HOME/.local/share/applications"
        mkdir -p "$DESKTOP_DIR"
        
        DESKTOP_FILE="$DESKTOP_DIR/${APP_NAME,,}.desktop"
        
        cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=$COMMENT
Exec="$EXEC_PATH"
Icon=$ICON_PATH
Terminal=false
Categories=$CATEGORIES
StartupNotify=true
EOF
        
        chmod +x "$DESKTOP_FILE"
        echo "   ✅ Desktop entry: $DESKTOP_FILE"
        
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - create .app bundle
        echo "   🍎 macOS: Manual .app bundle creation needed"
        echo "   Use: platypus or create .app folder manually"
        
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        # Windows - create shortcut
        echo "   🪟 Windows: Create shortcut manually from $EXEC_PATH"
    fi
}

# ============================================================================
# FUNCTION: Build with desktop options
# ============================================================================
build_for_desktop() {
    local PROJECT_DIR="$1"
    local APP_NAME="$2"
    local BUILD_SCRIPT="$3"
    
    echo ""
    echo "🔨 Building $APP_NAME as desktop app..."
    echo "────────────────────────────────────────"
    
    if [ ! -d "$PROJECT_DIR" ]; then
        echo "❌ Directory not found: $PROJECT_DIR"
        echo "   Looking in: $(pwd)/$PROJECT_DIR"
        return 1
    fi
    
    echo "📁 Entering directory: $PROJECT_DIR"
    cd "$PROJECT_DIR"
    
    # Check if build script exists
    if [ ! -f "$BUILD_SCRIPT" ]; then
        echo "❌ Build script not found: $BUILD_SCRIPT"
        echo "   Available files:"
        ls -la
        cd "$EXTERNAL_DIR"
        return 1
    fi
    
    echo "🛠️  Running: $BUILD_SCRIPT"
    echo "══════════════════════════════════════════════════════"
    
    # Run the build script
    bash "$BUILD_SCRIPT"
    
    BUILD_STATUS=$?
    
    echo "══════════════════════════════════════════════════════"
    
    if [ $BUILD_STATUS -eq 0 ]; then
        # Check for executable
        local EXECUTABLE=""
        if [ -f "dist/$APP_NAME" ]; then
            EXECUTABLE="$(pwd)/dist/$APP_NAME"
            echo "✅ Found executable: $EXECUTABLE"
        elif [ -f "dist/${APP_NAME}.exe" ]; then
            EXECUTABLE="$(pwd)/dist/${APP_NAME}.exe"
            echo "✅ Found executable: $EXECUTABLE"
        else
            echo "⚠️  No executable found in dist/ folder"
            echo "   Checking dist folder contents:"
            ls -la dist/ 2>/dev/null || echo "   dist/ folder doesn't exist"
        fi
        
        if [ -n "$EXECUTABLE" ]; then
            # Make executable on Unix-like systems
            if [[ "$EXECUTABLE" != *.exe ]]; then
                chmod +x "$EXECUTABLE"
            fi
            cd "$EXTERNAL_DIR"
            return 0
        fi
    fi
    
    echo "❌ Build failed or executable not created"
    cd "$EXTERNAL_DIR"
    return 1
}

# ============================================================================
# VERIFY DIRECTORY STRUCTURE
# ============================================================================
echo ""
echo "🔍 Verifying project structure..."
echo "────────────────────────────────"

echo "📁 Current directory: $EXTERNAL_DIR"
echo "   Expected structure:"
echo "   ├── fucyfuzz/ (contains: build_fucyfuzz.sh, main_app.py)"
echo "   └── Simulator/ (contains: build_simulator.sh, dashboard.py)"
echo ""

echo "Checking Fucyfuzz directory..."
if [ -d "$FUCFUZZ_DIR" ]; then
    echo "✅ Fucyfuzz directory exists: $FUCFUZZ_DIR"
    echo "   Contents:"
    ls "$FUCFUZZ_DIR" | head -10
else
    echo "❌ Fucyfuzz directory not found!"
    echo "   Looking for: $FUCFUZZ_DIR"
fi

echo ""
echo "Checking Simulator directory..."
if [ -d "$SIMULATOR_DIR" ]; then
    echo "✅ Simulator directory exists: $SIMULATOR_DIR"
    echo "   Contents:"
    ls "$SIMULATOR_DIR" | head -10
else
    echo "❌ Simulator directory not found!"
    echo "   Looking for: $SIMULATOR_DIR"
fi

echo ""
echo "══════════════════════════════════════════════════════"

# ============================================================================
# BUILD BOTH APPLICATIONS
# ============================================================================

SUCCESS_APPS=()
FAILED_APPS=()

# Build Fucyfuzz
if build_for_desktop "$FUCFUZZ_DIR" "Fucyfuzz" "build_fucyfuzz.sh"; then
    SUCCESS_APPS+=("Fucyfuzz")
else
    FAILED_APPS+=("Fucyfuzz")
fi

echo ""
echo "══════════════════════════════════════════════════════"

# Build Simulator  
if build_for_desktop "$SIMULATOR_DIR" "Simulator" "build_simulator.sh"; then
    SUCCESS_APPS+=("Simulator")
else
    FAILED_APPS+=("Simulator")
fi

# ============================================================================
# CREATE DESKTOP ENTRIES (Only for successful builds)
# ============================================================================
echo ""
echo "🖥️  Creating Desktop Integration..."
echo "────────────────────────────────────"

for i in "${!SUCCESS_APPS[@]}"; do
    APP_NAME="${SUCCESS_APPS[$i]}"
    
    # Determine which project directory
    if [ "$APP_NAME" = "Fucyfuzz" ]; then
        PROJECT_DIR="$FUCFUZZ_DIR"
        EXEC_PATH="$PROJECT_DIR/dist/$APP_NAME"
        COMMENT="${APP_COMMENTS[0]}"
        CATEGORIES="${APP_CATEGORIES[0]}"
    else
        PROJECT_DIR="$SIMULATOR_DIR"
        EXEC_PATH="$PROJECT_DIR/dist/$APP_NAME"
        COMMENT="${APP_COMMENTS[1]}"
        CATEGORIES="${APP_CATEGORIES[1]}"
    fi
    
    # Check if executable exists
    if [ -f "$EXEC_PATH" ] || [ -f "${EXEC_PATH}.exe" ]; then
        [ -f "${EXEC_PATH}.exe" ] && EXEC_PATH="${EXEC_PATH}.exe"
        create_desktop_entry "$APP_NAME" "$EXEC_PATH" "$COMMENT" "$CATEGORIES" "$PROJECT_DIR"
    else
        echo "⚠️  Cannot create desktop entry for $APP_NAME: Executable not found"
    fi
done

# ============================================================================
# FINAL SUMMARY
# ============================================================================
echo ""
echo "══════════════════════════════════════════════════════"
echo "📊 DESKTOP APPLICATIONS SUMMARY"
echo "══════════════════════════════════════════════════════"

if [ ${#SUCCESS_APPS[@]} -gt 0 ]; then
    echo "✅ Successfully built:"
    for app in "${SUCCESS_APPS[@]}"; do
        if [ "$app" = "Fucyfuzz" ]; then
            EXEC_PATH="$FUCFUZZ_DIR/dist/$app"
        else
            EXEC_PATH="$SIMULATOR_DIR/dist/$app"
        fi
        
        [ -f "${EXEC_PATH}.exe" ] && EXEC_PATH="${EXEC_PATH}.exe"
        
        if [ -f "$EXEC_PATH" ]; then
            SIZE_INFO=$(ls -lh "$EXEC_PATH" 2>/dev/null | awk '{print $5}')
            echo "   📦 $app"
            echo "      Path: $EXEC_PATH"
            echo "      Size: ${SIZE_INFO:-N/A}"
        fi
    done
    echo ""
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "🖥️  Desktop entries created in:"
        echo "   $HOME/.local/share/applications/"
        echo ""
        echo "🔍 Search for them in your application menu!"
    fi
fi

if [ ${#FAILED_APPS[@]} -gt 0 ]; then
    echo "❌ Failed to build:"
    for app in "${FAILED_APPS[@]}"; do
        echo "   • $app"
    done
    echo ""
    echo "⚠️  Troubleshooting:"
    echo "   1. Check that the build scripts exist in their respective directories"
    echo "   2. Make sure build scripts are executable: chmod +x build_*.sh"
    echo "   3. Check for Python dependencies"
fi

# Platform-specific instructions
echo "📋 Platform Instructions:"
echo "─────────────────────────"

case "$OSTYPE" in
    linux-gnu*)
        echo "🐧 Linux:"
        echo "   • Applications appear in your app menu"
        echo "   • To update desktop database:"
        echo "     update-desktop-database ~/.local/share/applications/"
        echo "   • Manual run: ./fucyfuzz/dist/Fucyfuzz or ./Simulator/dist/Simulator"
        ;;
    darwin*)
        echo "🍎 macOS:"
        echo "   • Create .app bundles manually or use:"
        echo "     brew install create-dmg"
        echo "   • Or use Platypus to create app bundles"
        ;;
    msys*|cygwin*)
        echo "🪟 Windows:"
        echo "   • Create shortcuts from the .exe files"
        echo "   • Right-click .exe → 'Create shortcut'"
        echo "   • Drag shortcut to Desktop or Start Menu"
        ;;
    *)
        echo "🌐 Other OS:"
        echo "   • Run executables from dist/ folders"
        ;;
esac

echo ""
echo "✨ Desktop app build complete! 🎉"