#!/usr/bin/env bash
# PidginPharma - start everything and open the REPL.
#
# This script:
#   1. Starts DocReader (Go) on 127.0.0.1:8765
#   2. Starts llama-server with the primary model (MedGemma) on 127.0.0.1:8080;
#      falls back to Qwen 2.5-1.5B if MedGemma is missing.
#   3. Waits until ALL services are confirmed ready
#   4. Opens the PidginPharma REPL
#
# Fully offline once download_model.sh has been run.
#
# Optional layers:
#   --pinchtab   also starts the local HTML doc server and enables the
#                PinchTab browser layer (uses ~300-800 MB extra RAM)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS="$HERE/tools"
MODELS="$HERE/model"
DATA="$HERE/app/data"
LLAMA_BIN="$TOOLS/llamacpp/llama-server.exe"
DOCREADER_BIN="$TOOLS/docreader.exe"
DR_PORT=8765
LLM_PORT=8080
HTML_PORT=8766
HTML_DIR="$HERE/app/data/html"

mkdir -p "$TOOLS" "$MODELS"

# ---------------------------------------------------------------------------
# Helper: wait for a HTTP health endpoint (silent, no output to user)
#   wait_for_service URL MAX_SECONDS
#   Returns 0 if ready, 1 if timed out.
# ---------------------------------------------------------------------------
wait_for_service() {
    local url="$1"
    local max_wait="$2"
    for i in $(seq 1 "$max_wait"); do
        if curl -sf "$url" > /dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    return 1
}

# ---------------------------------------------------------------------------
# 1. DocReader
# ---------------------------------------------------------------------------
if [ -f "$DOCREADER_BIN" ]; then
    if ! curl -sf "http://127.0.0.1:$DR_PORT/health" > /dev/null 2>&1; then
        echo "[start] Starting the data server..."
        "$DOCREADER_BIN" -addr "127.0.0.1:$DR_PORT" -data "$DATA" \
            > "$TOOLS/docreader.log" 2>&1 &
        if wait_for_service "http://127.0.0.1:$DR_PORT/health" 15; then
            echo "[start] Data server is ready."
        else
            echo "[start] ERROR: Data server failed to start."
            echo ""
            echo "  The clinical data could not load. This is needed for the system to work."
            echo "  Please ask your ICT support person to check the computer."
            echo "  You can also try restarting the computer and running start.sh again."
            echo ""
            echo "  Exiting. If this is an emergency, please refer the patient to hospital."
            exit 1
        fi
    else
        echo "[start] Data server already running."
    fi
else
    echo ""
    echo "  ERROR: The data server program (docreader.exe) is missing."
    echo ""
    echo "  Please ask your ICT support person to reinstall PidginPharma."
    echo "  If this is an emergency, please refer the patient to hospital."
    echo ""
    exit 1
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
    echo "[start] Model server already running."
elif [ -f "$LLAMA_BIN" ]; then
    MODEL="$(pick_model)"
    if [ -n "$MODEL" ]; then
        echo "[start] Loading the clinical brain (this may take a minute)..."
        "$LLAMA_BIN" \
            -m "$MODELS/$MODEL" \
            --host 127.0.0.1 --port "$LLM_PORT" \
            -c 2048 --threads 4 \
            --no-webui \
            > "$TOOLS/llama.log" 2>&1 &
        if wait_for_service "http://127.0.0.1:$LLM_PORT/health" 120; then
            echo "[start] Clinical brain is ready."
        else
            echo "[start] WARNING: Model server took too long to start."
            echo "         The system will still work for drug interaction lookups,"
            echo "         but will not be able to answer general clinical questions."
            echo "         Try restarting the computer if this persists."
        fi
    else
        echo ""
        echo "  WARNING: No clinical model found on this computer."
        echo "  The system will still work for drug interaction lookups,"
        echo "  but will not be able to answer general clinical questions."
        echo "  Please ask your ICT support person to run: bash download_model.sh"
        echo ""
    fi
else
    echo ""
    echo "  WARNING: The model program (llama-server) is missing."
    echo "  The system will still work for drug interaction lookups,"
    echo "  but will not be able to answer general clinical questions."
    echo "  Please ask your ICT support person to reinstall PidginPharma."
    echo ""
fi

# ---------------------------------------------------------------------------
# 2b. Optional HTML doc server (used by the PinchTab browser layer)
#     Only started when --pinchtab is passed.
# ---------------------------------------------------------------------------
if [[ " $* " == *" --pinchtab "* ]]; then
    if [ -d "$HTML_DIR" ]; then
        if ! curl -sf "http://127.0.0.1:$HTML_PORT/STG_conditions.html" > /dev/null 2>&1; then
            (cd "$HTML_DIR" && python -m http.server "$HTML_PORT" --bind 127.0.0.1 \
                > "$TOOLS/htmlsrv.log" 2>&1 &)
            sleep 2
        fi
    fi
fi

# ---------------------------------------------------------------------------
# 3. Final check and launch
# ---------------------------------------------------------------------------
echo ""
echo "  All systems are ready."
echo ""

cd "$HERE/app"
exec python orchestrator.py "$@"
