@echo off
echo 正在备份代码到GitHub...

cd /d C:\Users\huhaibin\Desktop\comfyui_modelfinder\modelfinder2.0

echo 1. 检查git状态...
git status

echo.
echo 2. 初始化git仓库(如果需要)...
git init

echo.
echo 3. 添加所有文件到暂存区...
git add .

echo.
echo 4. 提交更改...
git commit -m "初始代码备份"

echo.
echo 5. 添加GitHub远程仓库并推送代码...
git remote add origin https://github.com/hu-haibin/ModelFinder_V2.git
git push -u origin master

echo.
echo 备份完成！
echo 请按任意键退出...
pause > nul 