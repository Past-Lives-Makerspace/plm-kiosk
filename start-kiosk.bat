@echo off
cd /d C:\Users\PC\kiosk
rmdir /s /q __pycache__ 2>nul
start /min "" "C:\Program Files\Python312\python.exe" kiosk.py
ping 127.0.0.1 -n 8 > nul
start "" "C:\Program Files\Python312\pythonw.exe" launcher.pyw
