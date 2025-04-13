#!/usr/bin/env python
"""
===== ComfyUI Model Finder v2.0 =====
Function: Detect missing models and generate download links.
Features:
- Beautiful and intuitive interface
- Single workflow processing
- Batch workflow processing with one-click search
- Automatic search for download links
- HTML result view
- Random theme styles
Version: 2.0.1
Date: 2024-04-15
Contact: WeChat wangdefa4567
"""

import os
import sys
import time
import glob
import json
import csv
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Import custom modules
from .utils import (
    get_mirror_link,
    check_dependencies,
    create_html_view,
)
from .file_manager import (
    create_output_directory,
    cleanup_old_results,
    get_output_path,
    open_directory
)
from .licensing import (
    license_manager,
    LICENSE_VALID, LICENSE_EXPIRED, LICENSE_INVALID, LICENSE_TRIAL, LICENSE_FREE,
    MEMBERSHIP_FREE, MEMBERSHIP_BASIC, MEMBERSHIP_PRO
)
from .core import (
    find_missing_models, 
    create_csv_file, 
    search_model_links,
    batch_process_workflows
)
from . import __version__, __author__

# Execute dependency check
check_dependencies()

# Import dependencies
try:
    import ttkbootstrap
except ImportError:
    ttk.Style = ttk.Style

