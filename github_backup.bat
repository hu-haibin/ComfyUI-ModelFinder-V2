@echo off
echo Backing up code to GitHub...

cd /d C:\Users\huhaibin\Desktop\comfyui_modelfinder\modelfinder2.0

echo 1. Checking git status...
git status

echo.
echo 2. Initializing git repository (if needed)...
git init

echo.
echo 3. Adding all files to staging area...
git add .

echo.
echo 4. Committing changes...
git commit -m "Initial code backup"

echo.
echo 5. Adding GitHub remote repository and pushing code...
git remote add origin https://github.com/hu-haibin/ModelFinder_V2.git
git push -u origin master

echo.
echo Backup completed!
echo Press any key to exit...
pause > nul 