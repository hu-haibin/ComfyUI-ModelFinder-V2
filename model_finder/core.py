"""
核心功能模块
包含：检测缺失模型文件、查找下载链接等核心功能
"""

import os
import sys
import json
import time
import csv
import traceback
import re
from .utils import get_mirror_link, create_html_view

def contains_chinese(text):
    """检测字符串是否包含中文字符"""
    if not isinstance(text, str):
        return False
    # 使用Unicode范围检测中文字符
    pattern = re.compile(r'[\u4e00-\u9fff]')
    return bool(pattern.search(text))

def get_search_url(keyword):
    """根据关键词特点生成不同的搜索URL"""
    if contains_chinese(keyword):
        # 中文模型名称使用liblib.art搜索
        return f"https://www.bing.com/?setlang=en-US", f'site:liblib.art "{keyword}"'
    else:
        # 非中文名称使用huggingface搜索
        return f"https://www.bing.com/?setlang=en-US", f'site:huggingface.co "{keyword}"'

def find_missing_models(workflow_file):
    """从工作流文件中提取缺失的模型文件"""
    print(f"分析工作流文件: {workflow_file}")
    
    # 获取工作流文件所在目录
    base_dir = os.path.dirname(os.path.abspath(workflow_file))
    
    # 加载工作流JSON
    try:
        with open(workflow_file, 'r', encoding='utf-8', errors='ignore') as f:
            # 设置文件大小限制 (50MB)
            max_file_size = 50 * 1024 * 1024
            file_size = os.path.getsize(workflow_file)
            
            if file_size > max_file_size:
                print(f"警告: 文件大小 ({file_size/1024/1024:.2f}MB) 超过限制，可能处理较慢")
            
            # 使用超时加载JSON
            start_time = time.time()
            timeout = 10  # 10秒超时
            
            try:
                workflow_json = json.load(f)
                elapsed_time = time.time() - start_time
                print(f"JSON加载用时: {elapsed_time:.2f}秒")
                
                if elapsed_time > 5:
                    print("警告: JSON加载时间较长，可能是复杂工作流")
            except Exception as e:
                print(f"JSON解析失败: {e}")
                # 尝试逐行读取JSON以确定问题
                print("尝试逐行读取JSON...")
                f.seek(0)
                for i, line in enumerate(f):
                    if i % 10000 == 0:
                        print(f"已读取 {i} 行")
                        # 检查超时
                        if time.time() - start_time > timeout:
                            print("读取JSON超时，放弃处理")
                            return []
                
                return []
    except MemoryError:
        print("内存不足，无法加载工作流文件")
        return []
    except Exception as e:
        print(f"加载工作流文件时出错: {e}")
        return []
    
    # 检查工作流JSON格式
    if not isinstance(workflow_json, dict):
        print(f"工作流文件格式有误: 根对象不是字典")
        return []
    
    # 查找文件引用
    file_references = []
    model_extensions = ('.safetensors', '.pth', '.ckpt', '.pt', '.bin', '.onnx')
    
    # 模型相关的节点类型 - 基于ComfyUI的常见模型加载节点
    model_node_types = [
        "CheckpointLoaderSimple",
        "CheckpointLoader", 
        "ControlNetLoader",
        "DiffControlNetLoader", 
        "LoraLoader",
        "CLIPLoader",
        "UNETLoader",
        "VAELoader",
        "ModelLoader",
        "UpscaleModelLoader",
        "StyleModelLoader",
        "CLIPVisionLoader",
        "GANLoader",
        "InstantIDModelLoader",
        "EcomID_PulidModelLoader",
        "PulidEvaClipLoader",
        "UltralyticsDetectorProvider"
    ]
    
    # 限制节点数量以避免处理时间过长
    max_nodes = 1000
    nodes = workflow_json.get('nodes', [])
    
    if len(nodes) > max_nodes:
        print(f"警告: 节点数量 ({len(nodes)}) 超过限制，将只处理前 {max_nodes} 个节点")
        nodes = nodes[:max_nodes]
    
    # 处理所有节点
    start_time = time.time()
    processed_nodes = 0
    
    try:
        # 处理所有节点
        for node in nodes:
            processed_nodes += 1
            
            # 每处理50个节点检查一次超时
            if processed_nodes % 50 == 0:
                elapsed = time.time() - start_time
                if elapsed > 20:  # 20秒超时
                    print(f"处理节点超时，已处理 {processed_nodes}/{len(nodes)} 个节点")
                    break
            
            node_id = node.get('id')
            node_type = node.get('type', '')
            widgets_values = node.get('widgets_values', [])
            
            # 获取节点的properties
            properties = node.get('properties', {})
            property_node_name = properties.get('Node name for S&R', '')
            
            # 如果properties中有模型相关的节点名，使用它作为节点类型
            if property_node_name and property_node_name in model_node_types:
                node_type = property_node_name
            
            # 检查是否是模型节点类型 (使用ComfyUI的启发式方法)
            is_model_node = node_type in model_node_types or "Loader" in node_type
            
            # 如果不是模型节点，跳过
            if not is_model_node:
                continue
                
            # 跳过空的widgets_values
            if not widgets_values:
                continue
            
            # ComfyUI中模型文件通常是第一个参数
            # 检查第一个widgets_value是否可能是模型文件
            if len(widgets_values) > 0 and isinstance(widgets_values[0], str):
                value = widgets_values[0].strip()
                
                # 跳过空字符串
                if not value:
                    continue
                
                # 跳过包含换行符的字符串(文件名不会有换行)
                if '\n' in value or '\r' in value:
                    continue
                
                # 排除一些常见的非模型选项值
                common_non_model_options = ["default", "none", "empty", "auto", "off", "on"]
                if value.lower() in common_non_model_options:
                    continue
                    
                # 提取文件名（去掉路径）
                if '\\' in value or '/' in value:
                    value = os.path.basename(value.replace('\\', '/'))
                
                # 添加到引用列表
                file_references.append({
                    'node_id': node_id,
                    'node_type': node_type,
                    'file_path': value
                })
    except Exception as e:
        print(f"处理节点时出错: {e}")
        traceback.print_exc()
    
    print(f"节点处理完成，用时: {time.time() - start_time:.2f}秒")
    
    if not file_references:
        print("工作流中未找到文件引用。")
        return []
    
    print(f"在工作流中找到 {len(file_references)} 个模型文件引用。")
    
    # 检查文件是否存在 - 采用ComfyUI的逻辑
    missing_files = []
    
    # 为了提高效率，先缓存所有文件存在性检查的结果
    file_existence_cache = {}
    
    for ref in file_references:
        try:
            file_path = ref['file_path']
            name, ext = os.path.splitext(file_path)
            
            # 处理不同的路径格式
            paths_to_check = [file_path, os.path.join(base_dir, file_path)]
            
            # 如果没有扩展名，添加所有可能的扩展名
            if not ext:
                for model_ext in model_extensions:
                    paths_to_check.append(f"{file_path}{model_ext}")
                    paths_to_check.append(os.path.join(base_dir, f"{file_path}{model_ext}"))
            
            # 检查文件是否存在于任何可能的路径
            file_exists = False
            for p in paths_to_check:
                if p in file_existence_cache:
                    # 使用缓存结果
                    if file_existence_cache[p]:
                        file_exists = True
                        break
                else:
                    # 检查并缓存结果
                    exists = os.path.exists(p)
                    file_existence_cache[p] = exists
                    if exists:
                        file_exists = True
                        break
            
            if not file_exists:
                missing_files.append({
                    'node_id': ref['node_id'],
                    'node_type': ref['node_type'],
                    'file_path': file_path
                })
        except Exception as e:
            print(f"检查文件 {ref.get('file_path', 'unknown')} 是否存在时出错: {e}")
    
    if not missing_files:
        print("\n所有引用的文件都存在！")
        return []
    
    # 统计缺失文件
    print(f"\n缺失模型文件总数: {len(missing_files)}")
    
    # 打印缺失文件列表
    print("\n缺失文件列表:")
    print("-" * 50)
    for i, missing in enumerate(missing_files, 1):
        print(f"{i}. {missing['file_path']}")
    
    # 排序后返回
    missing_files = sorted(missing_files, key=lambda x: x['file_path'])
    return missing_files

