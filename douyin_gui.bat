@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动 抖音无水印下载器 图形界面...
python douyin_dl.py --gui
echo.
pause
