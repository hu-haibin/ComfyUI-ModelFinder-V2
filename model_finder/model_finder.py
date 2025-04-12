#!/usr/bin/env python
"""
===== ComfyUI模型查找器 2.0 (Model Finder) =====
功能：检测缺失模型并生成下载链接的工具
特点：
- 界面美观，操作直观
- 单个工作流处理
- 批量工作流一键处理与搜索
- 自动搜索生成下载链接
- HTML结果视图
- 随机主题风格
版本：2.0.1
日期：2024-04-15
联系方式：WeChat wangdefa4567
"""

import os
import sys
import json
import random
import threading
import webbrowser
import traceback
from .utils import check_dependencies
from . import __version__, __author__
# 执行依赖检查
check_dependencies()

# 导入依赖
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import glob

# 导入核心功能
from .core import (
    find_missing_models, 
    create_csv_file, 
    search_model_links,
    batch_process_workflows
)

class ModelFinderApp:
    def __init__(self, root):
        try:
            # 基本窗口设置
            self.root = root
            self.root.title(f"ComfyUI模型查找器 - Model Finder v{__version__} (WeChat: {__author__})")
            self.root.geometry("700x600")
            
            # 先初始化重要的变量以确保它们始终存在
            # 存储HTML文件路径
            self.html_file_path = None
            
            # 明确为root指定这些变量，避免绑定错误
            self.auto_open_html = tk.BooleanVar(root, value=True)
            self.use_bing_search = tk.BooleanVar(root, value=True)
            
            print("变量初始化成功")
            
            # 设置ttkbootstrap主题
            style = ttk.Style()
            self.themes = style.theme_names()
            self.current_theme = "cosmo"  # 默认主题
            style.theme_use(self.current_theme)
            
            # 创建选项卡
            self.notebook = ttk.Notebook(root)
            self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 创建三个选项卡
            self.tab_single = ttk.Frame(self.notebook)
            self.tab_batch = ttk.Frame(self.notebook)
            self.tab_settings = ttk.Frame(self.notebook)
            
            self.notebook.add(self.tab_single, text="单个处理")
            self.notebook.add(self.tab_batch, text="批量处理")
            self.notebook.add(self.tab_settings, text="设置")
            
            # 状态栏
            self.status_var = tk.StringVar(value="就绪")
            status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
            status_bar.pack(side=tk.BOTTOM, fill=tk.X)
            
            # 设置各选项卡的内容
            self.setup_single_tab()
            self.setup_batch_tab()
            self.setup_settings_tab()
            
        except Exception as e:
            print(f"初始化GUI时出错: {e}")
            if not hasattr(self, 'auto_open_html'):
                print("修复auto_open_html变量...")
                self.auto_open_html = tk.BooleanVar(root, value=True)
            if not hasattr(self, 'use_bing_search'):
                print("修复use_bing_search变量...")
                self.use_bing_search = tk.BooleanVar(root, value=True)
            
            # 显示错误消息
            import traceback
            traceback.print_exc()
            
            try:
                tk.messagebox.showerror("初始化错误", f"初始化过程出错: {str(e)}\n已尝试修复，请重启应用如果问题持续出现")
            except:
                print("无法显示错误消息窗口")
    
    def setup_single_tab(self):
        """设置单个处理选项卡"""
        # 创建主框架
        main_frame = ttk.Frame(self.tab_single, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 工作流处理标题
        ttk.Label(main_frame, text="工作流处理", font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        
        # 工作流文件选择
        ttk.Label(main_frame, text="工作流文件:").grid(row=1, column=0, sticky="w")
        self.workflow_path = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.workflow_path, width=50).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Button(main_frame, text="浏览...", command=self.browse_workflow).grid(row=1, column=2, padx=5)
        
        # 按钮区
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, sticky="w", pady=10)
        ttk.Button(button_frame, text="一键分析并搜索", style="success.TButton", command=self.analyze_and_search).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="查看结果", command=self.view_result, state=tk.DISABLED).pack(side=tk.LEFT)
        
        # 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5)
        ttk.Label(progress_frame, text="进度:").pack(side=tk.LEFT, padx=(0, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(main_frame, orient="horizontal").grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)
        
        # 日志区域
        ttk.Label(main_frame, text="处理日志:").grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 5))
        
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=(0, 5))
        
        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # 使主框架的列可伸缩
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        # 初始化日志
        self.show_welcome_message()
    
    def setup_batch_tab(self):
        """设置批量处理选项卡"""
        # 创建主框架
        main_frame = ttk.Frame(self.tab_batch, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 批量工作流处理标题
        ttk.Label(main_frame, text="批量工作流一键处理与搜索", font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        
        # 工作流目录选择
        ttk.Label(main_frame, text="工作流目录:").grid(row=1, column=0, sticky="w")
        self.workflow_dir = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.workflow_dir, width=50).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Button(main_frame, text="浏览...", command=self.browse_workflow_dir).grid(row=1, column=2, padx=5)
        
        # 文件格式选择
        ttk.Label(main_frame, text="文件格式:").grid(row=2, column=0, sticky="w", pady=5)
        self.file_pattern = tk.StringVar(value="*.json;*")
        ttk.Entry(main_frame, textvariable=self.file_pattern, width=20).grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        # 选项
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=5)
        ttk.Checkbutton(options_frame, text="创建合并CSV文件", variable=tk.BooleanVar(value=True), state=tk.DISABLED).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(options_frame, text="自动打开结果", variable=self.auto_open_html).pack(side=tk.LEFT)
        
        # 按钮 - 只保留"一键处理并搜索"按钮
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=4, column=0, columnspan=3, sticky="w", pady=10)
        ttk.Button(buttons_frame, text="开始处理并搜索", style="success.TButton", 
                command=self.batch_process).pack(side=tk.LEFT)
        
        # 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)
        ttk.Label(progress_frame, text="进度:").pack(side=tk.LEFT, padx=(0, 5))
        self.batch_progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.batch_progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.batch_progress_label = ttk.Label(progress_frame, text="0%")
        self.batch_progress_label.pack(side=tk.LEFT, padx=5)
        
        # 处理结果区域
        ttk.Label(main_frame, text="处理结果:").grid(row=6, column=0, columnspan=3, sticky="w", pady=(10, 5))
        
        result_frame = ttk.Frame(main_frame)
        result_frame.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=(0, 5))
        
        # 使用Treeview显示结果
        columns = ("文件名", "缺失数量", "状态")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=10)
        
        # 设置列标题
        for col in columns:
            self.result_tree.heading(col, text=col)
            self.result_tree.column(col, width=100)
        
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_tree.config(yscrollcommand=scrollbar.set)
        
        # 查看HTML按钮
        ttk.Button(main_frame, text="查看HTML", command=self.view_batch_html).grid(row=8, column=0, columnspan=3, sticky="w", pady=10)
        
        # 使主框架的列可伸缩
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(7, weight=1)

    def setup_settings_tab(self):
        """设置选项卡设置"""
        # 创建主框架，带滚动条
        main_frame = ttk.Frame(self.tab_settings)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 应用设置部分
        app_frame = ttk.LabelFrame(main_frame, text="应用设置")
        app_frame.pack(fill="x", pady=5)
        
        # 自动打开HTML结果开关
        auto_html_frame = ttk.Frame(app_frame)
        auto_html_frame.pack(fill="x", padx=5, pady=5)
        
        self.auto_open_html = tk.BooleanVar(value=True)
        ttk.Checkbutton(auto_html_frame, text="搜索完成后自动打开HTML结果", 
                    variable=self.auto_open_html).pack(side="left", padx=5)
        
        # Chrome浏览器路径设置
        chrome_frame = ttk.Frame(app_frame)
        chrome_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(chrome_frame, text="Chrome路径:").pack(side="left", padx=5)
        self.chrome_path_var = tk.StringVar()
        ttk.Entry(chrome_frame, textvariable=self.chrome_path_var, width=50).pack(side="left", fill="x", expand=True)
        ttk.Button(chrome_frame, text="浏览", command=self.browse_chrome).pack(side="left", padx=5)
        
        # 添加主题选择部分
        theme_frame = ttk.LabelFrame(main_frame, text="界面主题")
        theme_frame.pack(fill="x", pady=5)
        
        # 主题选择下拉框
        theme_select_frame = ttk.Frame(theme_frame)
        theme_select_frame.pack(fill="x", padx=5, pady=5)
        
        self.theme_names = [
            "flatly", "darkly", "litera", "minty", "lumen", "sandstone", 
            "yeti", "pulse", "united", "morph", "journal", "solar"
        ]
        
        self.theme_var = tk.StringVar()  # 修改为 theme_var
        
        ttk.Label(theme_select_frame, text="选择主题:").pack(side="left", padx=5)
        theme_dropdown = ttk.Combobox(theme_select_frame, textvariable=self.theme_var, 
                                    values=self.theme_names, state="readonly")
        theme_dropdown.pack(side="left", padx=5)
        theme_dropdown.current(0)
        
        ttk.Button(theme_select_frame, text="应用主题", 
                command=self.apply_theme).pack(side="left", padx=5)
        
        # 添加随机主题选项
        random_theme_frame = ttk.Frame(theme_frame)
        random_theme_frame.pack(fill="x", padx=5, pady=5)
        
        self.random_theme = tk.BooleanVar(value=True)
        ttk.Checkbutton(random_theme_frame, text="启动时使用随机主题", 
                    variable=self.random_theme).pack(side="left", padx=5)
        
        # 添加文件管理部分
        file_frame = ttk.LabelFrame(main_frame, text="文件管理")
        file_frame.pack(fill="x", pady=5)
        
        # 添加文件管理说明
        ttk.Label(file_frame, text="所有结果文件保存在results文件夹中，按日期组织").pack(anchor="w", padx=5, pady=2)
        
        # 保留天数设置
        retention_frame = ttk.Frame(file_frame)
        retention_frame.pack(fill="x", padx=5, pady=5)
        
        self.retention_days = tk.IntVar(value=30)
        ttk.Label(retention_frame, text="保留文件天数:").pack(side="left", padx=5)
        ttk.Spinbox(retention_frame, from_=1, to=365, width=5, 
                    textvariable=self.retention_days).pack(side="left")
        
        # 添加按钮框架
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        # 添加清理按钮
        cleanup_btn = ttk.Button(btn_frame, text="清理旧文件", command=self.cleanup_old_files)
        cleanup_btn.pack(side="left", padx=5)
        
        # 添加查看结果文件夹按钮
        open_folder_btn = ttk.Button(btn_frame, text="打开结果文件夹", command=self.open_results_folder)
        open_folder_btn.pack(side="left", padx=5)
        
        # 保存设置按钮
        save_frame = ttk.Frame(main_frame)
        save_frame.pack(fill="x", pady=10)
        
        ttk.Button(save_frame, text="保存设置", 
                command=self.save_settings).pack(side="right", padx=5)
        
        # 加载保存的设置
        self.load_settings()

    def show_welcome_message(self):
        """显示欢迎消息"""
        welcome_text = "欢迎使用模型查找器 2.0\n\n" \
                      "使用方法:\n" \
                      "1. 选择工作流JSON文件并分析\n" \
                      "2. 等待自动搜索下载链接\n" \
                      "3. 查看HTML结果获取下载链接\n"
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, welcome_text)
    
    def update_log(self, message):
        """更新日志显示"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def browse_workflow(self):
        """浏览工作流文件"""
        file_path = filedialog.askopenfilename(
            title="选择工作流JSON文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if file_path:
            self.workflow_path.set(file_path)
    
    def browse_workflow_dir(self):
        """浏览工作流目录"""
        dir_path = filedialog.askdirectory(
            title="选择工作流目录"
        )
        if dir_path:
            self.workflow_dir.set(dir_path)
    def browse_chrome(self):
        """浏览并选择Chrome浏览器路径"""
        chrome_path = filedialog.askopenfilename(
            title="选择Chrome浏览器",
            filetypes=[("可执行文件", "*.exe")],
            initialdir="C:/Program Files/Google/Chrome/Application"
        )
        if chrome_path:
            self.chrome_path_var.set(chrome_path)

    def analyze_and_search(self):
        """分析工作流并搜索链接"""
        workflow_file = self.workflow_path.get().strip()
        if not workflow_file:
            messagebox.showerror("错误", "请选择工作流JSON文件")
            return
        
        if not os.path.exists(workflow_file):
            messagebox.showerror("错误", "文件不存在")
            return
        
        # 清空日志
        self.log_text.delete(1.0, tk.END)
        self.status_var.set("正在分析...")
        
        # 重定向stdout到Text控件
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
            # 分析工作流
            missing_files = find_missing_models(workflow_file)
            
            if missing_files:
                # 创建CSV文件
                output_file = os.path.basename(workflow_file)
                csv_file = create_csv_file(missing_files, output_file)
                
                if csv_file:
                    # 进行搜索
                    self.search_links(csv_file)
                else:
                    messagebox.showinfo("完成", "创建CSV文件失败")
                    self.status_var.set("分析完成，但创建CSV失败")
            else:
                messagebox.showinfo("完成", "没有发现缺失文件")
                self.status_var.set("分析完成: 没有缺失文件")
        
        except Exception as e:
            messagebox.showerror("错误", f"分析过程中出错: {str(e)}")
            self.status_var.set("分析失败")
        
        finally:
            # 恢复stdout
            sys.stdout = old_stdout
    
    def search_links(self, csv_file):
        """搜索模型下载链接"""
        if not os.path.exists(csv_file):
            messagebox.showerror("错误", "CSV文件不存在")
            return
        
        # 重置进度条
        self.progress_bar['value'] = 0
        self.progress_label.config(text="0%")
        
        # 禁用按钮
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.config(state=tk.DISABLED)
        
        # 在单独的线程中执行搜索，避免界面冻结
        def search_thread():
            # 更新进度条的回调函数
            def update_progress(current, total):
                if total > 0:
                    percentage = int((current / total) * 100)
                    self.root.after(0, lambda: self.progress_bar.config(value=percentage))
                    self.root.after(0, lambda: self.progress_label.config(text=f"{percentage}%"))
            
            try:
                result = search_model_links(csv_file, progress_callback=update_progress)
                
                if isinstance(result, str) and os.path.exists(result):
                    self.html_file_path = result
                    self.status_var.set("搜索完成")
                    
                    # 确保进度条显示100%
                    self.root.after(0, lambda: self.progress_bar.config(value=100))
                    self.root.after(0, lambda: self.progress_label.config(text="100%"))
                    
                    # 启用查看HTML结果按钮
                    for widget in self.tab_single.winfo_children():
                        if isinstance(widget, ttk.Frame):
                            for child in widget.winfo_children():
                                if isinstance(child, ttk.Frame):
                                    for btn in child.winfo_children():
                                        if isinstance(btn, ttk.Button) and btn['text'] == "查看结果":
                                            self.root.after(0, lambda: btn.config(state=tk.NORMAL))
                    
                    # 如果设置了自动打开，则打开HTML结果
                    if self.auto_open_html.get():
                        self.root.after(0, lambda: webbrowser.open(result))
                    
                    self.root.after(0, lambda: messagebox.showinfo("完成", "搜索完成，可以查看HTML结果"))
                else:
                    self.status_var.set("搜索完成，但没有生成HTML结果")
                    self.root.after(0, lambda: messagebox.showinfo("完成", "搜索完成"))
            
            except Exception as e:
                error_msg = str(e)  # 立即捕获错误信息
                self.status_var.set("搜索失败")
                self.root.after(0, lambda error=error_msg: messagebox.showerror("错误", f"搜索过程中出错: {error}"))
           
            
            finally:
                # 启用按钮
                self.root.after(0, lambda: self.enable_buttons())
        
        threading.Thread(target=search_thread, daemon=True).start()
    
    def enable_buttons(self):
        """启用所有按钮"""
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Notebook):
                for tab in [self.tab_single, self.tab_batch, self.tab_settings]:
                    for child in tab.winfo_children():
                        if isinstance(child, ttk.Frame):
                            for grandchild in child.winfo_children():
                                if isinstance(grandchild, ttk.Button):
                                    grandchild.config(state=tk.NORMAL)
                                if isinstance(grandchild, ttk.Frame):
                                    for btn in grandchild.winfo_children():
                                        if isinstance(btn, ttk.Button):
                                            btn.config(state=tk.NORMAL)
    
    def view_result(self):
        """查看HTML结果"""
        if self.html_file_path and os.path.exists(self.html_file_path):
            webbrowser.open(self.html_file_path)
        else:
            # 尝试根据工作流文件名推断HTML文件名
            workflow_file = self.workflow_path.get().strip()
            if workflow_file:
                basename = os.path.splitext(os.path.basename(workflow_file))[0]
                html_file = f"{basename}.html"
                if os.path.exists(html_file):
                    webbrowser.open(html_file)
                    return
            
            messagebox.showerror("错误", "HTML结果文件不存在")
   

    def batch_process(self):
        """批量处理工作流文件并自动搜索"""
        directory = self.workflow_dir.get().strip()
        if not directory:
            messagebox.showerror("错误", "请选择工作流目录")
            return
        
        if not os.path.isdir(directory):
            messagebox.showerror("错误", "目录不存在")
            return
        
        file_pattern = self.file_pattern.get().strip()
        if not file_pattern:
            file_pattern = "*.json;*"  # 修改为同时匹配有后缀和无后缀的文件
        
        # 处理文件模式，支持多个模式
        patterns = file_pattern.split(';')
        all_workflow_files = []
        
        for pattern in patterns:
            pattern = pattern.strip()
            if pattern:
                # 使用glob查找匹配该模式的文件
                workflow_files = glob.glob(os.path.join(directory, pattern))
                all_workflow_files.extend(workflow_files)
        
        # 过滤出只有JSON格式的文件
        workflow_files = []
        for file_path in all_workflow_files:
            # 尝试读取文件并检查是否为JSON格式
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                workflow_files.append(file_path)
            except json.JSONDecodeError:
                print(f"跳过非JSON文件: {file_path}")
            except Exception as e:
                print(f"读取文件 {file_path} 时出错: {e}")
        
        if not workflow_files:
            messagebox.showerror("错误", f"在 {directory} 中没有找到匹配的工作流文件")
            return
        
        # 清空结果树
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        # 重置进度条
        self.batch_progress_bar['value'] = 0
        self.batch_progress_label.config(text="0%")
        self.status_var.set("正在处理工作流...")
        
        # 在单独的线程中执行批处理，避免界面冻结
        def batch_thread():
            try:
                # 更新进度条的回调函数
                def update_progress(current, total):
                    if total > 0:
                        percentage = int((current / total) * 100)
                        self.root.after(0, lambda: self.batch_progress_bar.config(value=percentage))
                        self.root.after(0, lambda: self.batch_progress_label.config(text=f"{percentage}%"))
                
                result = batch_process_workflows(directory, file_pattern, progress_callback=update_progress)
                
                if isinstance(result, str) and os.path.exists(result):
                    # 读取结果文件并显示在Treeview中
                    import csv
                    csv_files = []
                    with open(result, 'r', encoding='utf-8-sig') as f:
                        reader = csv.DictReader(f)
                        for i, row in enumerate(reader):
                            csv_file = row.get('CSV文件', '')
                            missing_count = row.get('缺失数量', '0')
                            full_path = os.path.join(directory, csv_file)
                            
                            # 保存CSV文件路径用于后续搜索
                            if os.path.exists(full_path):
                                csv_files.append(full_path)
                            
                            self.result_tree.insert("", "end", values=(
                                csv_file,
                                missing_count,
                                "已处理"
                            ))
                    
                    self.status_var.set("批量处理完成，准备搜索链接")
                    
                    # 直接搜索汇总文件而不是单个CSV文件
                    summary_file = os.path.join(directory, "汇总缺失文件.csv")
                    if os.path.exists(summary_file):
                        self.status_var.set("开始搜索汇总文件中的模型")
                        # 搜索汇总CSV文件中的所有模型
                        def update_search_progress(current, total):
                            if total > 0:
                                percentage = int((current / total) * 100)
                                self.root.after(0, lambda: self.batch_progress_bar.config(value=percentage))
                                self.root.after(0, lambda: self.batch_progress_label.config(text=f"{percentage}%"))
                        
                        # 重置进度条
                        self.root.after(0, lambda: self.batch_progress_bar.config(value=0))
                        self.root.after(0, lambda: self.batch_progress_label.config(text="0%"))
                        
                        # 直接调用search_model_links搜索汇总文件
                        html_result = search_model_links(summary_file, progress_callback=update_search_progress)
                        
                        # 搜索完成后更新状态并打开HTML
                        if html_result:
                            if isinstance(html_result, str) and os.path.exists(html_result):
                                self.status_var.set("搜索完成，打开HTML结果")
                                self.root.after(1000, lambda: webbrowser.open(html_result))
                                self.root.after(0, lambda: messagebox.showinfo("完成", "批量处理和搜索完成"))
                            else:
                                self.status_var.set("搜索完成，但没有生成HTML结果")
                                
                            # 更新树视图中所有项目的状态为"搜索完成"
                            for item in self.result_tree.get_children():
                                values = self.result_tree.item(item, 'values')
                                self.result_tree.item(item, values=(values[0], values[1], "搜索完成"))
                        else:
                            self.status_var.set("搜索失败")
                            self.root.after(0, lambda: messagebox.showerror("错误", "搜索过程中出错"))
                    else:
                        self.status_var.set("未找到汇总缺失文件，无法搜索")
                        self.root.after(0, lambda: messagebox.showwarning("警告", "未找到汇总缺失文件，无法搜索"))
                else:
                    self.status_var.set("批量处理完成，但未生成结果文件")
                    self.root.after(0, lambda: messagebox.showinfo("完成", "批量处理完成，未发现缺失文件"))
            
            except Exception as e:
                error_msg = str(e)  # 立即捕获错误信息
                self.status_var.set("批量处理失败")
                self.root.after(0, lambda error=error_msg: messagebox.showerror("错误", f"批量处理过程中出错: {error}"))
            
            finally:
                self.root.after(0, lambda: self.enable_buttons())
        
        threading.Thread(target=batch_thread, daemon=True).start()

    def view_batch_html(self):
        """查看批量处理HTML结果"""
        directory = self.workflow_dir.get().strip()
        if not directory:
            messagebox.showerror("错误", "请先选择工作流目录")
            return
        
        # 首先查找汇总缺失文件.csv并重新生成HTML
        summary_file = os.path.join(directory, "汇总缺失文件.csv")
        if os.path.exists(summary_file):
            try:
                print(f"重新生成汇总文件HTML: {summary_file}")
                from .utils import create_html_view
                html_file = create_html_view(summary_file)
                if html_file:
                    webbrowser.open(html_file)
                    return
            except Exception as e:
                print(f"转换汇总HTML出错: {e}")
        
        # 如果没有找到汇总文件，查找批量处理结果并重新生成HTML
        batch_summary = os.path.join(directory, "批量处理结果.csv")
        if os.path.exists(batch_summary):
            try:
                print(f"重新生成批量处理结果HTML: {batch_summary}")
                from .utils import create_html_view
                html_file = create_html_view(batch_summary)
                if html_file:
                    webbrowser.open(html_file)
                    return
            except Exception as e:
                print(f"转换批量结果HTML出错: {e}")
        
        # 如果以上都失败，显示错误
        messagebox.showerror("错误", "未找到CSV结果文件，无法生成HTML视图")

    def ask_batch_search(self, csv_files):
        """询问是否要进行批量搜索"""
        if messagebox.askyesno("批量搜索", f"发现 {len(csv_files)} 个CSV文件，是否要进行批量搜索下载链接？"):
            self.batch_search(csv_files)

    def batch_search(self, csv_files, open_html_after=False):
        """
        批量搜索所有CSV文件的下载链接
        注意：此方法已被弃用，但保留以供向后兼容
        当前的主工作流直接使用summary CSV文件
        """
        if not csv_files:
            return
        
        # 重置进度条
        self.batch_progress_bar['value'] = 0
        self.batch_progress_label.config(text="0%")
        self.status_var.set("准备批量搜索...")
        
        # 禁用按钮
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.config(state=tk.DISABLED)
        
        # 在单独的线程中执行搜索，避免界面冻结
        def search_thread():
            total_files = len(csv_files)
            success_count = 0
            total_models = 0
            processed_models = 0
            
            # 首先统计所有模型数量
            for csv_file in csv_files:
                try:
                    import pandas as pd
                    df = pd.read_csv(csv_file, encoding='utf-8-sig')
                    if '文件名' in df.columns:
                        # 过滤掉已处理的模型 - 只有当状态为'已处理'且有下载链接时才跳过
                        not_processed = df[~((df['状态'] == '已处理') & (~pd.isna(df['下载链接'])) & (df['下载链接'].str.strip() != ''))]
                        total_models += len(not_processed)
                except Exception as e:
                    print(f"读取CSV文件出错: {e}")
            
            print(f"总计需要搜索的模型数量: {total_models}")
            
            for i, csv_file in enumerate(csv_files):
                try:
                    # 更新状态
                    file_name = os.path.basename(csv_file)
                    self.status_var.set(f"搜索文件 ({i+1}/{total_files}): {file_name}")
                    
                    # 搜索单个文件的回调 - 更新进度
                    def update_sub_progress(current, total):
                        if total > 0:
                            # 更新总体进度
                            nonlocal processed_models
                            processed_models += 1
                            if total_models > 0:
                                overall_progress = int((processed_models / total_models) * 100)
                                if overall_progress > 100:  # 防止超过100%
                                    overall_progress = 100
                                self.root.after(0, lambda: self.batch_progress_bar.config(value=overall_progress))
                                self.root.after(0, lambda: self.batch_progress_label.config(text=f"{overall_progress}%"))
                    
                    # 执行搜索
                    result = search_model_links(csv_file, progress_callback=update_sub_progress)
                    
                    if result:
                        success_count += 1
                        # 更新树视图状态
                        for item in self.result_tree.get_children():
                            values = self.result_tree.item(item, 'values')
                            if len(values) > 0 and os.path.basename(csv_file) == values[0]:
                                self.result_tree.item(item, values=(
                                    values[0],
                                    values[1],
                                    "搜索完成"
                                ))
                except Exception as e:
                    print(f"搜索文件 {csv_file} 出错: {e}")
            
            # 完成批量搜索
            self.status_var.set(f"批量搜索完成，成功处理: {success_count}/{total_files} 文件")
            self.root.after(0, lambda: self.batch_progress_bar.config(value=100))
            self.root.after(0, lambda: self.batch_progress_label.config(text="100%"))
            
            # 在搜索完成后，总是重新生成汇总文件的HTML
            summary_file = os.path.join(os.path.dirname(csv_files[0]), "汇总缺失文件.csv")
            html_file = None
            if os.path.exists(summary_file):
                from .utils import create_html_view
                html_file = create_html_view(summary_file)
            
            # 如果设置了自动打开或者是一键处理并搜索流程，打开HTML结果
            if (self.auto_open_html.get() or open_html_after) and html_file:
                self.root.after(1000, lambda h=html_file: webbrowser.open(h))
                
            # 显示搜索完成消息
            if open_html_after:
                self.root.after(0, lambda: messagebox.showinfo("完成", "模型搜索完成"))
        
            self.root.after(0, lambda: self.enable_buttons())
        
        threading.Thread(target=search_thread, daemon=True).start()

    def apply_theme(self):
        """应用选择的主题"""
        theme = self.theme_var.get()
        if theme in self.themes:
            style = ttk.Style()
            style.theme_use(theme)
            self.current_theme = theme
    
    def check_dependencies(self):
        """检查依赖"""
        from .utils import check_dependencies
        check_dependencies()
        messagebox.showinfo("依赖检查", "依赖检查完成")
    
    def save_settings(self):
        """保存设置"""
        # 在这里保存设置到配置文件
        messagebox.showinfo("设置", "设置已保存")

    def load_settings(self):
        """加载保存的设置"""
        try:
            # 设置文件路径
            settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
            
            # 检查文件是否存在
            if not os.path.exists(settings_file):
                print("未找到设置文件，使用默认设置")
                return
            
            # 读取设置
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # 应用设置
            if 'auto_open_html' in settings:
                self.auto_open_html.set(settings['auto_open_html'])
            
            if 'chrome_path' in settings:
                self.chrome_path_var.set(settings['chrome_path'])
            
            if 'random_theme' in settings:
                self.random_theme.set(settings['random_theme'])
            
            if 'theme' in settings:
                self.theme_var.set(settings['theme'])  # 修改为 theme_var
            
            if 'retention_days' in settings and settings['retention_days'] > 0:
                self.retention_days.set(settings['retention_days'])
                
            print("设置加载成功")
        
        except Exception as e:
            print(f"加载设置出错: {e}")
            # 出错时使用默认设置，不影响程序运行
    def save_settings(self):
        """保存当前设置"""
        try:
            # 收集当前设置
            settings = {
                'auto_open_html': self.auto_open_html.get(),
                'chrome_path': self.chrome_path_var.get(),
                'random_theme': self.random_theme.get(),
                'theme': self.theme_var.get(),  # 修改为 theme_var
                'retention_days': self.retention_days.get()
            }
            
            # 设置文件路径
            settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
            
            # 保存设置
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("成功", "设置已保存")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存设置时出错: {e}")
            print(f"保存设置出错: {e}")

    def cleanup_old_files(self):
        """手动清理旧文件"""
        try:
            from .file_manager import cleanup_old_results
            
            # 获取用户设置的保留天数
            days = self.retention_days.get()
            
            # 确认操作
            confirm = messagebox.askyesno(
                "确认操作", 
                f"确定要清理 {days} 天前的所有结果文件吗？\n此操作不可撤销!"
            )
            
            if not confirm:
                return
                
            # 执行清理
            cleaned = cleanup_old_results(days_to_keep=days)
            
            # 显示结果
            if cleaned > 0:
                messagebox.showinfo("清理完成", f"已清理 {cleaned} 个旧结果目录")
            else:
                messagebox.showinfo("清理完成", "没有需要清理的旧文件")
                
        except Exception as e:
            messagebox.showerror("清理失败", f"清理文件时出错: {e}")
            print(f"清理文件出错: {e}")
            traceback.print_exc()

    def open_results_folder(self):
        """打开结果文件夹"""
        try:
            from .file_manager import get_results_folder
            
            # 获取结果文件夹路径
            results_folder = get_results_folder()
            
            # 确保文件夹存在
            os.makedirs(results_folder, exist_ok=True)
            
            # 打开文件夹
            import webbrowser
            webbrowser.open(f"file://{results_folder}")
            
        except Exception as e:
            messagebox.showerror("打开文件夹失败", f"无法打开结果文件夹: {e}")
            print(f"打开结果文件夹失败: {e}")

def main():
    try:
        # 创建应用程序，使用固定的默认主题
        root = ttk.Window(themename="cosmo")
        app = ModelFinderApp(root)
        
        # 获取有效的主题名称列表
        valid_themes = ["cosmo", "flatly", "litera", "minty", "lumen", 
                       "sandstone", "yeti", "pulse", "united", "morph", 
                       "journal", "darkly", "superhero", "solar", "cyborg"]
        
        # 随机选择一个主题
        random_theme = random.choice(valid_themes)
        print(f"应用随机主题: {random_theme}")
        
        # 应用随机主题
        style = ttk.Style()
        style.theme_use(random_theme)
        
        # 更新应用中的主题变量
        app.current_theme = random_theme
        app.theme_var.set(random_theme)
        
        # 设置窗口图标
        try:
            # 尝试设置图标
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            if os.path.exists(icon_path):
                root.iconbitmap(icon_path)
        except Exception as e:
            print(f"加载图标时出错: {e}")
        
        # 运行应用程序
        root.mainloop()
    except Exception as e:
        # 在GUI启动失败时提供错误反馈
        error_msg = f"程序启动失败: {type(e).__name__}: {str(e)}"
        try:
            # 尝试显示GUI错误窗口
            messagebox.showerror("启动错误", error_msg)
        except:
            # 如果连GUI错误窗口都无法显示，则使用控制台输出
            print("=" * 50)
            print(error_msg)
            print("-" * 50)
            traceback.print_exc()
            print("=" * 50)
            print("\n推荐解决方法:")
            print("1. 确保已安装所有依赖: pip install pandas DrissionPage ttkbootstrap")
            print("2. 确保Chrome浏览器已安装")
            print("3. 如有任何问题，请联系: WeChat wangdefa4567")
            input("按Enter键退出...")

if __name__ == "__main__":
    main()