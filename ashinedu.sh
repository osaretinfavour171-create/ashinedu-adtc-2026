#!/bin/bash
# Ashinedu — Global launcher
# Run from anywhere: just type 'ashinedu' in any terminal
cd "$(dirname "$(readlink -f "$0")")"
python3 app/orchestrator.py "$@"
