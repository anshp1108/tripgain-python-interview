#!/bin/bash
# Quick Start Script for Tripgain Gemini Integration

echo "=================================================="
echo "Tripgain Gemini Integration - Quick Setup"
echo "=================================================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "[✓] Python version: $python_version"
echo ""

# Install dependencies
echo "[*] Installing dependencies..."
pip install -q -r requirements.txt
echo "[✓] Dependencies installed"
echo ""

# Check API key
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "[!] GOOGLE_API_KEY environment variable not set"
    echo "[*] Please set it before running the script:"
    echo "    export GOOGLE_API_KEY='your_api_key_here'"
    echo ""
fi

# Run the main script
echo "[*] Starting Tripgain Gemini Integration..."
echo ""
python3 tripgain_gemini_analysis.py
