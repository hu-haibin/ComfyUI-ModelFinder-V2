"""
File Management Module
Contains functions for creating structured output directories, cleaning old files, etc.
"""

import os
import time
import shutil
from datetime import datetime
import ctypes
import sys
import platform
import subprocess

def is_admin():
    """Check if the program is running with administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Attempt to restart the program with administrator privileges"""
    try:
        if not is_admin():
            # Get the full path of the current program
            script = sys.executable
            params = sys.argv
            params.insert(0, script)
            
            # Use ShellExecute to restart the program with administrator privileges
            ctypes.windll.shell32.ShellExecuteW(None, "runas", script, " ".join(params), None, 1)
            # Exit the current instance
            sys.exit()
        return True
    except Exception as e:
        print(f"Failed to request administrator privileges: {e}")
        return False

def create_output_directory():
    """Create an organized output directory structure
    
    Returns:
        Path to the created output directory
    """
    try:
        # Use the improved get_results_folder function to get the base directory
        base_dir = get_results_folder()
        
        # Create a subfolder using the current date
        today = datetime.now()
        date_dir = os.path.join(base_dir, f"{today.year:04d}-{today.month:02d}-{today.day:02d}")
        
        # Ensure the directory exists
        os.makedirs(date_dir, exist_ok=True)
        
        return date_dir
    except Exception as e:
        # If an error occurs, use a temporary directory
        import tempfile
        today = datetime.now()
        date_str = f"{today.year:04d}-{today.month:02d}-{today.day:02d}"
        temp_dir = os.path.join(tempfile.gettempdir(), f"ModelFinder_Results/{date_str}")
        print(f"Error creating output directory: {e}, using temporary directory: {temp_dir}")
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir

def get_output_path(original_file, extension=None, prefix=""):
    """Generate output file path based on the original file name.
    
    Args:
        original_file: Path to the original file.
        extension: Optional file extension (without dot). Keeps original if None.
        prefix: Optional prefix to add to the base file name.
    
    Returns:
        Full path for the output file.
    """
    # Create output directory
    output_dir = create_output_directory()
    
    # Get base name (without path)
    base_name = os.path.basename(original_file)
    
    # If new extension provided, replace the old one
    if extension:
        name_part = os.path.splitext(base_name)[0]
        base_name = f"{name_part}.{extension}"
    
    # Add prefix if provided
    if prefix:
        base_name = f"{prefix}{base_name}"
        
    # Return full path
    return os.path.join(output_dir, base_name)

def cleanup_old_results(days_to_keep=30):
    """Clean up result files older than the specified number of days
    
    Args:
        days_to_keep: Number of days to keep files, default 30 days
    
    Returns:
        Number of cleaned folders
    """
    try:
        # Use the improved get_results_folder function to get the base directory
        base_dir = get_results_folder()
        
        if not os.path.exists(base_dir):
            print(f"Results directory does not exist: {base_dir}")
            return 0
        
        current_time = time.time()
        cleaned_count = 0
        
        # Check each date folder
        for dir_name in os.listdir(base_dir):
            dir_path = os.path.join(base_dir, dir_name)
            if os.path.isdir(dir_path):
                # Get directory modification time
                dir_time = os.path.getmtime(dir_path)
                # If older than the specified number of days
                if (current_time - dir_time) / (24 * 3600) > days_to_keep:
                    try:
                        shutil.rmtree(dir_path)
                        print(f"Cleaned old results directory: {dir_path}")
                        cleaned_count += 1
                    except Exception as e:
                        print(f"Error cleaning directory: {e}")
        
        return cleaned_count
    except Exception as e:
        print(f"Error cleaning old results: {e}")
        return 0

def get_results_folder():
    """Get the path of the results folder
    
    Returns:
        Full path of the results folder
    """
    try:
        # Get the directory where the application is located
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller bundled environment
            base_path = sys._MEIPASS
            print(f"Using PyInstaller base path: {base_path}")
        else:
            # Development environment
            # First try to get the directory of the current module
            base_path = os.path.dirname(os.path.abspath(__file__))
            print(f"File manager module path: {base_path}")
            
            # If in the model_finder subdirectory, move up one level
            if os.path.basename(base_path) == 'model_finder':
                base_path = os.path.dirname(base_path)
                print(f"Moved up to parent directory: {base_path}")
        
        # If the above logic fails, try using the current working directory
        if not os.path.exists(base_path):
            base_path = os.getcwd()
            print(f"Using current working directory: {base_path}")
        
        # Results folder under the application directory
        results_dir = os.path.join(base_path, "results")
        print(f"Results directory: {results_dir}")
        
        # Ensure the directory exists
        os.makedirs(results_dir, exist_ok=True)
        
        # Re-verify if the directory is accessible
        if not os.path.exists(results_dir) or not os.access(results_dir, os.W_OK):
            # If not accessible, fallback to the user's documents directory
            import ctypes.wintypes
            CSIDL_PERSONAL = 5  # My Documents
            SHGFP_TYPE_CURRENT = 0  # Current value
            
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
            
            # Create a results folder under My Documents
            docs_path = buf.value
            results_dir = os.path.join(docs_path, "ModelFinder_Results")
            print(f"Using fallback results directory: {results_dir}")
            os.makedirs(results_dir, exist_ok=True)
        
        return results_dir
    except Exception as e:
        # Use temporary directory on error
        import tempfile
        temp_dir = os.path.join(tempfile.gettempdir(), "ModelFinder_Results")
        print(f"Error getting results directory: {e}, using temporary directory: {temp_dir}")
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir

def open_directory(path):
    """Opens the specified directory in the default file explorer."""
    if not os.path.isdir(path):
        print(f"Error: Directory not found at {path}")
        return

    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", path], check=True)
        else:  # Linux and other Unix-like
            subprocess.run(["xdg-open", path], check=True)
        print(f"Opened directory: {path}")
    except FileNotFoundError:
        print(f"Error: Could not find the necessary command (open/xdg-open) to open the directory.")
    except Exception as e:
        print(f"Error opening directory {path}: {e}")