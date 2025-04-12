"""
工具函数模块
包含辅助功能：依赖检查、浏览器检测、HTML生成等
"""

import os
import sys
import subprocess
import traceback
from urllib.parse import urlparse, urljoin
import csv



def check_dependencies():
    """检查并安装缺失依赖"""
    required_packages = {"pandas": "pandas", "DrissionPage": "DrissionPage", "ttkbootstrap": "ttkbootstrap"}
    missing_packages = []
    
    for package, pip_name in required_packages.items():
        try:
            __import__(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            print(f"✗ 缺少 {package}")
            missing_packages.append(pip_name)
    
    if missing_packages:
        print("\n安装缺失依赖...")
        try:
            # 尝试使用国内镜像源安装
            cmd = [sys.executable, "-m", "pip", "install", 
                   "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"]
            cmd.extend(missing_packages)
            subprocess.check_call(cmd)
            print("依赖安装成功!")
            
            # 需要重启脚本以使导入生效
            print("重启程序以应用更改...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(f"安装依赖出错: {e}")
            # 尝试使用备用源
            try:
                print("尝试备用镜像...")
                cmd = [sys.executable, "-m", "pip", "install", 
                       "-i", "https://mirrors.aliyun.com/pypi/simple/"]
                cmd.extend(missing_packages)
                subprocess.check_call(cmd)
                print("依赖安装成功!")
                
                # 需要重启脚本以使导入生效
                print("重启程序以应用更改...")
                os.execv(sys.executable, [sys.executable] + sys.argv)
            except Exception as e2:
                print(f"安装依赖出错: {e2}")
                print("请手动安装以下包:")
                for pkg in missing_packages:
                    print(f"pip install {pkg}")
                input("按Enter键退出...")
                sys.exit(1)

def find_chrome_path():
    """查找Chrome浏览器路径"""
    # 可能的Chrome安装路径
    possible_paths = [
        # Windows 标准路径
        os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        # 其他可能的Windows路径
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    ]
    
    # 检查这些路径
    for path in possible_paths:
        if os.path.exists(path):
            print(f"找到Chrome浏览器: {path}")
            return path
    
    # 从注册表获取Chrome路径(仅Windows)
    if sys.platform.startswith('win'):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as key:
                chrome_path = winreg.QueryValue(key, None)
                if os.path.exists(chrome_path):
                    print(f"从注册表找到Chrome浏览器: {chrome_path}")
                    return chrome_path
        except Exception as e:
            print(f"检查注册表时出错: {e}")
    
    print("警告: 未找到Chrome浏览器。请安装Chrome。")
    return None

def get_mirror_link(original_url):
    """获取Hugging Face的镜像链接"""
    if not original_url or 'huggingface.co' not in original_url:
        return ''
    
    try:
        # 解析URL以确保正确的格式转换
        parsed_url = urlparse(original_url)
        path = parsed_url.path
        
        # 确保路径格式正确（移除/resolve/并替换为对应路径）
        if '/resolve/' in path:
            path = path.replace('/resolve/', '/blob/')
            
        # 构建正确的镜像链接
        mirror_base_url = "https://hf-mirror.com"
        mirror_url = urljoin(mirror_base_url, path)
        
        # 将blob替换回resolve用于下载
        if '/blob/' in mirror_url:
            mirror_url = mirror_url.replace('/blob/', '/resolve/')
            
        return mirror_url
    except Exception as e:
        print(f"构建镜像链接时出错: {e}")
        return ''

def create_html_view(csv_file):
    """创建改进的HTML视图，包含表头筛选和统一字体
    
    参数:
        csv_file: CSV文件路径，可能是单个工作流的结果或汇总文件
    
    返回:
        生成的HTML文件路径，失败则返回None
    """
    import pandas as pd
    try:
        # 添加调试信息
        print(f"正在为 {csv_file} 创建HTML视图")
        
        # 读取CSV文件并尝试不同的编码
        try:
            df = pd.read_csv(csv_file, encoding='utf-8')
            print(f"成功读取CSV，列名: {df.columns.tolist()}")
        except Exception:
            try:
                df = pd.read_csv(csv_file, encoding='utf-8-sig')
                print(f"使用UTF-8-SIG成功读取CSV，列名: {df.columns.tolist()}")
            except Exception as e:
                print(f"读取CSV文件失败: {e}")
                return None
        
        # 确保必要的列存在（适配不同的CSV格式）
        required_columns = ['文件名']
        
        # 检查必要的列是否存在
        for col in required_columns:
            if col not in df.columns:
                print(f"错误: CSV文件必须包含'{col}'列")
                return None
        
        # 处理汇总文件或批量处理结果的不同列名
        core_columns = []
        if '文件名' in df.columns:
            # 也包含搜索链接列
            core_columns.extend(['文件名', '下载链接', '镜像链接', '搜索链接', '状态'])
        elif 'CSV文件' in df.columns:  # 批量处理结果格式
            core_columns.extend(['工作流文件', 'CSV文件', '缺失数量'])
        
        # 生成HTML文件名
        html_file = os.path.splitext(csv_file)[0] + '.html'
        
        # 创建HTML内容 - 头部
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>模型下载链接</title>
            <style>
                body { font-family: "Microsoft YaHei", Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { 
                    background-color: #f2f2f2; 
                    position: sticky; 
                    top: 0; 
                    cursor: pointer;
                    user-select: none;
                }
                th:hover {
                    background-color: #e0e0e0;
                }
                th .filter-icon {
                    margin-left: 5px;
                    font-size: 12px;
                    color: #666;
                }
                tr:nth-child(even) { background-color: #f9f9f9; }
                a { text-decoration: none; }
                a:hover { text-decoration: underline; }
                .status-processed { color: green; font-weight: bold; }
                .status-notfound { color: red; }
                .status-error { color: orange; }
                .file-name { font-weight: bold; }
                .link-col { max-width: 300px; text-align: center; font-size: 16px; font-family: "Microsoft YaHei", Arial, sans-serif; }
                .summary { margin-top: 20px; padding: 10px; background-color: #f8f8f8; border-radius: 5px; }
                .section-title { font-size: 1.2em; margin-top: 30px; margin-bottom: 10px; font-weight: bold; }
                .filter-box { margin-bottom: 20px; padding: 10px; background: #f0f0f0; border-radius: 5px; }
                #filterInput { width: 300px; padding: 5px; }
                .hf-link { color: #ff6000; }
                .mirror-link { color: #0066ff; }
                .liblib-link { color: #00aa00; }
                .hf-link a, .mirror-link a, .liblib-link a { text-decoration: none; }
                
                /* 下拉菜单样式 */
                .dropdown-content {
                    display: none;
                    position: absolute;
                    background-color: white;
                    min-width: 160px;
                    box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.2);
                    z-index: 10;
                    padding: 5px;
                    border-radius: 3px;
                    max-height: 300px;
                    overflow-y: auto;
                }
                .dropdown-content.show {
                    display: block;
                }
                .dropdown-item {
                    padding: 5px;
                    cursor: pointer;
                }
                .dropdown-item:hover {
                    background-color: #f1f1f1;
                }
                .dropdown-search {
                    width: 100%;
                    box-sizing: border-box;
                    padding: 5px;
                    margin-bottom: 5px;
                }
                .filter-buttons {
                    display: flex;
                    justify-content: space-between;
                    margin-top: 5px;
                }
                .filter-apply, .filter-clear {
                    padding: 3px 8px;
                    cursor: pointer;
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                }
                .filter-apply:hover, .filter-clear:hover {
                    background-color: #e0e0e0;
                }
                .usage-guide { 
                    margin-bottom: 15px; 
                    padding: 10px; 
                    background: #f8fff8; 
                    border-left: 4px solid #00aa00; 
                    border-radius: 3px;
                }
            </style>
        </head>
        <body>
            <h1>模型下载链接</h1>
        """
        
        # 添加文件信息和统计
        file_basename = os.path.basename(csv_file)
        html_content += f"""
            <p>源文件: {file_basename}</p>
            <p>生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """
        
        # 添加使用指南
        html_content += """
            <div class="usage-guide">
                <p><strong>使用说明:</strong></p>
                <ul style="margin: 5px 0 0 20px; padding: 0;">
                    <li>点击表格标题可以<strong>排序</strong>列内容</li>
                    <li>点击表格标题右侧的筛选图标可以<strong>筛选</strong>列内容</li>
                    <li>表格中 <span style="color: #ff6000; font-size: 16px;">✓</span> 表示有链接可点击，<span>×</span> 表示无链接</li>
                    <li><span style="color: #ff6000;">✓点此跳转</span> - 跳转到 HuggingFace 模型页面</li>
                    <li><span style="color: #0066ff;">✓点此跳转</span> - 跳转到 HF镜像 下载页面</li>
                    <li><span style="color: #00aa00;">✓点此跳转</span> - 跳转到 LibLib 模型页面</li>
                </ul>
            </div>
        """
        
        # 如果是模型列表，添加全局筛选功能
        if '文件名' in df.columns:
            html_content += """
            <div class="filter-box">
                <label for="filterInput">筛选模型名称: </label>
                <input type="text" id="filterInput" onkeyup="filterTable()" placeholder="输入关键词...">
            </div>
            """
        
        # 开始创建表格
        html_content += """
            <table id="modelTable">
                <tr>
        """
        
        # 添加表头 - 确定要显示的列
        display_columns = []
        for col in df.columns:
            if col in core_columns or col in ['序号', '节点ID', '节点类型', '缺失数量']:
                display_columns.append(col)
                # 修改表头显示
                display_name = col
                if col == '下载链接':
                    display_name = 'huggingface'
                elif col == '镜像链接':
                    display_name = 'hf镜像'
                elif col == '搜索链接':
                    display_name = 'liblib'
                
                # 添加带筛选图标的表头
                html_content += f'<th onclick="sortTable({len(display_columns)-1})">{display_name}<span class="filter-icon" onclick="event.stopPropagation(); showFilter(event, {len(display_columns)-1})">▼</span></th>\n'
        
        html_content += "</tr>\n"
        
        # 添加数据行
        row_count = 0
        for index, row in df.iterrows():
            row_count += 1
            html_content += "<tr>\n"
            
            for col in display_columns:
                value = row.get(col, '')
                if pd.isna(value):
                    value = ''
                    
                if col == '状态':
                    # 为不同状态添加样式
                    if value == '已处理':
                        status_class = "status-processed"
                    elif value == '处理错误':
                        status_class = "status-error"
                    else:
                        status_class = "status-notfound"
                    html_content += f'<td class="{status_class}">{value}</td>\n'
                elif col in ['文件名', 'CSV文件', '工作流文件']:
                    # 文件名加粗显示
                    html_content += f'<td class="file-name">{value}</td>\n'
                elif col in ['下载链接', '镜像链接', '搜索链接']:
                    # 链接列使用✓或×表示
                    if value:
                        # 确定链接文本与样式
                        link_text = "✓点此跳转"  # 使用统一的文本
                        link_class = "link-col"
                        
                        # 根据列类型和链接内容设置不同的类
                        if col == '下载链接' and 'huggingface' in value:
                            link_class += " hf-link"
                            tooltip = "点击跳转到HuggingFace模型页面"
                        elif col == '镜像链接' and 'hf-mirror' in value:
                            link_class += " mirror-link"
                            tooltip = "点击跳转到HF镜像下载页面"
                        elif col == '搜索链接' and 'liblib' in value:
                            link_class += " liblib-link"
                            tooltip = "点击跳转到LibLib模型页面"
                        elif col == '下载链接' and 'liblib' in value:
                            link_class += " liblib-link"
                            tooltip = "点击跳转到LibLib模型页面"
                        else:
                            tooltip = "点击跳转到下载页面"
                            
                        # 生成带链接的✓符号，添加鼠标悬停提示
                        html_content += f'<td class="{link_class}"><a href="{value}" target="_blank" title="{tooltip}">{link_text}</a></td>\n'
                    else:
                        # 没有链接显示×符号
                        html_content += '<td>×暂无</td>\n'
                else:
                    # 其他列正常显示
                    html_content += f'<td>{value}</td>\n'
            
            html_content += "</tr>\n"
        
        # 添加表格结束标签和汇总信息
        html_content += """
            </table>
        """
        
        # 添加记录总数信息
        html_content += f"""
            <div class="summary">
                <p>总记录数: {row_count}</p>
            </div>
        """
        
        # 添加下拉筛选框元素
        html_content += """
            <div id="filterDropdown" class="dropdown-content">
                <input type="text" class="dropdown-search" placeholder="搜索筛选项..." id="filterSearchInput" onkeyup="filterDropdownItems()">
                <div id="dropdown-items"></div>
                <div class="filter-buttons">
                    <button class="filter-apply" onclick="applyFilter()">应用</button>
                    <button class="filter-clear" onclick="clearFilter()">清除</button>
                </div>
            </div>
        """
        
        # 添加JavaScript功能：排序、筛选和下拉菜单
        html_content += """
            <script>
            // 存储当前的筛选状态
            var currentFilterColumn = -1;
            var currentFilterValues = {};
            var tableHeaders = document.querySelectorAll("#modelTable th");
            
            // 排序功能
            function sortTable(n) {
                var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
                table = document.getElementById("modelTable");
                switching = true;
                // 设置默认排序方向
                dir = "asc"; 
                
                while (switching) {
                    switching = false;
                    rows = table.rows;
                    
                    for (i = 1; i < (rows.length - 1); i++) {
                        shouldSwitch = false;
                        
                        x = rows[i].getElementsByTagName("TD")[n];
                        y = rows[i + 1].getElementsByTagName("TD")[n];
                        
                        // 对"✓点此跳转"和"×暂无"特殊处理
                        var xText = x.textContent || x.innerText;
                        var yText = y.textContent || y.innerText;
                        
                        // 如果是链接列，根据是否有链接进行排序（✓ 在前，× 在后）
                        if (xText.includes("✓") || xText.includes("×")) {
                            var xHasLink = xText.includes("✓");
                            var yHasLink = yText.includes("✓");
                            
                            if (dir == "asc") {
                                shouldSwitch = (!xHasLink && yHasLink);
                            } else {
                                shouldSwitch = (xHasLink && !yHasLink);
                            }
                        } else {
                            // 默认字母顺序比较
                            if (dir == "asc") {
                                shouldSwitch = xText.toLowerCase() > yText.toLowerCase();
                            } else {
                                shouldSwitch = xText.toLowerCase() < yText.toLowerCase();
                            }
                        }
                        
                        if (shouldSwitch) {
                            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                            switching = true;
                            switchcount++;
                        }
                    }
                    
                    // 如果完成了一轮排序而没有切换，改变排序方向
                    if (switchcount == 0 && dir == "asc") {
                        dir = "desc";
                        switching = true;
                    }
                }
                
                // 更新表头状态
                for (i = 0; i < tableHeaders.length; i++) {
                    tableHeaders[i].querySelector(".filter-icon").textContent = "▼";
                }
                tableHeaders[n].querySelector(".filter-icon").textContent = (dir === "asc") ? "▲" : "▼";
            }
            
            // 全局筛选功能（现有的搜索功能）
            function filterTable() {
                var input, filter, table, tr, found;
                input = document.getElementById("filterInput");
                filter = input.value.toUpperCase();
                table = document.getElementById("modelTable");
                tr = table.getElementsByTagName("tr");
                
                for (var i = 1; i < tr.length; i++) {
                    found = false;
                    var td = tr[i].getElementsByTagName("td");
                    
                    // 首先检查是否通过列筛选
                    if (!passesColumnFilters(tr[i])) {
                        tr[i].style.display = "none";
                        continue;
                    }
                    
                    // 然后检查关键词搜索
                    if (filter === "") {
                        found = true; // 如果搜索框为空，显示所有通过列筛选的行
                    } else {
                        for (var j = 0; j < td.length; j++) {
                            var txtValue = td[j].textContent || td[j].innerText;
                            if (txtValue.toUpperCase().indexOf(filter) > -1) {
                                found = true;
                                break;
                            }
                        }
                    }
                    
                    if (found) {
                        tr[i].style.display = "";
                    } else {
                        tr[i].style.display = "none";
                    }
                }
            }
            
            // 显示列筛选下拉菜单
            function showFilter(event, colIndex) {
                var dropdown = document.getElementById("filterDropdown");
                
                // 设置当前筛选列
                currentFilterColumn = colIndex;
                
                // 计算下拉菜单位置
                var th = event.target.closest('th');
                var rect = th.getBoundingClientRect();
                dropdown.style.left = rect.left + window.pageXOffset + "px";
                dropdown.style.top = rect.bottom + window.pageYOffset + "px";
                dropdown.style.minWidth = rect.width + "px";
                
                // 生成唯一值列表
                populateDropdown(colIndex);
                
                // 显示下拉菜单
                dropdown.classList.add("show");
                
                // 点击其他地方关闭下拉菜单
                window.onclick = function(event) {
                    if (!event.target.matches('.filter-icon') && 
                        !event.target.closest('#filterDropdown')) {
                        dropdown.classList.remove("show");
                    }
                }
            }
            
            // 生成下拉菜单选项
            function populateDropdown(colIndex) {
                var table = document.getElementById("modelTable");
                var rows = table.getElementsByTagName("tr");
                var uniqueValues = new Set();
                
                // 收集唯一值
                for (var i = 1; i < rows.length; i++) {
                    var cell = rows[i].getElementsByTagName("td")[colIndex];
                    var value = cell.textContent || cell.innerText;
                    uniqueValues.add(value.trim());
                }
                
                // 转换为数组并排序
                var sortedValues = Array.from(uniqueValues).sort();
                
                // 清空并重新填充下拉菜单
                var dropdown = document.getElementById("dropdown-items");
                dropdown.innerHTML = "";
                
                // 添加"全选"选项
                var allItem = document.createElement("div");
                allItem.className = "dropdown-item";
                allItem.innerHTML = '<input type="checkbox" id="select-all" onchange="toggleAll(this.checked)"> <label for="select-all">全选</label>';
                dropdown.appendChild(allItem);
                
                // 添加分隔线
                var divider = document.createElement("hr");
                dropdown.appendChild(divider);
                
                // 添加每个唯一值
                sortedValues.forEach(function(value, index) {
                    var item = document.createElement("div");
                    item.className = "dropdown-item";
                    var checkboxId = "filter-item-" + index;
                    var isChecked = !currentFilterValues[currentFilterColumn] || 
                                    currentFilterValues[currentFilterColumn].includes(value);
                    
                    item.innerHTML = `<input type="checkbox" id="${checkboxId}" value="${value}" ${isChecked ? "checked" : ""}> 
                                     <label for="${checkboxId}">${value}</label>`;
                    dropdown.appendChild(item);
                });
                
                // 更新全选复选框状态
                updateSelectAllCheckbox();
            }
            
            // 筛选下拉菜单项
            function filterDropdownItems() {
                var input = document.getElementById("filterSearchInput");
                var filter = input.value.toUpperCase();
                var items = document.querySelectorAll("#dropdown-items .dropdown-item:not(:first-child)");
                
                items.forEach(function(item) {
                    var text = item.textContent || item.innerText;
                    if (text.toUpperCase().indexOf(filter) > -1) {
                        item.style.display = "";
                    } else {
                        item.style.display = "none";
                    }
                });
            }
            
            // 应用筛选
            function applyFilter() {
                // 获取选中的值
                var selectedValues = [];
                var checkboxes = document.querySelectorAll("#dropdown-items .dropdown-item:not(:first-child) input[type='checkbox']");
                
                checkboxes.forEach(function(checkbox) {
                    if (checkbox.checked) {
                        selectedValues.push(checkbox.value);
                    }
                });
                
                // 保存选中的值
                currentFilterValues[currentFilterColumn] = selectedValues;
                
                // 更新表头图标
                if (selectedValues.length > 0 && selectedValues.length < checkboxes.length) {
                    tableHeaders[currentFilterColumn].querySelector(".filter-icon").textContent = "🔍";
                } else {
                    tableHeaders[currentFilterColumn].querySelector(".filter-icon").textContent = "▼";
                }
                
                // 关闭下拉菜单
                document.getElementById("filterDropdown").classList.remove("show");
                
                // 应用筛选
                filterTable();
            }
            
            // 清除筛选
            function clearFilter() {
                // 清除当前列的筛选
                if (currentFilterColumn in currentFilterValues) {
                    delete currentFilterValues[currentFilterColumn];
                }
                
                // 更新表头图标
                tableHeaders[currentFilterColumn].querySelector(".filter-icon").textContent = "▼";
                
                // 重置复选框
                var checkboxes = document.querySelectorAll("#dropdown-items .dropdown-item input[type='checkbox']");
                checkboxes.forEach(function(checkbox) {
                    checkbox.checked = true;
                });
                
                // 关闭下拉菜单
                document.getElementById("filterDropdown").classList.remove("show");
                
                // 重新应用筛选
                filterTable();
            }
            
            // 全选/取消全选
            function toggleAll(checked) {
                var checkboxes = document.querySelectorAll("#dropdown-items .dropdown-item:not(:first-child) input[type='checkbox']");
                checkboxes.forEach(function(checkbox) {
                    if (checkbox.parentElement.style.display !== "none") { // 只处理可见的复选框
                        checkbox.checked = checked;
                    }
                });
            }
            
            // 更新全选复选框状态
            function updateSelectAllCheckbox() {
                var allCheckbox = document.getElementById("select-all");
                var checkboxes = document.querySelectorAll("#dropdown-items .dropdown-item:not(:first-child) input[type='checkbox']");
                var allChecked = true;
                var anyVisible = false;
                
                checkboxes.forEach(function(checkbox) {
                    if (checkbox.parentElement.style.display !== "none") {
                        anyVisible = true;
                        if (!checkbox.checked) {
                            allChecked = false;
                        }
                    }
                });
                
                allCheckbox.checked = anyVisible && allChecked;
                allCheckbox.indeterminate = !allChecked && anyVisible;
            }
            
            // 判断行是否通过列筛选
            function passesColumnFilters(row) {
                var cells = row.getElementsByTagName("td");
                
                for (var colIdx in currentFilterValues) {
                    var cellValue = cells[colIdx].textContent || cells[colIdx].innerText;
                    var allowedValues = currentFilterValues[colIdx];
                    
                    if (allowedValues && !allowedValues.includes(cellValue.trim())) {
                        return false;
                    }
                }
                
                return true;
            }
            </script>
        """
        
        # 结束HTML
        html_content += """
        </body>
        </html>
        """
        
        # 写入HTML文件
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return html_file
    except Exception as e:
        print(f"创建HTML视图时出错: {e}")
        traceback.print_exc()
        return None 