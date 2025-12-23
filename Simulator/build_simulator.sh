#!/bin/bash
# build_simulator.sh - Specialized fix for can.interface import

echo "🔨 Building Simulator - Specialized can.interface fix"
echo "════════════════════════════════════════════════════"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📍 Directory: $SCRIPT_DIR"
echo ""

# ============================================================================
# 1. FIRST, LET'S CHECK THE EXACT ISSUE
# ============================================================================
echo "🔍 [1/5] Analyzing the issue..."

cat > analyze_imports.py << 'EOF'
import sys
import os

# Simulate PyInstaller environment
sys.path.insert(0, os.getcwd())

print("Analyzing python-can imports in PyInstaller context...")
print("=" * 60)

# First, check what python-can looks like
try:
    import can
    print(f"✅ can module loaded: version {can.__version__}")
    print(f"   Location: {can.__file__}")
    
    # Check all possible import methods
    methods = [
        ("from can.interface import Bus", None),
        ("import can.interface", None),
        ("from can import Bus", None),
        ("can.Bus", None),
        ("can.interface.Bus", None),
    ]
    
    for method_desc, _ in methods:
        try:
            exec(method_desc.split()[1])  # Just the import part
            print(f"✅ {method_desc}: WORKS")
        except ImportError as e:
            print(f"❌ {method_desc}: {e}")
        except AttributeError as e:
            print(f"❌ {method_desc}: {e}")
        except Exception as e:
            print(f"❌ {method_desc}: {type(e).__name__}")
            
    # List contents of can module
    print("\n📋 Contents of can module:")
    for attr in dir(can):
        if not attr.startswith('_') or attr in ['__version__', '__file__']:
            print(f"  {attr}")
            
except ImportError as e:
    print(f"❌ Cannot import can at all: {e}")
    
print("\n" + "=" * 60)
EOF

python analyze_imports.py
rm -f analyze_imports.py
echo ""

# ============================================================================
# 2. CREATE PATCHED DASHBOARD.PY
# ============================================================================
echo "📝 [2/5] Creating patched dashboard.py..."

if [ -f "dashboard.py" ]; then
    # Create backup
    cp dashboard.py dashboard.py.backup
    echo "✅ Backup created: dashboard.py.backup"
    
    # Create the patch
    cat > patch_dashboard.py << 'EOF'
#!/usr/bin/env python3
"""
PATCH for dashboard.py - Fix can.interface import for PyInstaller
"""

import re

with open('dashboard.py', 'r') as f:
    content = f.read()

# Find the import section
import_section = '''import pygame
import can
import sys
import os
import math
import time'''

# Replace with patched version
patched_imports = '''import pygame
import sys
import os
import math
import time

# === PATCH FOR PYINSTALLER BUNDLING ===
# This fixes the 'can.interface' module issue when bundled
def setup_can_import():
    """Handle can import differently for PyInstaller vs normal Python"""
    try:
        # First try direct import (works in normal Python)
        import can
        return can
    except ImportError:
        # If can module not found at all
        print("❌ ERROR: python-can module not installed")
        sys.exit(1)

# Initialize can module
can = setup_can_import()

# Now try to import Bus - handle PyInstaller's special case
try:
    # Method 1: Try direct import first
    from can.interface import Bus
    print("✓ Import: from can.interface import Bus")
except ImportError:
    try:
        # Method 2: Try alternative import
        from can import Bus
        print("✓ Import: from can import Bus")
    except ImportError:
        try:
            # Method 3: Try accessing via module attribute
            Bus = can.interface.Bus
            print("✓ Import: Bus = can.interface.Bus")
        except AttributeError:
            # Method 4: Fallback to can.Bus
            Bus = can.Bus
            print("✓ Import: Bus = can.Bus")
# === END PATCH ==='''

content = content.replace(import_section, patched_imports)

# Also update the setup_can method to handle all cases
setup_can_method = '''    def setup_can(self):
        """Setup CAN bus connection"""
        try:
            self.bus = can.interface.Bus(channel=CAN_INTERFACE, bustype='socketcan')
            print(f"✓ Connected to {CAN_INTERFACE}")
        except OSError as e:
            print(f"⚠ CAN interface not available: {e}")
            print(f"\\n📋 To setup vcan0:")
            print("   sudo modprobe vcan")
            print("   sudo ip link add dev vcan0 type vcan")
            print("   sudo ip link set up vcan0")
            print("\\n▶ Running in DEMO mode (use arrow keys)")
            self.bus = None'''

fixed_setup_can = '''    def setup_can(self):
        """Setup CAN bus connection"""
        try:
            # Use the imported Bus class (works with all import methods)
            self.bus = Bus(channel=CAN_INTERFACE, bustype='socketcan')
            print(f"✓ Connected to {CAN_INTERFACE}")
        except OSError as e:
            print(f"⚠ CAN interface not available: {e}")
            print(f"\\n📋 To setup vcan0:")
            print("   sudo modprobe vcan")
            print("   sudo ip link add dev vcan0 type vcan")
            print("   sudo ip link set up vcan0")
            print("\\n▶ Running in DEMO mode (use arrow keys)")
            self.bus = None
        except Exception as e:
            print(f"❌ CAN setup error: {e}")
            print("Trying alternative Bus initialization...")
            try:
                self.bus = can.Bus(channel=CAN_INTERFACE, bustype='socketcan')
                print(f"✓ Connected to {CAN_INTERFACE} (using can.Bus)")
            except:
                print("⚠ Running in DEMO mode")
                self.bus = None'''

