#!/bin/bash
# make_deb.sh - Professional Debian packaging for Fucyfuzz Suite

APP_NAME="fucyfuzz-suite"
VERSION="1.0"
MAINTAINER="YourName <you@example.com>"
BUILD_DIR="fucyfuzz_pkg_temp"

echo "📦 Starting Debian Package Build..."

# 1. Clean previous attempts
rm -rf $BUILD_DIR
rm -f "${APP_NAME}_${VERSION}.deb"

# 2. Create the standard Linux directory structure
# /usr/bin/ for the executables
# /usr/share/fucyfuzz/ for assets (icons, etc)
# /usr/share/applications/ for the desktop menu entries
mkdir -p $BUILD_DIR/DEBIAN
mkdir -p $BUILD_DIR/usr/bin
mkdir -p $BUILD_DIR/usr/share/fucyfuzz
mkdir -p $BUILD_DIR/usr/share/applications
mkdir -p $BUILD_DIR/usr/share/icons/hicolor/64x64/apps

# 3. Copy the binaries (Checking if they exist first)
if [[ -f "fucyfuzz/dist/Fucyfuzz" && -f "Simulator/dist/Simulator" ]]; then
    cp fucyfuzz/dist/Fucyfuzz $BUILD_DIR/usr/bin/fucyfuzz
    cp Simulator/dist/Simulator $BUILD_DIR/usr/bin/fucy-simulator
    chmod +x $BUILD_DIR/usr/bin/fucy*
else
    echo "❌ Error: Binaries not found in dist folders! Run your build scripts first."
    exit 1
fi

# 4. Copy Icons and Assets
[ -f "fucyfuzz/icon_64.png" ] && cp fucyfuzz/icon_64.png $BUILD_DIR/usr/share/icons/hicolor/64x64/apps/fucyfuzz.png
[ -f "Simulator/simulator.png" ] && cp Simulator/simulator.png $BUILD_DIR/usr/share/icons/hicolor/64x64/apps/simulator.png

# 5. Create Desktop Menu Entries (so they appear in Kali's Application menu)
cat > $BUILD_DIR/usr/share/applications/fucyfuzz.desktop << EOF
[Desktop Entry]
Name=Fucyfuzz
Comment=CAN Bus Fuzzing Tool
Exec=/usr/bin/fucyfuzz
Icon=fucyfuzz
Terminal=false
Type=Application
Categories=Network;Security;
EOF

cat > $BUILD_DIR/usr/share/applications/fucy-simulator.desktop << EOF
[Desktop Entry]
Name=Fucy Simulator
Comment=Vehicle CAN Simulator
Exec=/usr/bin/fucy-simulator
Icon=simulator
Terminal=false
Type=Application
Categories=Education;Development;
EOF

# 6. Create the Control File (Package Metadata)
cat > $BUILD_DIR/DEBIAN/control << EOF
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Maintainer: $MAINTAINER
Depends: can-utils, python3
Description: Fucyfuzz Security Suite
 A complete toolset for CAN bus fuzzing and vehicle simulation.
 Packaged for Kali Linux.
EOF

# 7. Set correct permissions for Debian system
find $BUILD_DIR/usr -type d -exec chmod 755 {} +
find $BUILD_DIR/usr -type f -exec chmod 644 {} +
chmod 755 $BUILD_DIR/usr/bin/fucy*

# 8. Build the .deb
dpkg-deb --build $BUILD_DIR "${APP_NAME}_${VERSION}.deb"

# 9. Cleanup
rm -rf $BUILD_DIR

echo "------------------------------------------------"
echo "✅ SUCCESS: ${APP_NAME}_${VERSION}.deb created."
echo "🚀 To install: sudo dpkg -i ${APP_NAME}_${VERSION}.deb"
echo "------------------------------------------------"