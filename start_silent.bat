@echo off
rem 静默启动：不弹控制台窗口，只在托盘留图标
cd /d "%~dp0"
start "" pythonw reminder.py
