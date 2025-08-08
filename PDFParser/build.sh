#!/bin/bash

APP_NAME="PDFCSVTool"
ENTRY_FILE="app.py"
ICON_FILE="icon.ico"  # optional: put an icon file in your project

echo "Cleaning previous builds..."
rm -rf build dist __pycache__ *.spec

echo "Building with PyInstaller..."
pyinstaller \
  --onefile \
  --windowed \
  --name "$APP_NAME" \
  $ENTRY_FILE

echo "Done! Executable is in dist/$APP_NAME"

cp dist/$APP_NAME /home/dustin/public_html
echo "Copied to /home/dustin/public_html"
