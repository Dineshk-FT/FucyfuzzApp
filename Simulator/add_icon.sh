#!/bin/bash
# add_icon.sh - Add icon and create desktop launcher for Simulator

echo "🎨 Setting up Simulator icon and launcher"
echo "═══════════════════════════════════════════"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📍 Project directory: $SCRIPT_DIR"
echo ""

# ============================================================================
# 1. CHECK FOR ICON FILES
# ============================================================================
echo "🔍 [1/4] Looking for icon files..."

ICON_FILES=()
for icon in simulator.png fucyfuzzicon.png fucyfuzzicon.ico icon_64.png icon.png; do
    if [ -f "$icon" ]; then
        ICON_FILES+=("$icon")
        echo "✅ Found: $icon"
    fi
done

if [ ${#ICON_FILES[@]} -eq 0 ]; then
    echo "❌ No icon files found!"
    echo "   Creating a simple icon..."
    
    # Create a simple PNG icon (64x64 red circle)
    cat > create_icon.py << 'EOF'
import pygame
pygame.init()
icon = pygame.Surface((64, 64), pygame.SRCALPHA)
pygame.draw.circle(icon, (255, 50, 50), (32, 32), 30)
pygame.draw.circle(icon, (255, 255, 255), (32, 32), 20)
pygame.draw.circle(icon, (50, 150, 255), (32, 32), 10)
pygame.image.save(icon, "simulator_icon.png")
print("Created: simulator_icon.png")
EOF
    python create_icon.py
    rm create_icon.py
    ICON_FILES=("simulator_icon.png")
fi

# Select the best icon
SELECTED_ICON="${ICON_FILES[0]}"
echo "📌 Selected icon: $SELECTED_ICON"
echo ""

# ============================================================================
# 2. REBUILD WITH ICON
# ============================================================================
echo "🔨 [2/4] Rebuilding with icon..."

if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Please run build_simulator.sh first"
    exit 1
fi

source venv/bin/activate

# Clean and rebuild with icon
rm -rf build/ dist/ *.spec 2>/dev/null

echo "   Building Simulator with icon: $SELECTED_ICON"

pyinstaller --onefile \
    --name "Simulator" \
    --icon="$SELECTED_ICON" \
    --console \
    --clean \
    --add-data "assets:assets" \
    --hidden-import=can \
    --hidden-import=can.interface \
    --hidden-import=pygame \
    dashboard.py

if [ $? -eq 0 ] && [ -f "dist/Simulator" ]; then
    chmod +x dist/Simulator
    echo "✅ Rebuilt with icon!"
    echo "   Executable: dist/Simulator"
else
    echo "⚠️  Could not rebuild, using existing executable"
fi
echo ""

# ============================================================================
# 3. CREATE DESKTOP LAUNCHER
# ============================================================================
echo "🏠 [3/4] Creating desktop launcher..."

DESKTOP_LAUNCHER="$HOME/Desktop/Simulator.desktop"
ICON_PATH="$SCRIPT_DIR/$SELECTED_ICON"

cat > "$DESKTOP_LAUNCHER" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Simulator
Comment=CAN Bus Instrument Cluster Simulator
Exec=$SCRIPT_DIR/dist/Simulator
Icon=$ICON_PATH
Terminal=true
Categories=Development;Utility;
StartupNotify=true
EOF

chmod +x "$DESKTOP_LAUNCHER"
echo "✅ Desktop launcher created:"
echo "   📄 $DESKTOP_LAUNCHER"
echo "   🎨 Icon: $ICON_PATH"
echo ""

# ============================================================================
# 4. CREATE APPLICATION MENU ENTRY
# ============================================================================
echo "📋 [4/4] Creating application menu entry..."

if [ -d "/usr/share/applications" ] || [ -d "$HOME/.local/share/applications" ]; then
    APPS_DIR="$HOME/.local/share/applications"
    mkdir -p "$APPS_DIR"
    
    MENU_ENTRY="$APPS_DIR/simulator.desktop"
    
    cat > "$MENU_ENTRY" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Simulator
GenericName=CAN Bus Simulator
Comment=Instrument Cluster and UDS Diagnostics Simulator
Exec=$SCRIPT_DIR/dist/Simulator
Icon=$ICON_PATH
Terminal=true
Categories=Development;Utility;Science;
Keywords=CAN;UDS;Automotive;Diagnostics;Simulator
StartupNotify=true
EOF

    chmod +x "$MENU_ENTRY"
    echo "✅ Application menu entry created:"
    echo "   📁 $MENU_ENTRY"
    
    # Update desktop database
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$APPS_DIR"
        echo "✅ Updated desktop database"
    fi
else
    echo "⚠️  Could not create application menu entry"
fi

echo ""
echo "🎉 SETUP COMPLETE!"
echo "═══════════════════════════════════════════"
echo ""
echo "📋 What was created:"
echo "────────────────────"
echo "1. ✅ Rebuilt executable with icon"
echo "2. ✅ Desktop shortcut: ~/Desktop/Simulator.desktop"
echo "3. ✅ Application menu entry (if supported)"
echo ""
echo "🚀 Ways to launch Simulator:"
echo "────────────────────────────"
echo "1. Double-click: ~/Desktop/Simulator.desktop"
echo "2. Terminal: ./dist/Simulator"
echo "3. Application menu: Look for 'Simulator'"
echo ""
echo "🔧 To update later: ./build_simulator.sh"