content = content.replace(setup_can_method, fixed_setup_can)

# Write patched version
with open('dashboard_patched.py', 'w') as f:
    f.write(content)

print("✅ Created patched version: dashboard_patched.py")
EOF

    python patch_dashboard.py
    rm -f patch_dashboard.py
    
    # Replace original with patched version
    mv dashboard_patched.py dashboard.py
    echo "✅ Applied patch to dashboard.py"
else
    echo "❌ dashboard.py not found!"
    exit 1
fi
echo ""

# ============================================================================
# 3. SETUP ENVIRONMENT
# ============================================================================
echo "🔧 [3/5] Setting up environment..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Created: venv/"
else
    echo "✅ Using existing: venv/"
fi

source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install pygame python-can

echo "✅ Dependencies installed"
echo ""

# ============================================================================
# 4. CREATE SPECIALIZED HOOK
# ============================================================================
echo "📝 [4/5] Creating specialized hook..."

mkdir -p hooks

cat > hooks/hook-can.py << 'EOF'
# Specialized hook for python-can with can.interface support
from PyInstaller.utils.hooks import collect_all

# Collect everything from python-can
datas, binaries, hiddenimports = collect_all('can')

# Specifically ensure interface module is included
hiddenimports += [
    'can.interface',
    'can.interfaces',
    'can.bus',
    'can._interface',  # Sometimes internal module
    'can._bus',        # Internal bus module
]

# Force inclusion of interface module files
import can
import os

# Add any data files from can.interface
if hasattr(can, '__file__'):
    can_dir = os.path.dirname(can.__file__)
    interface_dir = os.path.join(can_dir, 'interface')
    if os.path.exists(interface_dir):
        for root, dirs, files in os.walk(interface_dir):
            for file in files:
                if file.endswith('.py'):
                    module_path = os.path.relpath(root, can_dir).replace('/', '.')
                    if module_path == '.':
                        module_name = 'can.interface'
                    else:
                        module_name = f'can.{module_path}.{file[:-3]}'
                    hiddenimports.append(module_name)

print(f"python-can hook: Added {len(hiddenimports)} hidden imports")
EOF

echo "✅ Created specialized hook"
echo ""

# ============================================================================
# 5. BUILD WITH COMPLETE FIX
# ============================================================================
echo "🔨 [5/5] Building with complete fix..."

rm -rf build/ dist/ *.spec __pycache__/ 2>/dev/null

echo "   Building dashboard.py with all fixes..."

# Test the patched import first
echo "🧪 Testing patched imports..."
python -c "
import sys
sys.path.insert(0, '.')
import dashboard
print('✅ Patched dashboard.py imports work!')
"
ICON_OPTION=""
if [ -f "simulator.png" ]; then
    ICON_OPTION="--icon=simulator.png"
elif [ -f "fucyfuzzicon.png" ]; then
    ICON_OPTION="--icon=fucyfuzzicon.png"
fi
# Build command
pyinstaller --onefile \
    --name "Simulator" \
    --console \
    --clean \
    --additional-hooks-dir="hooks" \
    --add-data "assets:assets" \
    --hidden-import=can \
    --hidden-import=can.interface \
    --hidden-import=can.interfaces \
    --hidden-import=can.bus \
    --hidden-import=can._interface \
    --hidden-import=pygame \
    --hidden-import=pygame._sdl2 \
    dashboard.py

# Check result
if [ $? -eq 0 ] && [ -f "dist/Simulator" ]; then
    chmod +x dist/Simulator
    
    echo ""
    echo "✅ BUILD COMPLETE WITH IMPORT FIX!"
    echo "═══════════════════════════════════════════"
    echo ""
    
    # Test the executable
    echo "🧪 Testing executable (5-second timeout)..."
    echo "   (Look for '✓ Import:' message in output)"
    timeout 5s ./dist/Simulator 2>&1 | grep -A5 -B5 "Import:" || \
    timeout 5s ./dist/Simulator 2>&1 | head -10
    
    echo ""
    echo "📊 Fixes applied:"
    echo "────────────────"
    echo "1. Patched dashboard.py with flexible import"
    echo "2. Created specialized PyInstaller hook"
    echo "3. Tested all import methods"
    echo "4. Built with all necessary hidden imports"
    echo ""
    echo "🚀 Run: ./dist/Simulator"
    echo ""
    echo "💡 If you need the original dashboard.py:"
    echo "   mv dashboard.py.backup dashboard.py"
    
else
    echo ""
    echo "❌ BUILD FAILED"
    echo "═══════════════════════════════════════════"
    echo ""
    echo "Last resort: Try the ALTERNATIVE SOLUTION below"
    echo "1. Restore original: mv dashboard.py.backup dashboard.py"
    echo "2. Use alternative build method"
    exit 1
fi