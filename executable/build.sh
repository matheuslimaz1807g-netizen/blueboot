#!/usr/bin/env bash
# build.sh — Generates the ApenasPromo executable using PyInstaller + optional Cython obfuscation
# Run on the target OS (Windows: use build.bat equivalent or WSL; Linux: run directly)

set -e

echo "=== ApenasPromo Build Script ==="

# ── 0. Setup ──────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure dependencies are installed
pip install -r requirements.txt

# ── 1. (Optional) Compile critical modules with Cython ────────────────────────
# This converts license.py and pipeline.py to native .pyd/.so files,
# making disassembly and string extraction much harder.
#
# How it works:
#   1. Cython compiles .py → .c
#   2. gcc/MSVC compiles .c → .pyd (Windows) or .so (Linux)
#   3. PyInstaller bundles the native binary instead of the .py source
#
# To enable: uncomment the block below and install Cython + a C compiler.
#   Windows: pip install cython  +  Visual Studio Build Tools
#   Linux:   pip install cython  +  gcc (via apt: build-essential)
#
# ---------------------------------------------------------------------------
# pip install cython
#
# cat > setup_cython.py << 'EOF'
# from setuptools import setup
# from Cython.Build import cythonize
# import numpy as np
#
# setup(
#     ext_modules=cythonize(
#         ["license.py", "pipeline.py"],
#         compiler_directives={"language_level": "3"},
#         annotate=False,
#     )
# )
# EOF
#
# python setup_cython.py build_ext --inplace
#
# # Remove Python sources so PyInstaller picks up the compiled .pyd/.so
# rm -f license.py pipeline.py
# ---------------------------------------------------------------------------

# ── 2. Build with PyInstaller ─────────────────────────────────────────────────
pyinstaller \
  --onefile \
  --name "ApenasPromo" \
  --add-data "web/templates:web/templates" \
  --add-data "web/static:web/static" \
  --hidden-import "telethon" \
  --hidden-import "telethon.sessions" \
  --hidden-import "telethon.sessions.string" \
  --hidden-import "flask" \
  --hidden-import "requests" \
  --hidden-import "httpx" \
  --hidden-import "cryptography" \
  --hidden-import "cryptography.fernet" \
  --hidden-import "affiliates.shopee" \
  --hidden-import "affiliates.aliexpress" \
  --hidden-import "affiliates.mercadolivre" \
  --collect-all "telethon" \
  --collect-all "flask" \
  --noconfirm \
  --clean \
  main.py

echo ""
echo "=== Build complete! ==="
echo "Executable: dist/ApenasPromo (Linux) or dist/ApenasPromo.exe (Windows)"

# ── 3. On Linux: make executable ──────────────────────────────────────────────
if [ -f "dist/ApenasPromo" ]; then
  chmod +x dist/ApenasPromo
  echo "Permissions set."
fi

# ── Optional: generate SHA-256 for update system ──────────────────────────────
if [ -f "dist/ApenasPromo" ]; then
  sha256sum dist/ApenasPromo > dist/ApenasPromo.sha256
  echo "SHA-256: $(cat dist/ApenasPromo.sha256)"
fi
if [ -f "dist/ApenasPromo.exe" ]; then
  # Windows sha256 (if running in WSL or Git Bash)
  sha256sum dist/ApenasPromo.exe > dist/ApenasPromo.exe.sha256 2>/dev/null || true
fi
