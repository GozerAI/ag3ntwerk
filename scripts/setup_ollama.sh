#!/bin/bash
# ag3ntwerk Ollama Setup Script for Linux/macOS
# ============================================

echo "=== ag3ntwerk Ollama Setup ==="
echo ""

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Installing..."
    curl -fsSL https://ollama.ai/install.sh | sh

    if [ $? -ne 0 ]; then
        echo "Failed to install Ollama. Please install manually from https://ollama.ai"
        exit 1
    fi
fi

echo "[OK] Ollama is installed"

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo ""
    echo "Starting Ollama server..."
    ollama serve &
    sleep 3
    echo "[OK] Ollama server started"
else
    echo "[OK] Ollama server is already running"
fi

echo ""
echo "=== Pulling Recommended Models ==="
echo ""

# Pull primary reasoning model
echo "Pulling llama3.2:3b (primary reasoning - 2GB)..."
ollama pull llama3.2:3b
echo "[OK] llama3.2:3b ready"
echo ""

# Pull fast model
echo "Pulling phi3:mini (fast inference - 2GB)..."
ollama pull phi3:mini
echo "[OK] phi3:mini ready"
echo ""

# Optional models prompt
echo "=== Optional Models ==="
echo "The following models are optional but recommended:"
echo "  - deepseek-coder:6.7b (code generation - 4GB)"
echo "  - nomic-embed-text (embeddings - 500MB)"
echo ""
read -p "Would you like to pull optional models? (y/N) " pull_optional

if [[ "$pull_optional" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Pulling deepseek-coder:6.7b..."
    ollama pull deepseek-coder:6.7b
    echo ""
    echo "Pulling nomic-embed-text..."
    ollama pull nomic-embed-text
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Available models:"
ollama list

echo ""
echo "You can now use ag3ntwerk with Ollama!"
echo ""
echo "Quick test:"
echo "  ag3ntwerk status"
echo "  ag3ntwerk models"
echo ""
