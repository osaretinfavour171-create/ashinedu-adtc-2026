#!/usr/bin/env bash
# Ashinedu - download models and toolchains (run once, needs internet).
#
# Usage:
#   bash download_model.sh           # Full install (MedGemma + Qwen, ~5.8 GB)
#   bash download_model.sh --lite    # Lite install (Qwen only, ~2 GB)
#
# Downloads:
#   Full:  models/medgemma + models/qwen + tools (~5.8 GB)
#   Lite:  models/qwen + tools (~2 GB)
#
# After this, everything runs fully offline.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS="$HERE/model"
TOOLS="$HERE/tools"
mkdir -p "$MODELS" "$TOOLS"

# --- Parse flags ---
LITE_MODE=false
for arg in "$@"; do
    case "$arg" in
        --lite|-l) LITE_MODE=true ;;
    esac
done

MEDGEMMA_URL="https://huggingface.co/unsloth/medgemma-1.5-4b-it-GGUF/resolve/main/medgemma-1.5-4b-it-Q8_0.gguf"
QWEN_URL="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q8_0.gguf"

# --- OS detection ---
if [[ "$(uname -s)" == *Linux* ]] || [[ -f /proc/version ]]; then
    IS_LINUX=true
    LLAMACPP_URL="https://github.com/ggml-org/llama.cpp/releases/download/b10612/llama-b10612-bin-ubuntu-x64.tar.gz"
else
    IS_LINUX=false
    LLAMACPP_URL="https://github.com/ggml-org/llama.cpp/releases/download/b10472/llama-b10472-bin-win-cpu-x64.zip"
fi

dl() {
    local url="$1" out="$2"
    if [ -f "$out" ] && [ -s "$out" ]; then
        echo "already present: $out ($(du -h "$out" | cut -f1))"
        return
    fi
    echo "downloading: $url"
    curl -L --fail --retry 3 -C - -o "$out" "$url"
    echo "done: $out"
    # verify checksum so a truncated/corrupt download is caught immediately
    local want="$3" got="$(sha256sum "$out" | cut -d" " -f1)"
    if [ "$got" != "$want" ]; then
        echo "ERROR: $out checksum mismatch (got $got, want $want) - delete and retry"
        exit 1
    fi
}

# --- Download models ---
if [ "$LITE_MODE" = true ]; then
    echo ""
    echo "  LITE MODE: Downloading Qwen 1.5B only (~2 GB)"
    echo "  For full mode (MedGemma + Qwen), run: bash download_model.sh"
    echo ""
    dl "$QWEN_URL" "$MODELS/qwen2.5-1.5b-instruct-q8_0.gguf" d7efb072e7724d25048a4fda0a3e10b04bdef5d06b1403a1c93bd9f1240a63c8
else
    echo ""
    echo "  FULL MODE: Downloading MedGemma 4B + Qwen 1.5B (~5.8 GB)"
    echo "  For lite mode (Qwen only), run: bash download_model.sh --lite"
    echo ""
    dl "$MEDGEMMA_URL" "$MODELS/medgemma-1.5-4b-it-Q8_0.gguf" 10c7b9a0d8027c0c151e2050156376f5ed9d4b437494eae81d9cdb81e9b50219
    dl "$QWEN_URL" "$MODELS/qwen2.5-1.5b-instruct-q8_0.gguf" d7efb072e7724d25048a4fda0a3e10b04bdef5d06b1403a1c93bd9f1240a63c8
fi

# --- Download binaries ---
if [ "$IS_LINUX" = true ]; then
    # Linux: download llama.cpp and shared libraries
    if [ ! -f "$TOOLS/llama-server" ]; then
        dl "$LLAMACPP_URL" "$TOOLS/llama-linux.tar.gz"
        (cd "$TOOLS" && tar xzf llama-linux.tar.gz && \
         cp llama-b10612/llama-server . && \
         cp llama-b10612/*.so* . 2>/dev/null; \
         chmod +x llama-server 2>/dev/null; \
         rm -rf llama-b10612 llama-linux.tar.gz)
        echo "llama.cpp (Linux) extracted to $TOOLS"
    fi
    # Linux: build docreader from source (needs Go)
    if [ ! -f "$TOOLS/docreader" ]; then
        if command -v go > /dev/null 2>&1; then
            echo "Building docreader for Linux..."
            (cd "$HERE/app/docreader" && GOOS=linux GOARCH=amd64 go build -o "$TOOLS/docreader" .)
            echo "docreader built: $TOOLS/docreader"
        else
            echo "WARNING: Go not found. Install Go to build docreader:"
            echo "  sudo apt install golang-go"
            echo "  Or download from: https://go.dev/dl/"
        fi
    fi
else
    # Windows: download llama.cpp Windows build
    if [ ! -f "$TOOLS/llamacpp/llama-server.exe" ]; then
        dl "$LLAMACPP_URL" "$TOOLS/llamacpp.zip"
        (cd "$TOOLS" && unzip -q -o llamacpp.zip -d llamacpp)
        echo "llama.cpp extracted to $TOOLS/llamacpp"
    fi
fi

echo ""
if [ "$LITE_MODE" = true ]; then
    echo "Lite download complete (~2 GB). Now run:  bash start.sh"
    echo "Note: Lite mode uses Qwen 1.5B only. For better accuracy,"
    echo "      run full mode: bash download_model.sh"
else
    echo "Full download complete (~5.8 GB). Now run:  bash start.sh"
fi
