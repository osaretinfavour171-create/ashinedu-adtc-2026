@echo off
:: Ashinedu — Global launcher
:: Run from anywhere: just type 'ashinedu' in any terminal
:: Use 'ashinedu --lite' for quick mode (Qwen only, ~2GB)
cd /d "C:\Users\HP\Desktop\Github Projects\ADTC Hackhathi\PidginPharma"
python app\orchestrator.py %*