def create_csv_file(missing_files, output_file):
    """创建CSV文件保存缺失文件列表"""
    try:
        # 使用文件管理模块创建结构化输出路径
        from .file_manager import get_output_path
        csv_file = get_output_path(output_file, "csv")
        
        # 获取完整路径
        abs_csv_path = os.path.abspath(csv_file)
        
        # 合并相同文件名的条目（即使节点ID不同）
        merged_files = {}
        
        for missing in missing_files:
            file_path = missing['file_path']
            node_id = missing['node_id']
            node_type = missing['node_type']
            
            if file_path in merged_files:
                # 如果已存在，更新节点信息
                existing = merged_files[file_path]
                
                # 检查是否是新的节点类型
                if node_type != existing['node_type']:
                    # 合并节点ID和类型
                    existing['node_id'] = f"{existing['node_id']},{node_id}"
                    existing['node_type'] = f"{existing['node_type']},{node_type}"
                else:
                    # 类型相同，只合并ID
                    existing['node_id'] = f"{existing['node_id']},{node_id}"
            else:
                # 如果是新的文件路径，添加到字典
                merged_files[file_path] = {
                    'node_id': str(node_id),
                    'node_type': node_type,
                    'file_path': file_path
                }
        
        # 将合并后的字典转换为列表
        merged_list = list(merged_files.values())
        
        # 排序
        merged_list = sorted(merged_list, key=lambda x: x['file_path'])
        
        # 写入CSV文件
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['序号', '节点ID', '节点类型', '文件名', '状态', '下载链接', '镜像链接', '搜索链接']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for i, merged in enumerate(merged_list, 1):
                file_path = merged['file_path']
                # 检测是否包含中文，为中文模型生成搜索链接
                search_link = ''
                if contains_chinese(file_path):
                    search_link = f"https://www.bing.com/search?q=site:liblib.art+{file_path.replace(' ', '+')}"
                
                writer.writerow({
                    '序号': i,
                    '节点ID': merged['node_id'],
                    '节点类型': merged['node_type'],
                    '文件名': file_path,
                    '状态': '',
                    '下载链接': '',
                    '镜像链接': '',
                    '搜索链接': search_link
                })
        
        print(f"\nCSV文件已保存为: {abs_csv_path}")
        return csv_file
    except Exception as e:
        print(f"\n创建CSV文件时出错: {e}")
        traceback.print_exc()
        return None


