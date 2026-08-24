#!/usr/bin/env bash
# Ashinedu - download models and toolchains (run once, needs internet).
#
# Downloads:
#   models/medgemma-1.5-4b-it-Q8_0.gguf        (primary model, ~4.4 GB)
#   models/qwen2.5-1.5b-instruct-q8_0.gguf      (fallback model, ~1.8 GB)
#   tools/llamacpp.zip                          (llama.cpp Windows CPU build)
#
# After this, everything runs fully offline.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS="$HERE/model"
TOOLS="$HERE/tools"
mkdir -p "$MODELS" "$TOOLS"

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

dl "$MEDGEMMA_URL" "$MODELS/medgemma-1.5-4b-it-Q8_0.gguf" 10c7b9a0d8027c0c151e2050156376f5ed9d4b437494eae81d9cdb81e9b50219
dl "$QWEN_URL" "$MODELS/qwen2.5-1.5b-instruct-q8_0.gguf" d7efb072e7724d25048a4fda0a3e10b04bdef5d06b1403a1c93bd9f1240a63c8

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

echo
echo "All downloads complete. Now run:  bash start.sh"
