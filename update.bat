@echo off

:: Display usage instructions
echo =========================================
echo          Python Project Updater
echo =========================================
echo:
echo This script will update your project files by copying the contents of the
echo 'project' folder into your project root directory, overwriting files with
echo the same name.
echo:
echo Instructions:
echo 1. If you do not see an 'update_package' folder, manually create a folder named 'update_package'
echo    and place this 'update.bat' file inside it. Then place the 'update_package' folder in your project root directory.
echo 2. Inside the 'update_package' folder, create another folder named 'project' and put the files and folders
echo    you wish to update into it. Any files with the same name in the project root will be overwritten.
echo 3. When running the script, you can choose whether to back up your existing project files.
echo    The backup will be stored in the 'project_backup' folder at the same level as your project root.
echo 4. The script will automatically update project files, excluding specified folders (e.g., Python_env).
echo 5. After updating, the script will use your Python environment (located in the Python_env folder)
echo    to update project dependencies.
echo:
echo How to run this script:
echo 1. Open the Command Prompt.
echo 2. Navigate to the project root directory containing the 'update_package' folder.
echo 3. In the Command Prompt, type 'update_package\update.bat' and press Enter to start the update process.
echo:

:: Set variables
SET "SCRIPT_DIR=%~dp0"
IF "%SCRIPT_DIR:~-1%"=="\" SET "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
PUSHD "%SCRIPT_DIR%\.."
SET "PROJECT_PATH=%CD%"
POPD
SET "BACKUP_PATH=%PROJECT_PATH%_backup"
SET "UPDATE_FILES_PATH=%SCRIPT_DIR%\project"
SET "PYTHON_PATH=%PROJECT_PATH%\Python_env\python.exe"

IF NOT EXIST "%UPDATE_FILES_PATH%" (
    echo Error: Cannot find the 'project' folder at "%UPDATE_FILES_PATH%".
    pause
    exit /b 1
)

echo =========================================
echo          Python Project Updater
echo =========================================
echo:
echo Project path: %PROJECT_PATH%
echo Update files path: %UPDATE_FILES_PATH%
echo Backup path: %BACKUP_PATH%
echo Python interpreter path: %PYTHON_PATH%
echo:

CHOICE /M "Do you want to continue with the update?"
IF %ERRORLEVEL% EQU 2 (
    echo Update canceled.
    pause
    exit /b 0
)

CHOICE /M "Do you want to back up the existing project files?"
IF %ERRORLEVEL% EQU 1 (
    echo Backing up project files to "%BACKUP_PATH%"...
    robocopy "%PROJECT_PATH%" "%BACKUP_PATH%" /E /XD "%SCRIPT_DIR%" "%BACKUP_PATH%" "%PROJECT_PATH%\Python_env"
    IF %ERRORLEVEL% GEQ 8 (
        echo Backup failed due to a critical error. Please check permissions or disk space.
        pause
        exit /b 1
    ) ELSE (
        echo Backup successful.
    )
) ELSE (
    echo Skipping backup.
)

echo Updating files...
robocopy "%UPDATE_FILES_PATH%" "%PROJECT_PATH%" /E /XO /R:3 /W:5 /XD Python_env update_package "%BACKUP_PATH%"
IF %ERRORLEVEL% GEQ 8 (
    echo Error occurred during file update!
    pause
    exit /b 1
) ELSE (
    echo Files updated successfully!
)

:: Update dependencies
echo.
echo Updating dependencies using requirements.txt
echo Installing dependencies...
"%PYTHON_PATH%" -m pip install --no-input --default-timeout=100 --no-warn-script-location --progress-bar off -r "%PROJECT_PATH%\requirements.txt"
IF EXIST "%PYTHON_PATH%" (
    IF EXIST "%PROJECT_PATH%\requirements.txt" (
        "%PYTHON_PATH%" -m pip install --no-input --default-timeout=100 --no-warn-script-location --progress-bar off -r "%PROJECT_PATH%\requirements.txt"
        
    )
) ELSE (
    echo Error: Cannot find Python interpreter at "%PYTHON_PATH%".
    pause
    exit /b 1
)


echo:
echo Update completed! You can now restart the application.
pause
