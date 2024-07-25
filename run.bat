@echo off
REM 更改工作目录到 src
cd /d "%~dp0src"

REM 使用虚拟环境中的 Python 解释器运行主程序
..\env\Scripts\python.exe main.py

REM 暂停，等待用户按任意键继续
pause