class ModelFinderApp:
    def __init__(self, root):
        try:
            # Basic window settings
            self.root = root
            self.root.title(f"ComfyUI Model Finder - Model Finder v{__version__} (WeChat: {__author__})")
            self.root.geometry("700x600")
            
            # Initialize important variables first to ensure they always exist
            # Store HTML file path
            self.html_file_path = None
            
            # Explicitly assign these variables to root to avoid binding errors
            self.auto_open_html = tk.BooleanVar(root, value=True)
            self.use_bing_search = tk.BooleanVar(root, value=True)
            
            print("Variables initialized successfully")
            
            # Set ttkbootstrap theme
            style = ttk.Style()
            self.themes = style.theme_names()
            self.current_theme = "cosmo"  # Default theme
            try:
                style.theme_use(self.current_theme)
                print(f"Successfully applied theme: {self.current_theme}")
            except tk.TclError as e:
                print(f"Warning: Failed to apply theme '{self.current_theme}': {e}. Falling back to default.")
                # Optionally try a basic theme guaranteed to exist
                try:
                     style.theme_use('clam') # 'clam' is usually available
                     self.current_theme = 'clam'
                except tk.TclError:
                    print("Warning: Could not even apply fallback theme 'clam'. Using system default.")
                    self.current_theme = style.theme_use() # Get the actual default

            # Create notebook (tabs)
            self.notebook = ttk.Notebook(root)
            self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Create three tabs
            self.tab_single = ttk.Frame(self.notebook)
            self.tab_batch = ttk.Frame(self.notebook)
            self.tab_settings = ttk.Frame(self.notebook)
            self.tab_license = ttk.Frame(self.notebook)  # New license tab

            self.notebook.add(self.tab_single, text="Single Process")
            self.notebook.add(self.tab_batch, text="Batch Process")
            self.notebook.add(self.tab_settings, text="Settings")
            self.notebook.add(self.tab_license, text="License")  # Add license tab

            # Status bar
            self.status_var = tk.StringVar(value="Ready")
            status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
            status_bar.pack(side=tk.BOTTOM, fill=tk.X)
            
            # Set up content for each tab
            self.setup_single_tab()
            self.setup_batch_tab()
            self.setup_settings_tab()
            self.setup_license_tab()  # Setup license tab
            # Check license status
            self.check_and_apply_license_limits()
            
        except Exception as e:
            print(f"Error initializing GUI: {e}")
            if not hasattr(self, 'auto_open_html'):
                print("Fixing auto_open_html variable...")
                self.auto_open_html = tk.BooleanVar(root, value=True)
            if not hasattr(self, 'use_bing_search'):
                print("Fixing use_bing_search variable...")
                self.use_bing_search = tk.BooleanVar(root, value=True)
            
            # Display error message
            import traceback
            traceback.print_exc()
            
            try:
                tk.messagebox.showerror("Initialization Error", f"Error during initialization: {str(e)}\nAttempted to fix. Please restart the application if the problem persists.")
            except:
                print("Unable to display error message window")
    
    def setup_single_tab(self):
        """Set up the single processing tab"""
        # Create main frame
        main_frame = ttk.Frame(self.tab_single, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Workflow processing label
        ttk.Label(main_frame, text="Workflow Processing", font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        
        # Workflow file selection
        ttk.Label(main_frame, text="Workflow File").grid(row=1, column=0, sticky="w")
        self.workflow_path = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.workflow_path, width=50).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_workflow).grid(row=1, column=2, padx=5)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, sticky="w", pady=10)
        ttk.Button(button_frame, text="Analyze and Search", style="success.TButton", command=self.analyze_and_search).pack(side=tk.LEFT, padx=(0, 5))
        self.view_result_button_single = ttk.Button(button_frame, text="View Result", command=self.view_result, state=tk.DISABLED)
        self.view_result_button_single.pack(side=tk.LEFT)
        
        # Progress bar
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5)
        ttk.Label(progress_frame, text="Progress:").pack(side=tk.LEFT, padx=(0, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(main_frame, orient="horizontal").grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)
        
        # Log area
        ttk.Label(main_frame, text="Processing Log:").grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 5))
        
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=(0, 5))
        
        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Make main frame columns/rows resizable
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        # Initialize log
        self.show_welcome_message()
    
    def setup_batch_tab(self):
        """Set up the batch processing tab"""
        # Create main frame
        main_frame = ttk.Frame(self.tab_batch, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Batch workflow processing label
        ttk.Label(main_frame, text="Batch Workflow Processing and Search", font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        
        # Workflow directory selection
        ttk.Label(main_frame, text="Workflow Directory").grid(row=1, column=0, sticky="w")
        self.workflow_dir = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.workflow_dir, width=50).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Button(main_frame, text="Browse...", command=self.browse_workflow_dir).grid(row=1, column=2, padx=5)

        # File format selection
        ttk.Label(main_frame, text="File Pattern:").grid(row=2, column=0, sticky="w", pady=5)
        self.file_pattern = tk.StringVar(value="*.json;*")
        ttk.Entry(main_frame, textvariable=self.file_pattern, width=20).grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        # Options
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=5)
        ttk.Checkbutton(options_frame, text="Create Merged CSV", variable=tk.BooleanVar(value=True), state=tk.DISABLED).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(options_frame, text="Auto Open Result", variable=self.auto_open_html).pack(side=tk.LEFT)
        
        # Button - Keep only "Start Processing and Search" button
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=4, column=0, columnspan=3, sticky="w", pady=10)
        ttk.Button(buttons_frame, text="Start Processing and Search", style="success.TButton",
                command=self.batch_process).pack(side=tk.LEFT)
        
        # Progress bar
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)
        ttk.Label(progress_frame, text="Progress:").pack(side=tk.LEFT, padx=(0, 5))
        self.batch_progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.batch_progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.batch_progress_label = ttk.Label(progress_frame, text="0%")
        self.batch_progress_label.pack(side=tk.LEFT, padx=5)
        
        # Processing results area
        ttk.Label(main_frame, text="Processing Results:").grid(row=6, column=0, columnspan=3, sticky="w", pady=(10, 5))
        
        result_frame = ttk.Frame(main_frame)
        result_frame.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=(0, 5))
        
        # Use Treeview to display results
        columns = ("File Name", "Missing Count", "Status")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=10)
        
        # Set column headings
        for col in columns:
            self.result_tree.heading(col, text=col)
            self.result_tree.column(col, width=100)
        
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_tree.config(yscrollcommand=scrollbar.set)
        
        # View HTML button
        ttk.Button(main_frame, text="View HTML", command=self.view_batch_html).grid(row=8, column=0, columnspan=3, sticky="w", pady=10)
        
        # Make main frame columns/rows resizable
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(7, weight=1)

    def setup_settings_tab(self):
        """Set up the settings tab"""
        # Create main frame with scrollbar
        main_frame = ttk.Frame(self.tab_settings)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Application settings section
        app_frame = ttk.LabelFrame(main_frame, text="Application Settings")
        app_frame.pack(fill="x", pady=5)

        # Auto open HTML result switch
        auto_html_frame = ttk.Frame(app_frame)
        auto_html_frame.pack(fill="x", padx=5, pady=5)

        self.auto_open_html = tk.BooleanVar(value=True)
        ttk.Checkbutton(auto_html_frame, text="Auto open HTML result after search",
                    variable=self.auto_open_html).pack(side="left", padx=5)

        # Chrome browser path setting
        chrome_frame = ttk.Frame(app_frame)
        chrome_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(chrome_frame, text="Chrome Path:").pack(side="left", padx=5)
        self.chrome_path_var = tk.StringVar()
        ttk.Entry(chrome_frame, textvariable=self.chrome_path_var, width=50).pack(side="left", fill="x", expand=True)
        ttk.Button(chrome_frame, text="Browse", command=self.browse_chrome).pack(side="left", padx=5)

        # Add theme selection section
        theme_frame = ttk.LabelFrame(main_frame, text="Interface Theme")
        theme_frame.pack(fill="x", pady=5)

        # Theme selection dropdown
        theme_select_frame = ttk.Frame(theme_frame)
        theme_select_frame.pack(fill="x", padx=5, pady=5)

        self.theme_names = [
            "flatly", "darkly", "litera", "minty", "lumen", "sandstone",
            "yeti", "pulse", "united", "morph", "journal", "solar"
        ]

        self.theme_var = tk.StringVar()

        ttk.Label(theme_select_frame, text="Select Theme:").pack(side="left", padx=5)
        theme_dropdown = ttk.Combobox(theme_select_frame, textvariable=self.theme_var,
                                    values=self.theme_names, state="readonly")
        theme_dropdown.pack(side="left", padx=5)
        theme_dropdown.current(0)

        ttk.Button(theme_select_frame, text="Apply Theme",
                command=self.apply_theme).pack(side="left", padx=5)

        # Add random theme option
        random_theme_frame = ttk.Frame(theme_frame)
        random_theme_frame.pack(fill="x", padx=5, pady=5)

        self.random_theme = tk.BooleanVar(value=True)
        ttk.Checkbutton(random_theme_frame, text="Use random theme on startup",
                    variable=self.random_theme).pack(side="left", padx=5)

        # Add file management section
        file_frame = ttk.LabelFrame(main_frame, text="File Management")
        file_frame.pack(fill="x", pady=5)

        # Add file management description
        ttk.Label(file_frame, text="All result files are saved in the 'results' folder, organized by date").pack(anchor="w", padx=5, pady=2)

        # Retention days setting
        retention_frame = ttk.Frame(file_frame)
        retention_frame.pack(fill="x", padx=5, pady=5)

        self.retention_days = tk.IntVar(value=30)
        ttk.Label(retention_frame, text="Retention Days:").pack(side="left", padx=5)
        ttk.Spinbox(retention_frame, from_=1, to=365, width=5,
                    textvariable=self.retention_days).pack(side="left")

        # Add button frame
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)

        # Add cleanup button
        cleanup_btn = ttk.Button(btn_frame, text="Cleanup Old Files", command=self.cleanup_old_files)
        cleanup_btn.pack(side="left", padx=5)

        # Add open results folder button
        open_folder_btn = ttk.Button(btn_frame, text="Open Results Folder", command=self.open_results_folder)
        open_folder_btn.pack(side="left", padx=5)

        # Save settings button
        save_frame = ttk.Frame(main_frame)
        save_frame.pack(fill="x", pady=10)

        ttk.Button(save_frame, text="Save Settings",
                command=self.save_settings).pack(side="right", padx=5)

        # Load saved settings
        self.load_settings()

    def setup_license_tab(self):
        """Set up the license tab"""
        # Create main frame
        main_frame = ttk.Frame(self.tab_license)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # License information section
        info_frame = ttk.LabelFrame(main_frame, text="License Information")
        info_frame.pack(fill="x", pady=5)

        # Get current license information
        license_status = license_manager.get_license_status()
        membership_type = license_manager.get_membership_type()
        credits = license_manager.get_credits()

        # Display license status
        status_frame = ttk.Frame(info_frame)
        status_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(status_frame, text="License Status:").pack(side="left", padx=5)

        # Status display with color coding for different states
        self.license_status_var = tk.StringVar()
        self.set_license_status_display(license_status)
        ttk.Label(status_frame, textvariable=self.license_status_var).pack(side="left", padx=5)

        # Membership type
        member_frame = ttk.Frame(info_frame)
        member_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(member_frame, text="Membership Type:").pack(side="left", padx=5)

        self.membership_var = tk.StringVar()
        self.set_membership_display(membership_type)
        ttk.Label(member_frame, textvariable=self.membership_var).pack(side="left", padx=5)

        # Current credits
        credit_frame = ttk.Frame(info_frame)
        credit_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(credit_frame, text="Current Credits:").pack(side="left", padx=5)

        self.credits_var = tk.StringVar(value=str(credits))
        ttk.Label(credit_frame, textvariable=self.credits_var).pack(side="left", padx=5)

        # Daily sign-in section
        signin_frame = ttk.LabelFrame(main_frame, text="Daily Sign-in")
        signin_frame.pack(fill="x", pady=5)

        ttk.Label(signin_frame, text="Daily sign-in earns extra credits. Rewards vary by membership type.").pack(anchor="w", padx=5, pady=2)

        signin_btn_frame = ttk.Frame(signin_frame)
        signin_btn_frame.pack(fill="x", padx=5, pady=5)

        self.signin_btn = ttk.Button(signin_btn_frame, text="Sign in for Credits",
                                command=self.daily_signin)
        self.signin_btn.pack(side="left", padx=5)

        # Activation code section
        activate_frame = ttk.LabelFrame(main_frame, text="Activate License")
        activate_frame.pack(fill="x", pady=5)

        ttk.Label(activate_frame, text="Enter activation code to activate software or add credits.").pack(anchor="w", padx=5, pady=2)

        # Activation code input
        code_frame = ttk.Frame(activate_frame)
        code_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(code_frame, text="Activation Code:").pack(side="left", padx=5)

        self.activation_code = tk.StringVar()
        ttk.Entry(code_frame, textvariable=self.activation_code, width=30).pack(side="left", padx=5)

        ttk.Button(code_frame, text="Activate",
                command=self.activate_license).pack(side="left", padx=5)

        # Feature limits description
        limits_frame = ttk.LabelFrame(main_frame, text="Feature Limits")
        limits_frame.pack(fill="x", pady=5)

        limits_info = (
            "Free Version: 3 single analyses, 1 batch analysis per day\n"
            "Basic Membership: 10 single analyses, 3 batch analyses per day\n"
            "Pro Membership: Unlimited use of all features\n\n"
            "Credits can be used to continue using features after reaching daily limits."
        )

        ttk.Label(limits_frame, text=limits_info, justify="left").pack(anchor="w", padx=5, pady=5)

        # Refresh license info button
        refresh_frame = ttk.Frame(main_frame)
        refresh_frame.pack(fill="x", pady=10)

        ttk.Button(refresh_frame, text="Refresh License Info",
                command=self.refresh_license_info).pack(side="right", padx=5)

    def set_license_status_display(self, status):
        """Set the display for license status"""
        status_display = {
            LICENSE_VALID: "Valid",
            LICENSE_EXPIRED: "Expired",
            LICENSE_INVALID: "Invalid",
            LICENSE_TRIAL: "Trial",
            LICENSE_FREE: "Free"
        }

        self.license_status_var.set(status_display.get(status, "Unknown"))

    def set_membership_display(self, membership):
        """Set the display for membership type"""
        membership_display = {
            MEMBERSHIP_FREE: "Free",
            MEMBERSHIP_BASIC: "Basic",
            MEMBERSHIP_PRO: "Pro"
        }

        self.membership_var.set(membership_display.get(membership, "Unknown"))

    def daily_signin(self):
        """Execute daily sign-in"""
        success, credits = license_manager.check_daily_signin()

        if success:
            messagebox.showinfo("Sign-in Successful", f"Sign-in successful, received {credits} credits.")
            # Refresh display
            self.refresh_license_info()
        else:
            messagebox.showinfo("Already Signed In", "You have already signed in today. Come back tomorrow!")

    def activate_license(self):
        """Activate the license"""
        activation_code = self.activation_code.get().strip()
        if not activation_code:
            messagebox.showerror("Error", "Please enter an activation code.")
            return

        success, message = license_manager.validate_activation_code(activation_code)

        if success:
            messagebox.showinfo("Activation Successful", message)
            # Refresh license info display
            self.refresh_license_info()
            # Clear activation code input
            self.activation_code.set("")
            # Update feature limits
            self.check_and_apply_license_limits()
        else:
            messagebox.showerror("Activation Failed", message)

    def refresh_license_info(self):
        """Refresh the license information display"""
        license_status = license_manager.get_license_status()
        membership_type = license_manager.get_membership_type()
        credits = license_manager.get_credits()

        self.set_license_status_display(license_status)
        self.set_membership_display(membership_type)
        self.credits_var.set(str(credits))

    def check_and_apply_license_limits(self):
        """Check and apply license limits"""
        # Implement license limit check and application logic
        # Check usage rights for single and batch analysis features
        can_use_single, reason_single = license_manager.can_use_feature("single_analysis", 2)
        can_use_batch, reason_batch = license_manager.can_use_feature("batch_analysis", 5)

        # Disable or enable corresponding features
        for child in self.tab_single.winfo_children():
            for widget in child.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for btn in widget.winfo_children():
                        if isinstance(btn, ttk.Button) and btn['text'].startswith("Analyze and Search"): # Check prefix
                            if can_use_single:
                                btn.config(state=tk.NORMAL)
                                btn.config(text="Analyze and Search")
                            else:
                                # Use translated reason from license manager if available, otherwise use default
                                if reason_single == "使用积分":
                                    reason_en = "Use Credits"
                                    btn.config(state=tk.NORMAL)
                                    btn.config(text="Analyze and Search (Use Credits)")
                                else:
                                    # Translate other potential reasons if needed
                                    reason_en = "Daily limit reached" if "每日使用上限" in reason_single else reason_single
                                    btn.config(state=tk.DISABLED)
                                    btn.config(text="Analyze and Search") # Reset text when disabled


        for child in self.tab_batch.winfo_children():
            for widget in child.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for btn in widget.winfo_children():
                         if isinstance(btn, ttk.Button) and btn['text'].startswith("Start Processing and Search"): # Check prefix
                            if can_use_batch:
                                btn.config(state=tk.NORMAL)
                                btn.config(text="Start Processing and Search")
                            else:
                                if reason_batch == "使用积分":
                                    reason_en = "Use Credits"
                                    btn.config(state=tk.NORMAL)
                                    btn.config(text="Start Processing and Search (Use Credits)")
                                else:
                                    reason_en = "Daily limit reached" if "每日使用上限" in reason_batch else reason_batch
                                    btn.config(state=tk.DISABLED)
                                    btn.config(text="Start Processing and Search") # Reset text when disabled


        # Update status bar to show license status
        license_status = license_manager.get_license_status()
        membership_type = license_manager.get_membership_type()
        self.status_var.set(f"License Status: {license_status}, Membership: {membership_type}, Credits: {license_manager.get_credits()}")
    
    def browse_workflow(self):
        """Browse for workflow file"""
        file_path = filedialog.askopenfilename(
            title="Select Workflow File",
            filetypes=[("JSON File", "*.json"), ("All Files", "*.*")]
        )
        if file_path:
            self.workflow_path.set(file_path)
    
    def browse_workflow_dir(self):
        """Browse for workflow directory"""
        dir_path = filedialog.askdirectory(title="Select Workflow Directory")
        if dir_path:
            self.workflow_dir.set(dir_path)
    
    def browse_chrome(self):
        """Browse for Chrome executable file"""
        file_path = filedialog.askopenfilename(
            title="Select Chrome Executable",
            filetypes=[
                ("Chrome Executable", "chrome.exe"),
                ("Executable File", "*.exe"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.chrome_path_var.set(file_path)

    def open_results_folder(self):
        """Open the results folder"""
        try:
            output_dir = create_output_directory()
            open_directory(output_dir)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open results folder: {str(e)}")

    def cleanup_old_files(self):
        """Cleanup old result files"""
        try:
            days = self.retention_days.get()
            if days <= 0:
                messagebox.showerror("Error", "Retention days must be greater than 0.")
                return

            if messagebox.askyesno("Confirm", f"Are you sure you want to delete result files older than {days} days?\nThis action cannot be undone."):
                cleaned = cleanup_old_results(days)
                messagebox.showinfo("Cleanup Complete", f"Cleanup finished. Deleted {cleaned} files or directories.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to cleanup files: {str(e)}")

    def show_welcome_message(self):
        """Display welcome message"""
        welcome_message = f"""Welcome to ComfyUI Model Finder v{__version__}

Usage:
1. Select a workflow JSON file
2. Click the "Analyze and Search" button
3. Wait for the analysis and search to complete
4. View the HTML result

If you encounter any issues, please contact: WeChat {__author__}
"""
        self.log_text.insert(tk.END, welcome_message)
    
    def analyze_and_search(self):
        """Analyze workflow and search for links"""
        workflow_file = self.workflow_path.get().strip()
        if not workflow_file:
            messagebox.showerror("Error", "Please select a workflow JSON file.")
            return
        
        if not os.path.exists(workflow_file):
            messagebox.showerror("Error", "File does not exist.")
            return
        # Check license status
        can_use, reason = license_manager.can_use_feature("single_analysis", 2)


        if not can_use:
            if reason == "使用积分": # Use the specific reason code from licensing
                # Prompt user to use credits
                if messagebox.askyesno("Use Credits", "You have used up your free analyses for today. Use 2 credits to continue?"):
                    if license_manager.use_credits(2):
                        # Continue execution
                        pass
                    else:
                        messagebox.showerror("Error", "Insufficient credits.")
                        return
                else:
                    return
            else:
                # Translate the reason if possible, otherwise show original
                # Assuming other reasons might be in Chinese from licensing.py
                reason_en = "Daily limit reached" if "每日使用上限" in reason else reason
                messagebox.showerror("Limited Feature", f"Cannot use this feature: {reason_en}")
                return

        # Record usage
        license_manager.record_usage("single_analysis")

        # Clear log
        self.log_text.delete(1.0, tk.END)
        self.status_var.set("Analyzing...")
        
        # Redirect stdout to Text widget
        class StdoutRedirector:
            def __init__(self, text_widget):
                self.text_widget = text_widget
            
            def write(self, string):
                self.text_widget.insert(tk.END, string)
                self.text_widget.see(tk.END)
                self.text_widget.update_idletasks()
            
            def flush(self):
                pass
        
        old_stdout = sys.stdout
        sys.stdout = StdoutRedirector(self.log_text)
        
        try:
            # Analyze workflow
            missing_files, status = find_missing_models(workflow_file)
            
            if missing_files:
                # Create CSV file
                output_file = os.path.basename(workflow_file)
                # Use English name for CSV
                csv_file = create_csv_file(missing_files, output_file, filename_prefix="Missing_Models_")
                
                if csv_file:
                    # Perform search
                    self.search_links(csv_file)
                    # Enable view result button after analysis
                    self.view_result_button_single.config(state=tk.NORMAL)
                else:
                    messagebox.showinfo("Complete", "Failed to create CSV file.")
                    self.status_var.set("Analysis complete, but failed to create CSV.")
            else:
                messagebox.showinfo("Complete", "No missing files found.")
                self.status_var.set("Analysis complete: No missing files.")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error during analysis: {str(e)}")
            self.status_var.set("Analysis failed.")
        
        finally:
            # Restore stdout
            sys.stdout = old_stdout
    
            # Refresh license info
            self.refresh_license_info()
    
    def search_links(self, csv_file):
        """Search for model download links"""
        if not os.path.exists(csv_file):
            messagebox.showerror("Error", "CSV file does not exist.")
            return
        
        # Reset progress bar
        self.progress_bar['value'] = 0
        self.progress_label.config(text="0%")
        
        # Disable buttons
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.config(state=tk.DISABLED)
        
        # Execute search in a separate thread to avoid freezing the interface
        def search_thread():
            # Update progress bar callback function
            def update_progress(current, total):
                if total > 0:
                    percentage = int((current / total) * 100)
                    self.root.after(0, lambda: self.progress_bar.config(value=percentage))
                    self.root.after(0, lambda: self.progress_label.config(text=f"{percentage}%"))
            
            try:
                result = search_model_links(csv_file, progress_callback=update_progress)
                
                if isinstance(result, str) and os.path.exists(result):
                    self.html_file_path = result
                    self.status_var.set("Search completed")
                    
                    # Ensure progress bar shows 100%
                    self.root.after(0, lambda: self.progress_bar.config(value=100))
                    self.root.after(0, lambda: self.progress_label.config(text="100%"))
                    
                    # Enable view result button
                    for widget in self.tab_single.winfo_children():
                        if isinstance(widget, ttk.Frame):
                            for child in widget.winfo_children():
                                if isinstance(child, ttk.Frame):
                                    for btn in child.winfo_children():
                                        if isinstance(btn, ttk.Button) and btn['text'] == "View Result":
                                            self.root.after(0, lambda: btn.config(state=tk.NORMAL))
                    
                    # If auto open is enabled, open the HTML result
                    if self.auto_open_html.get():
                        self.root.after(0, lambda: webbrowser.open(result))
                    
                    self.root.after(0, lambda: messagebox.showinfo("Complete", "Search completed, HTML result is ready to view."))
                else:
                    self.status_var.set("Search completed, but no HTML result generated")
                    self.root.after(0, lambda: messagebox.showinfo("Complete", "Search completed"))
            
            except Exception as e:
                error_msg = str(e)  # Capture error immediately
                self.status_var.set("Search failed")
                self.root.after(0, lambda error=error_msg: messagebox.showerror("Error", f"Search error: {error}"))
           
            
            finally:
                # Enable buttons
                self.root.after(0, lambda: self.enable_buttons())
        
        threading.Thread(target=search_thread, daemon=True).start()
    
    def enable_buttons(self):
        """Enable all buttons"""
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Notebook):
                for tab in [self.tab_single, self.tab_batch, self.tab_settings, self.tab_license]: # Included license tab
                    for child in tab.winfo_children():
                        if isinstance(child, ttk.Frame):
                            for grandchild in child.winfo_children():
                                if isinstance(grandchild, ttk.Button):
                                    grandchild.config(state=tk.NORMAL)
                                # Handle nested frames (like button frames)
                                if isinstance(grandchild, ttk.Frame):
                                    for btn in grandchild.winfo_children():
                                        if isinstance(btn, ttk.Button):
                                            btn.config(state=tk.NORMAL)
        # Re-apply license limits after enabling all buttons
        self.check_and_apply_license_limits()
    
    def view_result(self):
        """View HTML result"""
        if self.html_file_path and os.path.exists(self.html_file_path):
            webbrowser.open(self.html_file_path)
        else:
            # Try to infer HTML file path based on workflow file name
            workflow_file = self.workflow_path.get().strip()
            if workflow_file:
                # Use the same logic as create_csv_file (potentially)
                # or assume a standard naming convention if view_result is only for single analysis
                basename = os.path.splitext(os.path.basename(workflow_file))[0]
                # Use English name for HTML
                html_file = get_output_path(workflow_file, extension="html", prefix="Missing_Models_")
                if os.path.exists(html_file):
                    webbrowser.open(html_file)
                    return
                else:
                    # Fallback to old name if new name doesnt exist
                    html_file_old = get_output_path(workflow_file, extension="html")
                    if os.path.exists(html_file_old):
                         webbrowser.open(html_file_old)
                    return
            
            messagebox.showerror("Error", "HTML result file does not exist or cannot be inferred.")
   

    def batch_process(self):
        """Batch process workflow files and search automatically"""
        directory = self.workflow_dir.get().strip()
        if not directory:
            messagebox.showerror("Error", "Please select a workflow directory.")
            return
        
        if not os.path.isdir(directory):
            messagebox.showerror("Error", "Directory does not exist.")
            return
        
        # Check license status
        can_use, reason = license_manager.can_use_feature("batch_analysis", 5)


        if not can_use:
            if reason == "使用积分": # Use the specific reason code from licensing
                # Prompt user to use credits
                if messagebox.askyesno("Use Credits", "You have used up your free batch analyses for today. Use 5 credits to continue?"):
                    if license_manager.use_credits(5):
                        # Continue execution
                        pass
                    else:
                        messagebox.showerror("Error", "Insufficient credits.")
                        return
                else:
                    return
            else:
                reason_en = "Daily limit reached" if "每日使用上限" in reason else reason
                messagebox.showerror("Limited Feature", f"Cannot use this feature: {reason_en}")
                return

        # Record usage
        license_manager.record_usage("batch_analysis")

        # Get file pattern
        file_pattern = self.file_pattern.get().strip()
        if not file_pattern:
            file_pattern = "*.json"
        


        # Process file pattern, supporting multiple patterns
        patterns = file_pattern.split(';')
        all_workflow_files = []

        for pattern in patterns:
            pattern = pattern.strip()
            if pattern:
                # Use glob to find files matching the pattern
                try:
                    workflow_files_pattern = glob.glob(os.path.join(directory, pattern))
                    all_workflow_files.extend(workflow_files_pattern)
                except Exception as e:
                     print(f"Error processing pattern {pattern}: {e}")


        # Filter out only valid JSON files
        valid_workflow_files = []
        for file_path in all_workflow_files:
            # Try to read file and check if it's a JSON format
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                valid_workflow_files.append(file_path)
            except json.JSONDecodeError:
                print(f"Skipping non-JSON file: {file_path}")
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")

        if not valid_workflow_files:
            messagebox.showerror("Error", f"No valid JSON workflow files found in {directory} with the specified pattern.")
            return

        # Clear result tree
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        # Reset progress bar
        self.batch_progress_bar['value'] = 0
        self.batch_progress_label.config(text="0%")
        self.status_var.set("Processing workflow files...")
        
        # Execute batch processing in a separate thread to avoid freezing the interface
        def batch_thread():
            try:
                # Update progress bar callback function
                def update_progress(current, total):
                    if total > 0:
                        percentage = int((current / total) * 100)
                        self.root.after(0, lambda: self.batch_progress_bar.config(value=percentage))
                        self.root.after(0, lambda: self.batch_progress_label.config(text=f"{percentage}%"))
                
                # Use the filtered list of valid JSON files
                result = batch_process_workflows(directory, file_pattern, progress_callback=update_progress, specific_files=valid_workflow_files)

                # The result from batch_process_workflows is now expected to be a dictionary
                # or False if it failed early.
                if isinstance(result, tuple) and len(result) == 2 and result[0]:
                    success, result_data = result
                    if isinstance(result_data, dict):
                        # Extract data from result
                        summary_csv_path = result_data.get('summary_csv')
                        individual_results = result_data.get('results', [])

                        # Update Treeview with individual results
                        csv_files_for_search = []
                        for res in individual_results:
                            workflow_base = os.path.basename(res['workflow'])
                            csv_file_path = res.get('csv')
                            if csv_file_path and os.path.exists(csv_file_path):
                                csv_files_for_search.append(csv_file_path)
                                self.result_tree.insert("", "end", values=(
                                workflow_base,
                                res.get('missing_count', '0'),
                                "Processed"
                            ))

                        self.status_var.set("Batch processing completed, preparing to search links.")

                        # Search the summary CSV file
                        if summary_csv_path and os.path.exists(summary_csv_path):
                            self.status_var.set(f"Starting search in summary file: {summary_csv_path}")

                            def update_search_progress(current, total):
                                if total > 0:
                                    percentage = int((current / total) * 100)
                                    self.root.after(0, lambda: self.batch_progress_bar.config(value=percentage))
                                    self.root.after(0, lambda: self.batch_progress_label.config(text=f"{percentage}%"))
                            
                            # Reset progress bar for search phase
                            self.root.after(0, lambda: self.batch_progress_bar.config(value=0))
                            self.root.after(0, lambda: self.batch_progress_label.config(text="0%"))
                            
                            # Directly call search_model_links to search summary file
                            html_result = search_model_links(summary_csv_path, progress_callback=update_search_progress)

                            # If search fails, try to create HTML view from the summary CSV
                            if not html_result or not isinstance(html_result, str) or not os.path.exists(html_result):
                                try:
                                    from .utils import create_html_view
                                    html_result = create_html_view(summary_csv_path)
                                    print(f"Created HTML view using create_html_view for summary: {html_result}")
                                except Exception as e:
                                    print(f"Error creating HTML view for summary: {e}")

                            # Search completed, update status and open HTML
                            if html_result and isinstance(html_result, str) and os.path.exists(html_result):
                                self.status_var.set("Search completed, opening HTML result.")
                                print(f"Opening HTML result in 1 second: {html_result}")
                                # Open the summary HTML result
                                if self.auto_open_html.get():
                                    self.root.after(1000, lambda h=html_result: webbrowser.open(h))
                                self.root.after(0, lambda: messagebox.showinfo("Complete", "Batch processing and search completed."))
                            else:
                                self.status_var.set("Search completed, but no HTML result generated")
                                
                                # Update tree view status for all items
                                for item in self.result_tree.get_children():
                                    values = self.result_tree.item(item, 'values')
                                    self.result_tree.item(item, values=(values[0], values[1], "Search completed"))
                        else:
                            self.status_var.set(f"Summary CSV file not found: {summary_csv_path}")
                            self.root.after(0, lambda: messagebox.showwarning("Warning", "Summary Missing Files.csv not found, cannot perform search."))
                    else:
                        self.status_var.set("Batch processing completed, but result format is unexpected.")
                        self.root.after(0, lambda: messagebox.showinfo("Complete", "Batch processing completed, but result structure is not recognized."))
                else:
                    self.status_var.set("Batch processing completed, no missing files found or no valid workflows processed.")
                    self.root.after(0, lambda: messagebox.showinfo("Complete", "Batch processing completed. No missing files found in valid workflows."))
            
            except Exception as e:
                error_msg = str(e)
                import traceback
                traceback.print_exc() # Print full traceback for debugging
                self.status_var.set("Batch processing failed")
                self.root.after(0, lambda error=error_msg: messagebox.showerror("Error", f"Batch processing error: {error}"))
            
            finally:
                self.root.after(0, lambda: self.enable_buttons())
                self.root.after(0, lambda: self.refresh_license_info())
        
        threading.Thread(target=batch_thread, daemon=True).start()

    def view_batch_html(self):
        """View batch processing HTML result (tries summary first)"""
        directory = self.workflow_dir.get().strip()
        if not directory:
            messagebox.showerror("Error", "Please select a workflow directory first.")
            return
        
        # Try to open the summary HTML file first (assuming standard name)
        output_dir = create_output_directory() # Use the central results dir
        
        # 尝试不同的命名格式
        possible_html_paths = [
            os.path.join(output_dir, "Summary Missing Files.html"),
            os.path.join(output_dir, "Summary_Missing_Files.html")
        ]
        
        for summary_html_path in possible_html_paths:
            if os.path.exists(summary_html_path):
                try:
                    print(f"Opening summary HTML: {summary_html_path}")
                    webbrowser.open(summary_html_path)
                    return
                except Exception as e:
                    print(f"Error opening summary HTML: {e}")

        # Fallback: If summary HTML doesn't exist, try regenerating from summary CSV
        possible_csv_paths = [
            os.path.join(output_dir, "Summary Missing Files.csv"),
            os.path.join(output_dir, "Summary_Missing_Files.csv")
        ]
        
        for summary_csv_path in possible_csv_paths:
            if os.path.exists(summary_csv_path):
                try:
                    print(f"Regenerating HTML from summary CSV: {summary_csv_path}")
                    from .utils import create_html_view
                    html_file = create_html_view(summary_csv_path)
                    if html_file:
                        webbrowser.open(html_file)
                        return
                except Exception as e:
                    print(f"Error converting summary CSV to HTML: {e}")

        # If all else fails, show error
        messagebox.showerror("Error", "Could not find or generate the summary HTML result file.")

    def apply_theme(self):
        """Apply the selected theme"""
        theme = self.theme_var.get()
        if theme in self.themes:
            style = ttk.Style()
            style.theme_use(theme)
            self.current_theme = theme

    def check_dependencies(self):
        """Check dependencies"""
        from .utils import check_dependencies
        check_dependencies()
        messagebox.showinfo("Dependency Check", "Dependency check completed.")

    def save_settings(self):
        """Save settings"""
        try:
            # Collect current settings
            settings = {
                'auto_open_html': self.auto_open_html.get(),
                'chrome_path': self.chrome_path_var.get(),
                'random_theme': self.random_theme.get(),
                'theme': self.theme_var.get(),
                'retention_days': self.retention_days.get()
            }

            # Set file path
            settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

            # Save to JSON file
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)

            messagebox.showinfo("Settings", "Settings saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving settings: {str(e)}")

    def load_settings(self):
        """Load saved settings"""
        try:
            # Set file path
            settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

            # Check if file exists
            if not os.path.exists(settings_file):
                print("No settings file found, using default settings")
                return

            # Read settings
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)

            # Apply settings
            if 'auto_open_html' in settings:
                self.auto_open_html.set(settings['auto_open_html'])

            if 'chrome_path' in settings:
                self.chrome_path_var.set(settings['chrome_path'])

            if 'random_theme' in settings:
                self.random_theme.set(settings['random_theme'])

            if 'theme' in settings:
                self.theme_var.set(settings['theme'])

            if 'retention_days' in settings and settings['retention_days'] > 0:
                self.retention_days.set(settings['retention_days'])

            print("Settings loaded successfully")

        except Exception as e:
            print(f"Error loading settings: {e}")
            # Use default settings if error occurs, does not affect program execution

def main():
    """Main function, create and run the interface"""
    root = tk.Tk()

    # Set random theme
    try:
        import ttkbootstrap as ttk
        from ttkbootstrap import Style
        import random

        # Randomly select a theme
        themes = [
            "flatly", "darkly", "litera", "minty", "lumen", "sandstone",
            "yeti", "pulse", "united", "morph", "journal", "solar"
        ]

        random_theme = random.choice(themes)
        print(f"Using random theme: {random_theme}")

        # Apply theme
        try:
            style = Style(theme=random_theme)
            root = style.master
            print(f"Successfully applied random theme: {random_theme}")
        except tk.TclError as e:
             print(f"Warning: Failed to apply random theme '{random_theme}': {e}. Using default TK root.")
             # If random theme fails, just use the default root
             # The __init__ method will handle applying a fallback theme later
             pass
    except ImportError:
        # If ttkbootstrap is not available, use standard ttk
        import tkinter.ttk as ttk

    app = ModelFinderApp(root)

    # Set window icon
    try:
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception as e:
        print(f"Error setting icon: {e}")
        
    root.mainloop()

if __name__ == "__main__":
    main()
