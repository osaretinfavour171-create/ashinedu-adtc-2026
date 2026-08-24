#!/bin/bash
# EARL AI — Global launcher
# Run from anywhere: just type 'earlai' in any terminal
cd "$(dirname "$(readlink -f "$0")")"
python3 app/orchestrator.py "$@"
