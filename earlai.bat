@echo off
:: EARL AI — Global launcher
:: Run from anywhere: just type 'earlai' in any terminal
:: Use 'earlai --lite' for quick mode (Qwen only, ~2GB)
cd /d "C:\Users\HP\Desktop\Github Projects\ADTC Hackhathi\PidginPharma"
python app\orchestrator.py %*
