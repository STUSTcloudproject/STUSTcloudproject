@echo off
REM 更改工作目錄到 src
cd /d "%~dp0src"

REM 判斷虛擬環境是否存在
IF EXIST ..\env\Scripts\python.exe (
    REM 使用虛擬環境中的 Python 直譯器運行主程序
    ..\env\Scripts\python.exe main.py
) ELSE (
    REM 使用系統中的 Python 直譯器運行主程序
    python main.py
)

REM 暫停，等待用戶按任意鍵繼續
pause
