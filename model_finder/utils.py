"""
Utility Functions Module
Contains helper functions: dependency check, browser detection, HTML generation, etc.
"""

import os
import sys
import subprocess
import traceback
from urllib.parse import urlparse, urljoin
import csv



def check_dependencies():
    """Check and install missing dependencies"""
    required_packages = {"pandas": "pandas", "DrissionPage": "DrissionPage", "ttkbootstrap": "ttkbootstrap"}
    missing_packages = []
    
    for package, pip_name in required_packages.items():
        try:
            __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"✗ Missing {package}")
            missing_packages.append(pip_name)
    
    if missing_packages:
        print("\nInstalling missing dependencies...")
        try:
            # Try using domestic mirror source
            cmd = [sys.executable, "-m", "pip", "install", 
                   "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"]
            cmd.extend(missing_packages)
            subprocess.check_call(cmd)
            print("Dependencies installed successfully!")
            
            # Need to restart script for imports to take effect
            print("Restarting program to apply changes...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(f"Error installing dependencies: {e}")
            # Try using backup mirror
            try:
                print("Trying alternative mirror...")
                cmd = [sys.executable, "-m", "pip", "install", 
                       "-i", "https://mirrors.aliyun.com/pypi/simple/"]
                cmd.extend(missing_packages)
                subprocess.check_call(cmd)
                print("Dependencies installed successfully!")
                
                # Need to restart script for imports to take effect
                print("Restarting program to apply changes...")
                os.execv(sys.executable, [sys.executable] + sys.argv)
            except Exception as e2:
                print(f"Error installing dependencies: {e2}")
                print("Please manually install the following packages:")
                for pkg in missing_packages:
                    print(f"pip install {pkg}")
                input("Press Enter to exit...")
                sys.exit(1)

def find_chrome_path():
    """Find Chrome browser path"""
    # Possible Chrome installation paths
    possible_paths = [
        # Windows standard paths
        os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        # Other possible Windows paths
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    ]
    
    # Check these paths
    for path in possible_paths:
        if os.path.exists(path):
            print(f"Found Chrome browser: {path}")
            return path
    
    # Get Chrome path from registry (Windows only)
    if sys.platform.startswith('win'):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as key:
                chrome_path = winreg.QueryValue(key, None)
                if os.path.exists(chrome_path):
                    print(f"Found Chrome browser from registry: {chrome_path}")
                    return chrome_path
        except Exception as e:
            print(f"Error checking registry: {e}")
    
    print("Warning: Chrome browser not found. Please install Chrome.")
    return None

def get_mirror_link(original_url):
    """Get Hugging Face mirror link"""
    if not original_url or 'huggingface.co' not in original_url:
        return ''
    
    try:
        # Parse URL to ensure correct format conversion
        parsed_url = urlparse(original_url)
        path = parsed_url.path
        
        # Ensure path format is correct (remove /resolve/ and replace with corresponding path)
        if '/resolve/' in path:
            path = path.replace('/resolve/', '/blob/')
            
        # Build correct mirror link
        mirror_base_url = "https://hf-mirror.com"
        mirror_url = urljoin(mirror_base_url, path)
        
        # Replace blob back to resolve for download
        if '/blob/' in mirror_url:
            mirror_url = mirror_url.replace('/blob/', '/resolve/')
            
        return mirror_url
    except Exception as e:
        print(f"Error building mirror link: {e}")
        return ''

def create_html_view(csv_file):
    """Create improved HTML view with table filtering and unified font
    
    Args:
        csv_file: CSV file path, can be single workflow result or summary file
    
    Returns:
        Generated HTML file path, or None if failed
    """
    import pandas as pd
    try:
        # Add debug info
        print(f"Creating HTML view for {csv_file}")
        
        # Read CSV file with different encodings
        try:
            df = pd.read_csv(csv_file, encoding='utf-8')
            print(f"Successfully read CSV, columns: {df.columns.tolist()}")
        except Exception:
            try:
                df = pd.read_csv(csv_file, encoding='utf-8-sig')
                print(f"Successfully read CSV with UTF-8-SIG, columns: {df.columns.tolist()}")
            except Exception as e:
                print(f"Failed to read CSV file: {e}")
                return None
        
        # Ensure required columns exist (adapt to different CSV formats)
        # Check for English column names and fall back to Chinese if needed
        required_columns = []
        if 'File Name' in df.columns:
            required_columns = ['File Name']
        elif '文件名' in df.columns:
            required_columns = ['文件名']
        elif 'Workflow File' in df.columns:
            required_columns = ['Workflow File']
        elif '工作流文件' in df.columns:
            required_columns = ['工作流文件']
        
        # Check if necessary columns exist
        for col in required_columns:
            if col not in df.columns:
                print(f"Error: CSV file must contain '{col}' column")
                return None
        
        # Process different column names for summary files or batch processing results
        core_columns = []
        if 'File Name' in df.columns:
            # Also include search link column
            core_columns.extend(['File Name', 'Download Link', 'Mirror Link', 'Search Link', 'Status'])
        elif 'CSV File' in df.columns:  # Batch processing result format
            core_columns.extend(['Workflow File', 'CSV File', 'Missing Quantity'])
        
        # Generate HTML file name
        html_file = os.path.splitext(csv_file)[0] + '.html'
        
        # Create HTML content - header
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
                
                /* Dropdown menu styles */
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
        
        # Add file information and statistics
        file_basename = os.path.basename(csv_file)
        html_content += f"""
            <p>Source file: {file_basename}</p>
            <p>Generated time: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """
        
        # Add usage guide
        html_content += """
            <div class="usage-guide">
                <p><strong>Usage Instructions:</strong></p>
                <ul style="margin: 5px 0 0 20px; padding: 0;">
                    <li>Click table headers to <strong>sort</strong> column content</li>
                    <li>Click the filter icon on the right of table headers to <strong>filter</strong> column content</li>
                    <li>Table <span style="color: #ff6000; font-size: 16px;">✓</span> indicates clickable links, <span>×</span> indicates no links</li>
                    <li><span style="color: #ff6000;">✓ Click to jump</span> - Jump to HuggingFace model page</li>
                    <li><span style="color: #0066ff;">✓ Click to jump</span> - Jump to HF mirror download page</li>
                    <li><span style="color: #00aa00;">✓ Click to jump</span> - Jump to LibLib model page</li>
                </ul>
            </div>
        """
        
        # If it's a model list, add global filtering functionality
        if 'File Name' in df.columns:
            html_content += """
            <div class="filter-box">
                <label for="filterInput">Filter model name: </label>
                <input type="text" id="filterInput" onkeyup="filterTable()" placeholder="Enter keyword...">
            </div>
            """
        
        # Start creating table
        html_content += """
            <table id="modelTable">
                <tr>
        """
        
        # Add table header - determine which columns to display
        display_columns = []
        for col in df.columns:
            if col in core_columns or col in ['Index', 'Node ID', 'Node Type', 'Missing Quantity']:
                display_columns.append(col)
                # Modify table header display
                display_name = col
                if col == 'Download Link':
                    display_name = 'huggingface'
                elif col == 'Mirror Link':
                    display_name = 'hf mirror'
                elif col == 'Search Link':
                    display_name = 'liblib'
                
                # Add column header with filter icon
                html_content += f'<th onclick="sortTable({len(display_columns)-1})">{display_name}<span class="filter-icon" onclick="event.stopPropagation(); showFilter(event, {len(display_columns)-1})">▼</span></th>\n'
        
        html_content += "</tr>\n"
        
        # Add data rows
        row_count = 0
        for index, row in df.iterrows():
            row_count += 1
            html_content += "<tr>\n"
            
            for col in display_columns:
                value = row.get(col, '')
                if pd.isna(value):
                    value = ''
                    
                if col == 'Status':
                    # Add styles for different statuses
                    if value == 'Processed':
                        status_class = "status-processed"
                    elif value == 'Processing Error':
                        status_class = "status-error"
                    else:
                        status_class = "status-notfound"
                    html_content += f'<td class="{status_class}">{value}</td>\n'
                elif col in ['File Name', 'CSV File', 'Workflow File']:
                    # Bold file name display
                    html_content += f'<td class="file-name">{value}</td>\n'
                elif col in ['Download Link', 'Mirror Link', 'Search Link']:
                    # Link column using ✓ or × to indicate
                    if value:
                        # Determine link text and style
                        link_text = "✓ Click to jump"  # Use uniform text
                        link_class = "link-col"
                        
                        # Set different classes based on column type and link content
                        if col == 'Download Link' and 'huggingface' in value:
                            link_class += " hf-link"
                            tooltip = "Click to jump to HuggingFace model page"
                        elif col == 'Mirror Link' and 'hf-mirror' in value:
                            link_class += " mirror-link"
                            tooltip = "Click to jump to HF mirror download page"
                        elif col == 'Search Link' and 'liblib' in value:
                            link_class += " liblib-link"
                            tooltip = "Click to jump to LibLib model page"
                        elif col == 'Download Link' and 'liblib' in value:
                            link_class += " liblib-link"
                            tooltip = "Click to jump to LibLib model page"
                        else:
                            tooltip = "Click to jump to download page"
                            
                        # Generate ✓ symbol with hover tooltip
                        html_content += f'<td class="{link_class}"><a href="{value}" target="_blank" title="{tooltip}">{link_text}</a></td>\n'
                    else:
                        # No link display × symbol
                        html_content += '<td>× No link</td>\n'
                else:
                    # Normal display for other columns
                    html_content += f'<td>{value}</td>\n'
            
            html_content += "</tr>\n"
        
        # Add table end tag and summary information
        html_content += """
            </table>
        """
        
        # Add total record count information
        html_content += f"""
            <div class="summary">
                <p>Total record count: {row_count}</p>
            </div>
        """
        
        # Add dropdown filter element
        html_content += """
            <div id="filterDropdown" class="dropdown-content">
                <input type="text" class="dropdown-search" placeholder="Search filter options..." id="filterSearchInput" onkeyup="filterDropdownItems()">
                <div id="dropdown-items"></div>
                <div class="filter-buttons">
                    <button class="filter-apply" onclick="applyFilter()">Apply</button>
                    <button class="filter-clear" onclick="clearFilter()">Clear</button>
                </div>
            </div>
        """
        
        # Add JavaScript functionality: sorting, filtering, and dropdown menu
        html_content += """
            <script>
            // Store current filtering state
            var currentFilterColumn = -1;
            var currentFilterValues = {};
            var tableHeaders = document.querySelectorAll("#modelTable th");
            
            // Sorting functionality
            function sortTable(n) {
                var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
                table = document.getElementById("modelTable");
                switching = true;
                // Set default sorting direction
                dir = "asc"; 
                
                while (switching) {
                    switching = false;
                    rows = table.rows;
                    
                    for (i = 1; i < (rows.length - 1); i++) {
                        shouldSwitch = false;
                        
                        x = rows[i].getElementsByTagName("TD")[n];
                        y = rows[i + 1].getElementsByTagName("TD")[n];
                        
                        // Special handling for "✓ Click to jump" and "× No link"
                        var xText = x.textContent || x.innerText;
                        var yText = y.textContent || y.innerText;
                        
                        // If it's a link column, sort based on whether there's a link (✓ before ×)
                        if (xText.includes("✓") || xText.includes("×")) {
                            var xHasLink = xText.includes("✓");
                            var yHasLink = yText.includes("✓");
                            
                            if (dir == "asc") {
                                shouldSwitch = (!xHasLink && yHasLink);
                            } else {
                                shouldSwitch = (xHasLink && !yHasLink);
                            }
                        } else {
                            // Default alphabetical order comparison
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
                    
                    // If a full sorting pass was made without switching, change sorting direction
                    if (switchcount == 0 && dir == "asc") {
                        dir = "desc";
                        switching = true;
                    }
                }
                
                // Update table header status
                for (i = 0; i < tableHeaders.length; i++) {
                    tableHeaders[i].querySelector(".filter-icon").textContent = "▼";
                }
                tableHeaders[n].querySelector(".filter-icon").textContent = (dir === "asc") ? "▲" : "▼";
            }
            
            // Global filtering functionality (existing search functionality)
            function filterTable() {
                var input, filter, table, tr, found;
                input = document.getElementById("filterInput");
                filter = input.value.toUpperCase();
                table = document.getElementById("modelTable");
                tr = table.getElementsByTagName("tr");
                
                for (var i = 1; i < tr.length; i++) {
                    found = false;
                    var td = tr[i].getElementsByTagName("td");
                    
                    // First check if row passes column filters
                    if (!passesColumnFilters(tr[i])) {
                        tr[i].style.display = "none";
                        continue;
                    }
                    
                    // Then check keyword search
                    if (filter === "") {
                        found = true; // If search box is empty, display all rows passing column filters
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
            
            // Show column filter dropdown menu
            function showFilter(event, colIndex) {
                var dropdown = document.getElementById("filterDropdown");
                
                // Set current filtering column
                currentFilterColumn = colIndex;
                
                // Calculate dropdown menu position
                var th = event.target.closest('th');
                var rect = th.getBoundingClientRect();
                dropdown.style.left = rect.left + window.pageXOffset + "px";
                dropdown.style.top = rect.bottom + window.pageYOffset + "px";
                dropdown.style.minWidth = rect.width + "px";
                
                // Generate unique value list
                populateDropdown(colIndex);
                
                // Show dropdown menu
                dropdown.classList.add("show");
                
                // Click elsewhere to close dropdown menu
                window.onclick = function(event) {
                    if (!event.target.matches('.filter-icon') && 
                        !event.target.closest('#filterDropdown')) {
                        dropdown.classList.remove("show");
                    }
                }
            }
            
            // Generate dropdown menu options
            function populateDropdown(colIndex) {
                var table = document.getElementById("modelTable");
                var rows = table.getElementsByTagName("tr");
                var uniqueValues = new Set();
                
                // Collect unique values
                for (var i = 1; i < rows.length; i++) {
                    var cell = rows[i].getElementsByTagName("td")[colIndex];
                    var value = cell.textContent || cell.innerText;
                    uniqueValues.add(value.trim());
                }
                
                // Convert to array and sort
                var sortedValues = Array.from(uniqueValues).sort();
                
                // Clear and re-populate dropdown menu
                var dropdown = document.getElementById("dropdown-items");
                dropdown.innerHTML = "";
                
                // Add "Select All" option
                var allItem = document.createElement("div");
                allItem.className = "dropdown-item";
                allItem.innerHTML = '<input type="checkbox" id="select-all" onchange="toggleAll(this.checked)"> <label for="select-all">Select All</label>';
                dropdown.appendChild(allItem);
                
                // Add divider
                var divider = document.createElement("hr");
                dropdown.appendChild(divider);
                
                // Add each unique value
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
                
                // Update Select All checkbox status
                updateSelectAllCheckbox();
            }
            
            // Filter dropdown menu items
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
            
            // Apply filtering
            function applyFilter() {
                // Get selected values
                var selectedValues = [];
                var checkboxes = document.querySelectorAll("#dropdown-items .dropdown-item:not(:first-child) input[type='checkbox']");
                
                checkboxes.forEach(function(checkbox) {
                    if (checkbox.checked) {
                        selectedValues.push(checkbox.value);
                    }
                });
                
                // Save selected values
                currentFilterValues[currentFilterColumn] = selectedValues;
                
                // Update table header icon
                if (selectedValues.length > 0 && selectedValues.length < checkboxes.length) {
                    tableHeaders[currentFilterColumn].querySelector(".filter-icon").textContent = "🔍";
                } else {
                    tableHeaders[currentFilterColumn].querySelector(".filter-icon").textContent = "▼";
                }
                
                // Close dropdown menu
                document.getElementById("filterDropdown").classList.remove("show");
                
                // Apply filtering
                filterTable();
            }
            
            // Clear filtering
            function clearFilter() {
                // Clear current column filtering
                if (currentFilterColumn in currentFilterValues) {
                    delete currentFilterValues[currentFilterColumn];
                }
                
                // Update table header icon
                tableHeaders[currentFilterColumn].querySelector(".filter-icon").textContent = "▼";
                
                // Reset checkboxes
                var checkboxes = document.querySelectorAll("#dropdown-items .dropdown-item input[type='checkbox']");
                checkboxes.forEach(function(checkbox) {
                    checkbox.checked = true;
                });
                
                // Close dropdown menu
                document.getElementById("filterDropdown").classList.remove("show");
                
                // Re-apply filtering
                filterTable();
            }
            
            // Select/unselect all
            function toggleAll(checked) {
                var checkboxes = document.querySelectorAll("#dropdown-items .dropdown-item:not(:first-child) input[type='checkbox']");
                checkboxes.forEach(function(checkbox) {
                    if (checkbox.parentElement.style.display !== "none") { // Only process visible checkboxes
                        checkbox.checked = checked;
                    }
                });
            }
            
            // Update Select All checkbox status
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
            
            // Check if row passes column filters
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
        
        # End HTML
        html_content += """
        </body>
        </html>
        """
        
        # Write HTML file
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return html_file
    except Exception as e:
        print(f"Error creating HTML view: {e}")
        traceback.print_exc()
        return None 