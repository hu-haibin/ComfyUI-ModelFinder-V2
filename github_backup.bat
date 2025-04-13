@echo off
echo Backing up code to GitHub...

cd /d C:\Users\huhaibin\Desktop\comfyui_modelfinder\modelfinder2.0

echo 1. Checking git status...
git status

echo.
echo 2. Adding all files to staging area...
git add .

echo.
echo 3. Committing changes...
git commit -m "Code backup update"

echo.
echo 4. Pushing changes to GitHub...
git push origin commercial-features

echo.
echo Backup completed!
echo Press any key to exit...
pause > nul 