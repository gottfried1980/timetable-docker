@echo off
setlocal
cd /d "%~dp0"
if not exist "public" mkdir "public"
copy /y "index.html" "public\index.html" >nul
if errorlevel 1 exit /b 1
copy /y "calendar.js" "public\calendar.js" >nul
if errorlevel 1 exit /b 1
copy /y "tasks.js" "public\tasks.js" >nul
if errorlevel 1 exit /b 1
copy /y "media.js" "public\media.js" >nul
if errorlevel 1 exit /b 1
python build-media.py
if errorlevel 1 exit /b 1
echo Tagesdisplay: http://127.0.0.1:3000/index.html
call json-server "..\todo_backend\db.json" --static "public" --host 127.0.0.1 --port 3000
