#!/usr/bin/env bash
# PidginPharma - start everything and open the REPL.
#
#   1. Starts DocReader (Go) on 127.0.0.1:8765
#   2. Starts llama-server with the primary model (MedGemma) on 127.0.0.1:8080;
#      falls back to Qwen 2.5-1.5B if MedGemma is missing.
#   3. Opens the PidginPharma REPL.
#
# Fully offline once download_model.sh has been run.
#
# Optional layers:
#   --pinchtab   also starts the local HTML doc server and enables the
#                PinchTab browser layer (uses ~300-800 MB extra RAM)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS="$HERE/tools"
MODELS="$HERE/models"
DATA="$HERE/app/data"
LLAMA_BIN="$TOOLS/llamacpp/llama-server.exe"
DOCREADER_BIN="$TOOLS/docreader.exe"
DR_PORT=8765
LLM_PORT=8080
HTML_PORT=8766
HTML_DIR="$HERE/app/data/html"

mkdir -p "$TOOLS" "$MODELS"

# ---------------------------------------------------------------------------
# 1. DocReader
# ---------------------------------------------------------------------------
if [ -f "$DOCREADER_BIN" ]; then
    if ! curl -sf "http://127.0.0.1:$DR_PORT/health" > /dev/null 2>&1; then
        echo "[start] starting DocReader on :$DR_PORT ..."
        "$DOCREADER_BIN" -addr "127.0.0.1:$DR_PORT" -data "$DATA" \
            > "$TOOLS/docreader.log" 2>&1 &
        sleep 2
    else
        echo "[start] DocReader already running on :$DR_PORT"
    fi
else
    echo "[start] WARNING: docreader.exe not found - build it with:"
    echo "        cd app/docreader && go build -o ../../tools/docreader.exe ."
fi

# ---------------------------------------------------------------------------
# 2. Model server (llama-server)
# ---------------------------------------------------------------------------
pick_model() {
    if [ -f "$MODELS/medgemma-1.5-4b-it-Q8_0.gguf" ]; then
        echo "medgemma-1.5-4b-it-Q8_0.gguf"
    elif [ -f "$MODELS/qwen2.5-1.5b-instruct-q8_0.gguf" ]; then
        echo "qwen2.5-1.5b-instruct-q8_0.gguf"
    else
        echo ""
    fi
}

if curl -sf "http://127.0.0.1:$LLM_PORT/health" > /dev/null 2>&1; then
    echo "[start] model server already running on :$LLM_PORT"
elif [ -f "$LLAMA_BIN" ]; then
    MODEL="$(pick_model)"
    if [ -n "$MODEL" ]; then
        echo "[start] starting llama-server with $MODEL on :$LLM_PORT ..."
        "$LLAMA_BIN" \
            -m "$MODELS/$MODEL" \
            --host 127.0.0.1 --port "$LLM_PORT" \
            -c 2048 --threads 4 \
            --no-webui \
            > "$TOOLS/llama.log" 2>&1 &
        sleep 3
        echo "[start] model server starting (see tools/llama.log)"
    else
        echo "[start] WARNING: no model found. Run:  bash download_model.sh"
    fi
else
    echo "[start] WARNING: llama-server.exe not found. Run:  bash download_model.sh"
fi

# ---------------------------------------------------------------------------
# 2b. Optional HTML doc server (used by the PinchTab browser layer)
#     Only started when --pinchtab is passed. Serves the pre-converted
#     EML/STG HTML on 127.0.0.1:8766 so PinchTab can browse it locally.
# ---------------------------------------------------------------------------
if [[ " $* " == *" --pinchtab "* ]]; then
    if [ -d "$HTML_DIR" ]; then
        if ! curl -sf "http://127.0.0.1:$HTML_PORT/STG_conditions.html" > /dev/null 2>&1; then
            echo "[start] serving converted guideline HTML on :$HTML_PORT ..."
            # SECURITY: bind to 127.0.0.1 only. Serving on 0.0.0.0 would
            # expose the clinical guideline HTML to the local network.
            (cd "$HTML_DIR" && python -m http.server "$HTML_PORT" --bind 127.0.0.1 \n                > "$TOOLS/htmlsrv.log" 2>&1 &)
            sleep 2
        else
            echo "[start] HTML doc server already running on :$HTML_PORT"
        fi
    else
        echo "[start] WARNING: $HTML_DIR not found - PinchTab layer will be unavailable"
    fi
fi

# ---------------------------------------------------------------------------
# 3. Orchestrator REPL
# ---------------------------------------------------------------------------
echo
echo "[start] launching PidginPharma ..."
cd "$HERE/app"
exec python orchestrator.py "$@"
