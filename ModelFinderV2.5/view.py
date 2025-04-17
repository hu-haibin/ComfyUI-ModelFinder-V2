# model_finder/view.py
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import os
import logging # Import logging

logger = logging.getLogger(__name__) # Get logger for this module

class AppView:
    def __init__(self, root):
        self.root = root
        self.controller = None # Set later by set_controller

        self.notebook = None
        self.tab_single = None
        self.tab_batch = None
        self.tab_settings = None

        self.workflow_path_var = tk.StringVar()
        self.workflow_dir_var = tk.StringVar()
        self.file_pattern_var = tk.StringVar(value="*.json;*")
        self.chrome_path_var = tk.StringVar()
        self.theme_var = tk.StringVar()
        self.retention_days_var = tk.IntVar(value=30) # Keep default for initial display

        self.log_text = None
        self.progress_bar = None
        self.progress_label = None
        self.batch_progress_bar = None
        self.batch_progress_label = None
        self.result_tree = None
        self.view_result_button = None
        self.view_batch_html_button = None
        self.theme_dropdown = None
        self.status_label = None # Reference for status bar label
        # References for checkbuttons needed in _update_initial_settings
        self.auto_open_html_check = None
        self.auto_open_check = None # Checkbutton in batch tab
        self.random_theme_check = None

        self._set_icon()
        self._create_main_widgets()
        self._setup_tabs()
        logger.debug("AppView initialized.")

    def set_controller(self, controller):
        """Sets the controller reference and updates initial settings from controller."""
        logger.debug("Setting controller reference in View.")
        self.controller = controller
        if self.controller:
             self._update_initial_settings()
             # Link status bar label to controller's variable
             if self.status_label:
                 self.status_label.config(textvariable=self.controller.status_var)
             else:
                 logger.warning("Status label widget not found during set_controller.")

    def _set_icon(self):
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Modelfinder.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            else:
                 logger.warning(f"Icon file not found at {icon_path}")
        except Exception as e:
             logger.error("加载图标时出错", exc_info=True)

    def _create_main_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        # Status bar: Create label, textvariable linked in set_controller
        self.status_label = ttk.Label(self.root, text="...", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def _setup_tabs(self):
        self.tab_single = ttk.Frame(self.notebook)
        self.tab_batch = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_single, text="单个处理")
        self.notebook.add(self.tab_batch, text="批量处理")
        self.notebook.add(self.tab_settings, text="设置")
        self._setup_single_tab(self.tab_single)
        self._setup_batch_tab(self.tab_batch)
        self._setup_settings_tab(self.tab_settings)

    def _setup_single_tab(self, tab_frame):
        main_frame = ttk.Frame(tab_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        # ... (rest of layout code) ...
        ttk.Label(main_frame, text="工作流文件:").grid(row=1, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.workflow_path_var, width=50).grid(row=1, column=1, sticky="ew", padx=5)
        # Use lambda to safely call controller method only if controller exists
        ttk.Button(main_frame, text="浏览...", command=lambda: self.controller.browse_workflow() if self.controller else None).grid(row=1, column=2, padx=5)
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, sticky="w", pady=10)
        ttk.Button(button_frame, text="一键分析并搜索", style="success.TButton", command=lambda: self.controller.analyze_and_search() if self.controller else None).pack(side=tk.LEFT, padx=(0, 5))
        self.view_result_button = ttk.Button(button_frame, text="查看结果", command=lambda: self.controller.view_result() if self.controller else None, state=tk.DISABLED)
        self.view_result_button.pack(side=tk.LEFT)
        # ... (progress bar, log text setup) ...
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5)
        ttk.Label(progress_frame, text="进度:").pack(side=tk.LEFT, padx=(0, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.pack(side=tk.LEFT, padx=5)
        ttk.Separator(main_frame, orient="horizontal").grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)
        ttk.Label(main_frame, text="处理日志:").grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 5))
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=(0, 5))
        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)


    def _setup_batch_tab(self, tab_frame):
        main_frame = ttk.Frame(tab_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        # ... (layout code) ...
        ttk.Label(main_frame, text="工作流目录:").grid(row=1, column=0, sticky="w")
        ttk.Entry(main_frame, textvariable=self.workflow_dir_var, width=50).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Button(main_frame, text="浏览...", command=lambda: self.controller.browse_workflow_dir() if self.controller else None).grid(row=1, column=2, padx=5)
        ttk.Label(main_frame, text="文件格式:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.file_pattern_var, width=20).grid(row=2, column=1, sticky="w", padx=5, pady=5)
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=5)
        # Store reference to checkbutton to link its variable later
        self.auto_open_check = ttk.Checkbutton(options_frame, text="自动打开结果")
        self.auto_open_check.pack(side=tk.LEFT)
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=4, column=0, columnspan=3, sticky="w", pady=10)
        ttk.Button(buttons_frame, text="开始处理并搜索", style="success.TButton",
                   command=lambda: self.controller.batch_process() if self.controller else None).pack(side=tk.LEFT)
        # ... (progress bar, result tree setup) ...
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)
        ttk.Label(progress_frame, text="进度:").pack(side=tk.LEFT, padx=(0, 5))
        self.batch_progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.batch_progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.batch_progress_label = ttk.Label(progress_frame, text="0%")
        self.batch_progress_label.pack(side=tk.LEFT, padx=5)
        ttk.Label(main_frame, text="处理结果:").grid(row=6, column=0, columnspan=3, sticky="w", pady=(10, 5))
        result_frame = ttk.Frame(main_frame)
        result_frame.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=(0, 5))
        columns = ("文件名", "缺失数量", "状态")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=10)
        for col in columns: self.result_tree.heading(col, text=col); self.result_tree.column(col, width=150)
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_tree.config(yscrollcommand=scrollbar.set)
        self.view_batch_html_button = ttk.Button(main_frame, text="查看HTML", command=lambda: self.controller.view_batch_html() if self.controller else None)
        self.view_batch_html_button.grid(row=8, column=0, columnspan=3, sticky="w", pady=10)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(7, weight=1)


    def _setup_settings_tab(self, tab_frame):
        main_frame = ttk.Frame(tab_frame)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        # ... (app settings frame) ...
        app_frame = ttk.LabelFrame(main_frame, text="应用设置")
        app_frame.pack(fill="x", pady=5)
        auto_html_frame = ttk.Frame(app_frame)
        auto_html_frame.pack(fill="x", padx=5, pady=5)
        self.auto_open_html_check = ttk.Checkbutton(auto_html_frame, text="搜索完成后自动打开HTML结果")
        self.auto_open_html_check.pack(side="left", padx=5)
        chrome_frame = ttk.Frame(app_frame)
        chrome_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(chrome_frame, text="Chrome路径:").pack(side="left", padx=5)
        ttk.Entry(chrome_frame, textvariable=self.chrome_path_var, width=50).pack(side="left", fill="x", expand=True)
        ttk.Button(chrome_frame, text="浏览", command=lambda: self.controller.browse_chrome() if self.controller else None).pack(side="left", padx=5)
        # ... (theme frame) ...
        theme_frame = ttk.LabelFrame(main_frame, text="界面主题")
        theme_frame.pack(fill="x", pady=5)
        theme_select_frame = ttk.Frame(theme_frame)
        theme_select_frame.pack(fill="x", padx=5, pady=5)
        theme_names = [ "cosmo", "flatly", "litera", "minty", "lumen", "sandstone", "yeti", "pulse", "united", "morph", "journal", "darkly", "superhero", "solar", "cyborg" ]
        ttk.Label(theme_select_frame, text="选择主题:").pack(side="left", padx=5)
        self.theme_dropdown = ttk.Combobox(theme_select_frame, textvariable=self.theme_var, values=theme_names, state="readonly")
        self.theme_dropdown.pack(side="left", padx=5)
        ttk.Button(theme_select_frame, text="应用主题", command=lambda: self.controller.apply_theme() if self.controller else None).pack(side="left", padx=5)
        random_theme_frame = ttk.Frame(theme_frame)
        random_theme_frame.pack(fill="x", padx=5, pady=5)
        self.random_theme_check = ttk.Checkbutton(random_theme_frame, text="启动时使用随机主题")
        self.random_theme_check.pack(side="left", padx=5)
        # ... (file management frame) ...
        file_frame = ttk.LabelFrame(main_frame, text="文件管理")
        file_frame.pack(fill="x", pady=5)
        ttk.Label(file_frame, text="所有结果文件保存在results文件夹中，按日期组织").pack(anchor="w", padx=5, pady=2)
        retention_frame = ttk.Frame(file_frame)
        retention_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(retention_frame, text="保留文件天数:").pack(side="left", padx=5)
        ttk.Spinbox(retention_frame, from_=1, to=365, width=5, textvariable=self.retention_days_var).pack(side="left")
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(btn_frame, text="清理旧文件", command=lambda: self.controller.cleanup_old_files() if self.controller else None).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="打开结果文件夹", command=lambda: self.controller.open_results_folder() if self.controller else None).pack(side="left", padx=5)
        save_frame = ttk.Frame(main_frame)
        save_frame.pack(fill="x", pady=10)
        ttk.Button(save_frame, text="保存设置", command=lambda: self.controller.save_settings() if self.controller else None).pack(side="right", padx=5)


    def _update_initial_settings(self):
        """Update widgets based on controller state after controller is set."""
        logger.debug("View updating initial settings from controller.")
        if self.controller:
            # Link checkbuttons to controller variables now that controller exists
            if self.auto_open_html_check: self.auto_open_html_check.config(variable=self.controller.auto_open_html)
            if self.auto_open_check: self.auto_open_check.config(variable=self.controller.auto_open_html) # Link batch tab checkbutton too
            if self.random_theme_check: self.random_theme_check.config(variable=self.controller.random_theme)

            # Get initial values from controller getters
            theme = self.controller.get_loaded_theme_preference()
            chrome = self.controller.get_loaded_chrome_path()
            days = self.controller.get_loaded_retention_days()
            logger.debug(f"Applying initial settings to view: Theme={theme}, Chrome='{chrome}', Days={days}")

            # Apply values to view widgets
            if theme and self.theme_dropdown: self.set_selected_theme(theme)
            self.set_chrome_path(chrome)
            self.set_retention_days(days)
        else:
             logger.warning("Controller not set in view during _update_initial_settings.")

    # --- Getters for Controller ---
    def get_workflow_path(self): return self.workflow_path_var.get().strip()
    def get_workflow_dir(self): return self.workflow_dir_var.get().strip()
    def get_file_pattern(self): return self.file_pattern_var.get().strip()
    def get_chrome_path(self): return self.chrome_path_var.get().strip()
    def get_selected_theme(self): return self.theme_var.get()
    def get_retention_days(self):
        try: return self.retention_days_var.get()
        except tk.TclError: return 30 # Default if var is bad

    # --- Setters for Controller ---
    def set_workflow_path(self, path): self.workflow_path_var.set(path)
    def set_workflow_dir(self, path): self.workflow_dir_var.set(path)
    def set_chrome_path(self, path): self.chrome_path_var.set(path)
    def set_selected_theme(self, theme_name):
        logger.debug(f"View setting theme dropdown/var to: {theme_name}")
        self.theme_var.set(theme_name)
        if self.theme_dropdown: self.theme_dropdown.set(theme_name) # Ensure combobox shows it
    def set_retention_days(self, days):
        logger.debug(f"View setting retention days var to: {days}")
        self.retention_days_var.set(days)
    def set_window_title(self, title): self.root.title(title)

    # --- UI Update Methods ---
    # (Keep existing methods: update_log, clear_log, set_progress, etc.)
    # ... (previous methods remain here) ...
    def update_log(self, message):
        if self.log_text: self.log_text.insert(tk.END, message + "\n"); self.log_text.see(tk.END)
    def clear_log(self):
        if self.log_text: self.log_text.delete(1.0, tk.END)
    def set_progress(self, value, text):
        if self.progress_bar: self.progress_bar['value'] = value
        if self.progress_label: self.progress_label.config(text=text)
        if self.root.winfo_exists(): self.root.update_idletasks() # Add check
    def set_batch_progress(self, value, text):
        if self.batch_progress_bar: self.batch_progress_bar['value'] = value
        if self.batch_progress_label: self.batch_progress_label.config(text=text)
        if self.root.winfo_exists(): self.root.update_idletasks() # Add check
    def enable_view_result_button(self, enabled=True):
        if self.view_result_button: self.view_result_button.config(state=tk.NORMAL if enabled else tk.DISABLED)
    def clear_batch_results(self):
        if self.result_tree:
            for item in self.result_tree.get_children(): self.result_tree.delete(item)
    def add_batch_result(self, file_name, missing_count, status):
        if self.result_tree: self.result_tree.insert("", "end", values=(file_name, missing_count, status))
    def update_batch_result_status(self, file_name, new_status):
         if self.result_tree:
             for item in self.result_tree.get_children():
                 values = self.result_tree.item(item, 'values')
                 if len(values) > 0 and values[0] == file_name:
                     self.result_tree.item(item, values=(values[0], values[1], new_status)); break
    # --- User Feedback Methods ---
    def show_info(self, title, message): logger.info(f"Showing info dialog: {title} - {message}"); messagebox.showinfo(title, message)
    def show_error(self, title, message): logger.error(f"Showing error dialog: {title} - {message}"); messagebox.showerror(title, message)
    def show_warning(self, title, message): logger.warning(f"Showing warning dialog: {title} - {message}"); messagebox.showwarning(title, message)
    def ask_yes_no(self, title, message): logger.info(f"Showing yes/no dialog: {title} - {message}"); return messagebox.askyesno(title, message)