def search_model_links(csv_file, status_callback=None, progress_callback=None):
    """使用Bing搜索引擎查找模型下载链接"""
    try:
        # 导入依赖库
        import pandas as pd
        from DrissionPage import ChromiumPage, ChromiumOptions
        from .utils import find_chrome_path

        # 读取CSV文件
        try:
            df = pd.read_csv(csv_file, encoding='utf-8')
        except Exception:
            df = pd.read_csv(csv_file, encoding='utf-8-sig')
        
        # 检查必要的列是否存在
        if '文件名' not in df.columns:
            print("错误: CSV文件必须包含'文件名'列")
            return False
        
        # 添加必要的列
        for col in ['下载链接', '镜像链接', '状态']:
            if col not in df.columns:
                print(f"添加缺失列: '{col}'")
                df[col] = ''
        
        # 添加搜索链接列
        if '搜索链接' not in df.columns:
            df['搜索链接'] = ''
        
        # 获取需要处理的关键词列表
        keywords = []
        for index, row in df.iterrows():
            keyword = row['文件名']
            if pd.isna(keyword) or keyword == '':
                continue
                
            # 检查是否已经处理过 - 修改这里的逻辑，只有当状态为'已处理'且有下载链接时才跳过
            if row['状态'] == '已处理' and not pd.isna(row['下载链接']) and row['下载链接'].strip() != '':
                print(f"跳过已处理的关键词: {keyword}")
                continue
                
            keywords.append(keyword)
        
        if not keywords:
            print("没有找到需要处理的关键词")
            return True
            
        print(f"找到 {len(keywords)} 个需要处理的关键词")
        
        # 创建浏览器配置
        print("正在准备浏览器配置...")
        chrome_options = ChromiumOptions()
        
        # 使用增强的Chrome路径检测
        chrome_path = find_chrome_path()
        if chrome_path:
            print(f"使用找到的Chrome浏览器: {chrome_path}")
            chrome_options.set_browser_path(chrome_path)
            
            # 获取Chrome用户数据目录
            chrome_dir = os.path.dirname(chrome_path)
            parent_dir = os.path.dirname(chrome_dir)
            if os.path.basename(chrome_dir) == 'Application':
                user_data_dir = os.path.join(parent_dir, 'User Data')
                if os.path.exists(user_data_dir):
                    print(f"使用Chrome用户数据目录: {user_data_dir}")
                    chrome_options.set_user_data_path(user_data_dir)
        
        # 配置其他浏览器参数
        chrome_options.set_argument('--disable-infobars')
        chrome_options.set_argument('--no-sandbox')
        
        # 创建浏览器实例
        page = None
        try:
            print("正在初始化浏览器...")
            page = ChromiumPage(chrome_options)
            
            # 处理每个关键词
            for i, keyword in enumerate(keywords):
                print(f"搜索模型 ({i+1}/{len(keywords)}): {keyword}")
                
                # 更新进度
                if progress_callback:
                    progress_callback(i+1, len(keywords))
                
                try:
                    # 根据关键词特点选择搜索引擎和查询
                    url, search_query = get_search_url(keyword)
                    
                    # 访问搜索引擎
                    page.get(url)
                    time.sleep(1)
                    
                    # 获取搜索框元素
                    search_box = page.ele("#sb_form_q")
                    
                    if search_box:
                        # 清空搜索框并输入新的搜索关键词
                        search_box.clear()
                        
                        # 输入搜索关键词
                        search_box.input(search_query)
                        time.sleep(1)
                        
                        # 提交搜索表单
                        page.run_js("document.querySelector('#sb_form').submit();")
                        time.sleep(2)
                        
                        # 尝试提取搜索结果
                        search_results = page.eles("xpath://*[@id='b_results']//h2/a")
                        
                        if search_results and len(search_results) > 0:
                            # 获取第一个搜索结果
                            first_result = search_results[0]
                            title = first_result.text
                            original_link = first_result.attr("href")
                            
                            print(f"找到搜索结果: {title}")
                            
                            # 根据关键词处理不同的搜索结果
                            row_idx = df.index[df['文件名'] == keyword].tolist()
                            if row_idx:
                                idx = row_idx[0]
                                
                                # 判断当前搜索的是中文还是国际资源
                                if contains_chinese(keyword):
                                    # 中文资源 - liblib.art
                                    if 'liblib.art' in original_link:
                                        # 直接使用第一个搜索结果的链接，而不是搜索链接
                                        # df.at[idx, '下载链接'] = original_link
                                        df.at[idx, '下载链接'] = ''  # 不在huggingface列显示liblib链接
                                        df.at[idx, '状态'] = '已处理'
                                        # 仍然保留搜索链接供用户手动查询
                                        search_link = f"https://www.bing.com/search?q=site:liblib.art+{keyword.replace(' ', '+')}"
                                        df.at[idx, '搜索链接'] = original_link  # 将liblib链接保存到liblib列
                                        
                                        print(f"成功: 找到liblib直接链接: {original_link}")
                                        
                                        # 确保用户知道有下载链接
                                        if status_callback:
                                            status_callback(f"找到模型: {keyword} → {original_link}")
                                    else:
                                        print(f"警告: 找到结果但不是liblib.art链接: {original_link}")
                                        df.at[idx, '状态'] = '未找到'
                                        # 仍然生成搜索链接
                                        search_link = f"https://www.bing.com/search?q=site:liblib.art+{keyword.replace(' ', '+')}"
                                        df.at[idx, '搜索链接'] = search_link
                                        
                                        if status_callback:
                                            status_callback(f"未找到liblib链接: {keyword}")
                                else:
                                    # 国际资源 - huggingface
                                    if 'huggingface.co' in original_link:
                                        # 在原链接中，如果是blob路径，转换为resolve路径用于下载
                                        if "/blob/" in original_link:
                                            download_link = original_link.replace("/blob/", "/resolve/")
                                        else:
                                            download_link = original_link
                                            
                                        # 构造镜像链接
                                        mirror_link = get_mirror_link(original_link)
                                        
                                        # 保存结果
                                        df.at[idx, '下载链接'] = download_link
                                        df.at[idx, '镜像链接'] = mirror_link
                                        df.at[idx, '状态'] = '已处理'
                                        
                                        print(f"生成下载链接: {download_link}")
                                        print(f"生成镜像链接: {mirror_link}")
                                    else:
                                        print(f"找到结果但不是Hugging Face链接")
                                        df.at[idx, '状态'] = '未找到'
                        else:
                            print(f"未找到搜索结果")
                            row_idx = df.index[df['文件名'] == keyword].tolist()
                            if row_idx:
                                idx = row_idx[0]
                                df.at[idx, '状态'] = '未找到'
                                
                                # 生成搜索链接，即使未找到结果
                                if contains_chinese(keyword):
                                    search_link = f"https://www.bing.com/search?q=site:liblib.art+{keyword.replace(' ', '+')}"
                                    df.at[idx, '搜索链接'] = search_link
                    else:
                        print(f"未找到搜索框")
                        row_idx = df.index[df['文件名'] == keyword].tolist()
                        if row_idx:
                            idx = row_idx[0]
                            df.at[idx, '状态'] = '处理错误'
                        
                except Exception as e:
                    print(f"处理关键词 {keyword} 时发生错误: {str(e)}")
                    
                    row_idx = df.index[df['文件名'] == keyword].tolist()
                    if row_idx:
                        idx = row_idx[0]
                        df.at[idx, '状态'] = '处理错误'
                
                # 每处理一个关键词保存一次进度
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                print(f"已保存当前进度 ({i+1}/{len(keywords)})")
                
                # 两次搜索之间增加等待时间
                time.sleep(1)
        
        finally:
            # 确保浏览器实例被关闭
            if page:
                try:
                    print("正在关闭浏览器...")
                    page.quit()
                except Exception as e:
                    print(f"关闭浏览器时出错: {str(e)}")
        
        # 创建HTML视图
        html_file = create_html_view(csv_file)
        if html_file:
            print(f"已生成HTML结果文件: {html_file}")
            return html_file
        
        return True
    
    except Exception as e:
        print(f"处理CSV文件时发生错误: {str(e)}")
        print("错误详情:")
        traceback.print_exc()
        return False


