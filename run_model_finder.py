#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Model Finder Launcher
This script handles the startup of the Model Finder application
"""

import os
import sys
import traceback

def main():
    try:
        print("Starting Model Finder 2.0...")
        
        # Add the current directory to the Python path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # First try to import necessary components
        try:
            import tkinter as tk
            from tkinter import messagebox
        except ImportError:
            print("ERROR: Tkinter not available. Please install Python with Tkinter support.")
            input("Press Enter to exit...")
            return
        
        # Check for required packages
        missing_packages = []
        required_packages = ["pandas", "DrissionPage", "ttkbootstrap"]
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"✓ {package} is installed")
            except ImportError:
                print(f"✗ Missing {package}")
                missing_packages.append(package)
        
        # If missing packages, ask to install
        if missing_packages:
            root = tk.Tk()
            root.withdraw()
            result = messagebox.askyesno(
                "Missing Dependencies",
                f"The following packages are required but not installed:\n" +
                "\n".join(missing_packages) + 
                "\n\nWould you like to install them now?"
            )
            root.destroy()
            
            if result:
                print("Installing missing packages...")
                try:
                    import subprocess
                    cmd = [sys.executable, "-m", "pip", "install", 
                           "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"]
                    cmd.extend(missing_packages)
                    subprocess.check_call(cmd)
                    print("Packages installed successfully!")
                except Exception as e:
                    print(f"Error installing packages: {e}")
                    input("Press Enter to exit...")
                    return
            else:
                print("Cannot continue without required packages.")
                input("Press Enter to exit...")
                return
        
        # 检查许可证状态
        try:
            from model_finder.licensing import license_manager
            status = license_manager.get_license_status()
            membership = license_manager.get_membership_type()
            credits = license_manager.get_credits()
            print(f"许可证状态: {status}, 会员级别: {membership}, 积分: {credits}")
            
            # 每日签到
            signed, earned = license_manager.check_daily_signin()
            if signed:
                print(f"每日签到成功，获得{earned}积分！")
        except Exception as e:
            print(f"WARNING: Could not check license: {e}")
        
        # 清理旧文件
        try:
            from model_finder.file_manager import cleanup_old_results
            cleaned = cleanup_old_results(days_to_keep=7)  # 保留7天的文件
            if cleaned > 0:
                print(f"已清理 {cleaned} 个旧结果目录")
        except ImportError:
            pass  # 如果无法导入，则不执行清理
        
        # Now try to import and start the Model Finder
        try:
            # Import from model_finder directory
            from model_finder.model_finder import main as start_app
            
            # Start the application
            print("Launching Model Finder...")
            start_app()
            
        except ImportError as e:
            print(f"ERROR: Could not import Model Finder: {e}")
            traceback.print_exc()
            input("Press Enter to exit...")
            return
            
        except Exception as e:
            print(f"ERROR: Failed to start Model Finder: {e}")
            traceback.print_exc()
            input("Press Enter to exit...")
            return
    
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()