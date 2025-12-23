#!/bin/bash
# update_simulator.sh - Quick rebuild with hooks

cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null

echo "🔄 Rebuilding Simulator with python-can hooks..."

# Ensure hooks directory exists
mkdir -p hooks

# Create/update hook file
cat > hooks/hook-can.py << 'EOF'
from PyInstaller.utils.hooks import collect_submodules
hiddenimports = collect_submodules('can')
hiddenimports += ['can.interface', 'can.interfaces', 'can.bus']
EOF

rm -rf build/ __pycache__/
pyinstaller --onefile \
    --name "Simulator" \
    --clean \
    --additional-hooks-dir="hooks" \
    --add-data "assets:assets" \
    --hidden-import=can \
    --hidden-import=can.interface \
    dashboard.py

if [ -f "dist/Simulator" ]; then
    chmod +x dist/Simulator
    echo "✅ Updated: dist/Simulator (with hooks)"
else
    echo "❌ Update failed"
fi