def batch_process_workflows(directory, file_pattern="*.json", progress_callback=None):
    """批量处理目录中的工作流文件"""
    import glob
    import json
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
    
    # 初始化变量，防止回调引用错误
    i = 0
    
    # 处理文件模式，支持多个模式
    patterns = file_pattern.split(';')
    all_workflow_files = []
    
    print(f"开始在 {directory} 搜索文件...")
    for pattern in patterns:
        pattern = pattern.strip()
        if pattern:
            # 使用glob查找匹配该模式的文件
            try:
                print(f"查找模式: {pattern}")
                files = glob.glob(os.path.join(directory, pattern))
                print(f"找到 {len(files)} 个匹配 {pattern} 的文件")
                all_workflow_files.extend(files)
            except Exception as e:
                print(f"搜索模式 {pattern} 时出错: {e}")
    
    # 过滤出只有JSON格式的文件
    workflow_files = []
    skipped_files = 0
    
    print(f"检查 {len(all_workflow_files)} 个文件是否为有效JSON...")
    
    def check_json_file(file_path):
        # 尝试读取文件并检查是否为JSON格式
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 只读取前10KB来验证是否为JSON
                content = f.read(10240)
                # 快速检查是否包含JSON特征
                if '{' in content and '}' in content:
                    # 进一步验证为完整JSON
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as full_f:
                        json.load(full_f)
                    return file_path, True
                return file_path, False
        except json.JSONDecodeError:
            return file_path, False
        except Exception as e:
            print(f"读取文件 {file_path} 时出错: {e}")
            return file_path, False
    
    # 使用线程池并行处理文件验证
    with ThreadPoolExecutor(max_workers=8) as executor:
        # 提交所有文件检查任务
        future_to_file = {executor.submit(check_json_file, file): file for file in all_workflow_files}
        
        # 收集结果
        for future in as_completed(future_to_file):
            file = future_to_file[future]
            try:
                result_file, is_valid = future.result(timeout=5)  # 5秒超时
                if is_valid:
                    workflow_files.append(result_file)
                else:
                    skipped_files += 1
            except TimeoutError:
                print(f"检查文件超时: {file}")
                skipped_files += 1
            except Exception as e:
                print(f"处理文件 {file} 时出错: {e}")
                skipped_files += 1
    
    print(f"验证结果: 有效JSON文件 {len(workflow_files)} 个, 跳过 {skipped_files} 个无效文件")
    
    if not workflow_files:
        print(f"在 {directory} 中没有找到匹配的工作流文件")
        return False
    
    # 按文件名排序
    workflow_files = sorted(workflow_files)
    
    print(f"找到 {len(workflow_files)} 个工作流文件")
    
    # 收集所有缺失文件信息（用于去重）
    all_missing_files = {}  # 使用字典来去重
    
    # 处理每个工作流文件
    results = []
    
    for i, workflow_file in enumerate(workflow_files):
        try:
            print(f"\n处理工作流 ({i+1}/{len(workflow_files)}): {os.path.basename(workflow_file)}")
            
            # 更新进度
            if progress_callback:
                progress_callback(i+1, len(workflow_files))
            
            # 为每个文件设置处理超时
            start_time = time.time()
            timeout = 30  # 单个文件处理最长30秒
            
            # 分析工作流
            try:
                missing_files = find_missing_models(workflow_file)
                
                # 检查超时
                if time.time() - start_time > timeout:
                    print(f"处理文件 {workflow_file} 超时，已跳过")
                    continue
                
                if missing_files:
                    # 记录到去重字典中
                    for file_info in missing_files:
                        file_path = file_info['file_path']
                        if file_path not in all_missing_files:
                            all_missing_files[file_path] = file_info
                    
                    # 创建CSV文件
                    output_file = os.path.basename(workflow_file)
                    csv_file = create_csv_file(missing_files, output_file)
                    
                    if csv_file:
                        results.append({
                            'workflow': workflow_file,
                            'csv': csv_file,
                            'missing_count': len(missing_files)
                        })
            except Exception as e:
                print(f"处理文件 {workflow_file} 时出错: {e}")
                import traceback
                traceback.print_exc()
        except Exception as e:
            print(f"处理循环中出错: {e}")
            continue
        
        # 每处理5个文件，显示一次进度汇总
        if (i+1) % 5 == 0 or i == len(workflow_files) - 1:
            print(f"已处理 {i+1}/{len(workflow_files)} 个文件, 找到 {len(all_missing_files)} 个缺失模型")
    
    # 创建一个汇总CSV文件，包含所有不重复的缺失文件
    if all_missing_files:
        try:
            # 使用结构化输出目录
            from .file_manager import create_output_directory
            output_dir = create_output_directory()
            summary_csv = os.path.join(output_dir, "汇总缺失文件.csv")
            
            with open(summary_csv, 'w', newline='', encoding='utf-8-sig') as f:
                # 使用与create_csv_file函数相同的列名
                fieldnames = ['序号', '节点ID', '节点类型', '文件名', '状态', '下载链接', '镜像链接', '搜索链接']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
        
                
                for i, (file_path, file_info) in enumerate(sorted(all_missing_files.items()), 1):
                    # 检测是否包含中文，为中文模型生成搜索链接
                    search_link = ''
                    if contains_chinese(file_path):
                        search_link = f"https://www.bing.com/search?q=site:liblib.art+{file_path.replace(' ', '+')}"
                    
                    writer.writerow({
                        '序号': i,
                        '节点ID': file_info.get('node_id', ''),
                        '节点类型': file_info.get('node_type', ''),
                        '文件名': file_path,
                        '状态': '',
                        '下载链接': '',
                        '镜像链接': '',
                        '搜索链接': search_link
                    })
            
            print(f"已创建汇总缺失文件CSV: {summary_csv}")
        except Exception as e:
            print(f"创建汇总CSV文件时出错: {e}")
    
    # 创建批量处理结果汇总
    if results:
        try:
            # 使用结构化输出目录
            from .file_manager import create_output_directory
            output_dir = create_output_directory()
            summary_file = os.path.join(output_dir, "批量处理结果.csv")

            with open(summary_file, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['工作流文件', 'CSV文件', '缺失数量']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                # 按文件名排序结果
                results = sorted(results, key=lambda x: x['workflow'])
                
                for result in results:
                    writer.writerow({
                        '工作流文件': os.path.basename(result['workflow']),
                        'CSV文件': os.path.basename(result['csv']),
                        '缺失数量': result['missing_count']
                    })
            
            print(f"\n批量处理完成，结果已保存至: {summary_file}")
            return summary_file
        except Exception as e:
            print(f"创建汇总文件时出错: {e}")
            return False
    else:
        print("\n批量处理完成，未发现缺失文件")
        return True