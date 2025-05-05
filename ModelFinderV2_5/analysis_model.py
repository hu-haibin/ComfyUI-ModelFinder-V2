import os
import sys
import json
import time
import csv
import traceback
import re
import logging
import random

# Import utilities and file manager directly, as Model handles core logic
from .utils import get_mirror_link, create_html_view, find_chrome_path # Assuming utils are stable
from .file_manager import get_output_path # Model needs to know where to create files

# Dependencies for specific methods (import within method or at top)
try:
    import pandas as pd
except ImportError:
    pd = None # Handle missing dependency gracefully? Or let it fail? Let's assume it's installed.

try:
    from DrissionPage import ChromiumPage, ChromiumOptions
except ImportError:
    ChromiumPage = None # Handle missing dependency


logger = logging.getLogger(__name__)

class AnalysisModel:
    """
    Handles the core logic for analyzing workflows, finding models,
    creating CSVs, searching links, and batch processing.
    """

    def __init__(self):
        logger.info("AnalysisModel initialized.")
        # Pre-compile regex if used frequently
        self._chinese_char_pattern = re.compile(r'[\u4e00-\u9fff]')
        # Check heavy dependencies
        if pd is None:
            logger.error("Pandas library is not installed, search/batch functionality might be affected.")
        if ChromiumPage is None:
            logger.error("DrissionPage library is not installed, search functionality will not work.")

    def remove_chinese_prefix(self, filename):
        """
        Removes ONLY the Chinese prefix from a filename, if it exists at the beginning.
        Examples:
        "万相clip_vision_h.safetensors" -> "clip_vision_h.safetensors"
        "牛奶abc_def_pingguo.safetensors" -> "abc_def_pingguo.safetensors"
        "abc一二三def.safetensors" -> "abc一二三def.safetensors" (no change)
        "abcdef一二三.safetensors" -> "abcdef一二三.safetensors" (no change)
        """

        # 匹配以一个或多个中文字符开始的模式
        prefix_pattern = re.compile(r"^[\u4e00-\u9fa5]+")

        # 检查是否以中文开头
        if re.search(r"^[\u4e00-\u9fa5]", filename):
            # 移除中文前缀
            filename = re.sub(prefix_pattern, "", filename).strip()
            # 移除前导的分隔符
            filename = re.sub(r"^[-_|\s]+", "", filename).strip()

        return filename
    
    def _contains_chinese(self, text):
        """Detects if a string contains Chinese characters."""
        if not isinstance(text, str):
            return False
        return bool(self._chinese_char_pattern.search(text))

    def _get_search_url(self, keyword):
        """Generates different search URLs based on the keyword."""
        logger.debug(f"Generating search URL for keyword: {keyword}")
        if self._contains_chinese(keyword):
            logger.debug("Keyword contains Chinese, using liblib search.")
            # Using Bing as a proxy to search specific sites
            # Note: Web scraping search results can be unreliable. Consider dedicated APIs if possible.
            return f"https://www.bing.com/?setlang=en-US", f'site:liblib.art "{keyword}"'
        else:
            logger.debug("Keyword does not contain Chinese, using Hugging Face search.")
            return f"https://www.bing.com/?setlang=en-US", f'site:huggingface.co "{keyword}"'

    def find_missing_models(self, workflow_file):
        """Extracts missing model files from a workflow file."""
        logger.info(f"Analyzing workflow file: {workflow_file}")
        base_dir = os.path.dirname(os.path.abspath(workflow_file))
        missing_files_list = []

        try:
            with open(workflow_file, 'r', encoding='utf-8', errors='ignore') as f:
                max_file_size = 50 * 1024 * 1024
                file_size = os.path.getsize(workflow_file)
                if file_size > max_file_size:
                    logger.warning(f"File size ({file_size/1024/1024:.2f}MB) exceeds limit, may process slowly.")

                start_time = time.time()
                timeout = 10 # JSON load timeout
                try:
                    workflow_json = json.load(f)
                    elapsed_time = time.time() - start_time
                    logger.debug(f"JSON loaded in {elapsed_time:.2f} seconds.")
                    if elapsed_time > 5: logger.warning("JSON loading took longer than 5 seconds.")
                except Exception as e:
                     logger.error(f"JSON parsing failed for {workflow_file}", exc_info=True)
                     # Add more robust handling or return empty?
                     return [] # Return empty on JSON error

            if not isinstance(workflow_json, dict) or 'nodes' not in workflow_json:
                logger.error(f"Invalid workflow format: Root is not a dict or 'nodes' key missing in {workflow_file}")
                return []

            node_model_indices = {"default": [0], "SUPIR_Upscale": [0, 1]} # Simplified example
            model_extensions = ('.safetensors', '.pth', '.ckpt', '.pt', '.bin', '.onnx')

            model_node_types = [ "CheckpointLoader", 
                        "DiffControlNetLoader", 
                        "VAELoader",
                        "ModelLoader",
                        "GANLoader", 
                        "PulidEvaClipLoader",
                        "SUPIR_Upscale",
                        "WanVideoLoraSelect",
                        "DownloadAndLoadGIMMVFIModel",
                        "UpscaleModelLoader",
                        "Miaoshouai_Tagger",
                        "ACN_ControlNet++LoaderSingle",
                        "ADE_AnimateDiffLoaderWithContext",
                        "ADE_LoadAnimateDiffModel",
                        "ApplyStableSRUpscaler",
                        "AuraSR.AuraSRUpscaler",
                        "BrushNetLoader",
                        "CLIPLoader",
                        "CLIPVisionLoader",
                        "CheckpointLoaderSimple",
                        "ControlNetLoader",
                        "DepthAnythingPreprocessor",
                        "DownloadAndLoadGIMMVFIModel",
                        "DownloadAndLoadMochiModel",
                        "DualCLIPLoader",
                        "DynamiCrafterModelLoader",
                        "EcomID_PulidModelLoader",
                        "Eff. Loader SDXL",
                        "Efficient Loader",
                        "FaceRestoreModelLoader",   
                        "FantasyTalkingModelLoader",
                        "FluxLoraLoader",
                        "FluxTrainModelSelect",     
                        "HyVideoLoraSelect",
                        "HyVideoModelLoader",
                        "HyVideoVAELoader",
                        "INPAINT_LoadFooocusInpaint",
                        "IPAdapterSD3Loader",
                        "ImageOnlyCheckpointLoader",
                        "InstantIDModelLoader",
                        "LoadAndApplyICLightUnet",
                        "LoadFluxIPAdapter",
                        "LoadICLightUnetDiffusers",
                        "LoadWanVideoClipTextEncoder",
                        "LoadWanVideoT5TextEncoder",
                        "LoraLoader",
                        "MZ_ChatGLM3Loader",
                        "MZ_IPAdapterModelLoaderKolors",
                        "MZ_KolorsUNETLoader",
                        "MZ_KolorsUNETLoaderV2",
                        "MochiVAEEncoderLoader",
                        "PhotoMakerLoaderPlus",
                        "PowerPaintCLIPLoader",
                        "PulidFluxModelLoader",
                        "PulidModelLoader",
                        "RIFE VFI",
                        "ReActorFaceSwap",
                        "SAMLoader",
                        "SONICTLoader",
                        "StyleModelLoader",
                        "TripleCLIPLoader",
                        "UNETLoader",
                        "UltralyticsDetectorProvider",
                        "UpscaleModelLoader",
                        "WanVideoLoraSelect",
                        "WanVideoModelLoader",
                        "WanVideoVAELoader",]  # 添加了 DiffusionModelLoaderKJ
           

            file_references = []
            nodes = workflow_json.get('nodes', [])
            max_nodes = 1000
            if len(nodes) > max_nodes:
                 logger.warning(f"Node count ({len(nodes)}) exceeds limit {max_nodes}, processing first {max_nodes}.")
                 nodes = nodes[:max_nodes]

            start_time = time.time()
            processed_nodes = 0
            node_processing_timeout = 20 # Timeout for processing all nodes

            for node in nodes:
                processed_nodes += 1
                if processed_nodes % 50 == 0 and (time.time() - start_time) > node_processing_timeout:
                     logger.warning(f"Node processing timed out after {node_processing_timeout}s ({processed_nodes}/{len(nodes)} processed).")
                     break

                try: # Add try-except for individual node processing
                    node_id = node.get('id')
                    node_type = node.get('type', '')
                    widgets_values = node.get('widgets_values', [])
                    properties = node.get('properties', {})
                    property_node_name = properties.get('Node name for S&R', '')

                    if property_node_name and property_node_name in model_node_types: node_type = property_node_name
                    is_model_node = node_type in model_node_types or "Loader" in node_type
                    if not is_model_node or not widgets_values: continue

                    indices_to_check = node_model_indices.get(node_type, node_model_indices["default"])

                    for index in indices_to_check:
                        if len(widgets_values) > index and isinstance(widgets_values[index], str):
                            value = widgets_values[index].strip()
                            if not value or '\n' in value or '\r' in value: continue
                            if value.lower() in ["default", "none", "empty", "auto", "off", "on"]: continue
                            filename = os.path.basename(value.replace('\\', '/')) if '\\' in value or '/' in value else value
                            file_references.append({'node_id': node_id, 'node_type': node_type, 'file_path': filename})
                except Exception as node_e:
                     logger.error(f"Error processing node ID {node.get('id', 'N/A')}", exc_info=True)


            logger.debug(f"Node processing complete in {time.time() - start_time:.2f}s. Found {len(file_references)} potential references.")
            if not file_references: return []

            # Check file existence (simplified logic)
            file_existence_cache = {}
            for ref in file_references:
                try:
                    file_path = ref['file_path']
                    name, ext = os.path.splitext(file_path)
                    # Basic check, assuming ComfyUI handles subdirs correctly internally if not found directly
                    # A more robust check would involve searching known model directories.
                    # Let's assume if a direct path isn't found, it's missing for this tool's purpose.
                    if file_path in file_existence_cache:
                        if not file_existence_cache[file_path]: # If known missing
                            missing_files_list.append(ref)
                        continue # Skip if already checked

                    exists = os.path.exists(file_path) or os.path.exists(os.path.join(base_dir, file_path))
                    # Check with common extensions if original had none
                    if not exists and not ext:
                         for model_ext in model_extensions:
                             if os.path.exists(f"{file_path}{model_ext}") or os.path.exists(os.path.join(base_dir, f"{file_path}{model_ext}")):
                                 exists = True
                                 break

                    file_existence_cache[file_path] = exists # Cache result
                    if not exists:
                        logger.debug(f"Missing file identified: {file_path}")
                        missing_files_list.append(ref)
                except Exception as check_e:
                    logger.error(f"Error checking existence for file '{ref.get('file_path', 'unknown')}'", exc_info=True)

        except MemoryError:
            logger.critical("MemoryError loading workflow file.", exc_info=True)
            # Maybe raise a specific exception for controller to catch?
            raise # Re-raise for now
        except Exception as e:
            logger.error(f"Error during find_missing_models for {workflow_file}", exc_info=True)
            raise # Re-raise for controller to handle

        if missing_files_list:
            logger.info(f"Found {len(missing_files_list)} missing files for {workflow_file}")
            # Sort results for consistent output
            missing_files_list = sorted(missing_files_list, key=lambda x: x['file_path'])
        else:
            logger.info(f"No missing files found for {workflow_file}")

        return missing_files_list

    def create_csv_file(self, missing_files, output_basename):
        """Creates a CSV file listing missing files."""
        logger.info(f"Creating CSV for {len(missing_files)} missing files (output base: {output_basename}).")
        if not missing_files:
            logger.warning("create_csv_file called with empty list, returning None.")
            return None
        try:
            csv_file_path = get_output_path(output_basename, "csv") # Use file_manager utility
            abs_csv_path = os.path.abspath(csv_file_path)
            logger.debug(f"Target CSV path: {abs_csv_path}")

            merged_files = {}
            for missing in missing_files:
                file_path = missing['file_path']
                node_id = missing['node_id']
                node_type = missing['node_type']
                if file_path in merged_files:
                    existing = merged_files[file_path]
                    existing['node_id'] = f"{existing['node_id']},{node_id}"
                    if node_type != existing['node_type']: # Append type only if different
                        existing['node_type'] = f"{existing['node_type']},{node_type}"
                else:
                    merged_files[file_path] = {'node_id': str(node_id), 'node_type': node_type, 'file_path': file_path}

            merged_list = sorted(list(merged_files.values()), key=lambda x: x['file_path'])

            with open(csv_file_path, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['序号', '节点ID', '节点类型', '文件名', '状态', '下载链接', '镜像链接', '搜索链接']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for i, merged in enumerate(merged_list, 1):
                    file_path = merged['file_path']
                    # Generate appropriate search link based on name
                    search_link = ''
                    base_search_url, site_query = self._get_search_url(file_path)
                    # Construct a direct search query URL (simple approach)
                    # Note: Bing URL format might change. URL encoding might be needed.
                    query_param = site_query.replace(' ', '+').replace('"', '%22')
                    search_link = f"https://www.bing.com/search?q={query_param}"

                    writer.writerow({
                        '序号': i, '节点ID': merged['node_id'], '节点类型': merged['node_type'],
                        '文件名': file_path, '状态': '', '下载链接': '', '镜像链接': '',
                        '搜索链接': search_link # Store generated search link
                    })

            logger.info(f"CSV file successfully saved to: {abs_csv_path}")
            return csv_file_path
        except Exception as e:
            logger.error(f"Error creating CSV file for {output_basename}", exc_info=True)
            return None
        

    def search_model_links(self, csv_file, progress_callback=None):
        """Searches model download links using Bing and DrissionPage."""
        logger.info(f"Starting model link search for CSV: {csv_file}")
        if pd is None or ChromiumPage is None:
             logger.error("Search cannot proceed: Missing pandas or DrissionPage library.")
             return False # Indicate failure due to missing dependency

        try:
            # --- 修改开始: 读取 CSV 并处理数据类型 ---
            logger.debug(f"Attempting to read CSV with specified string dtypes: {csv_file}")

            # 1. 定义需要确保为字符串类型的列
            string_columns = ['状态', '下载链接', '镜像链接', '搜索链接']
            # 2. 创建 dtype 字典，告诉 Pandas 这些列应该是字符串
            col_dtypes = {col: str for col in string_columns}

            try:
                # 3. 尝试用两种编码读取 CSV，同时传入 dtype 和处理空值的参数
                try:
                    df = pd.read_csv(csv_file, encoding='utf-8', dtype=col_dtypes, keep_default_na=False, na_values=[''])
                except Exception:
                    df = pd.read_csv(csv_file, encoding='utf-8-sig', dtype=col_dtypes, keep_default_na=False, na_values=[''])

                logger.debug(f"Successfully read CSV: {csv_file}, Shape: {df.shape}, Dtypes:\n{df.dtypes}")

                # 4. 确保所有必需的列存在，并再次强制转换类型/填充NaN为空字符串
                required_cols = ['文件名', '状态', '下载链接', '镜像链接', '搜索链接']
                for col in required_cols:
                    if col not in df.columns:
                        logger.warning(f"CSV missing required column '{col}', adding it.")
                        df[col] = '' # 添加新列时初始化为空字符串
                    else:
                        # 对明确需要是字符串的列，再次进行处理以防万一
                        if col in string_columns:
                            # fillna('') 确保没有 NaN 值, astype(str) 强制转换为字符串
                            df[col] = df[col].fillna('').astype(str)
                            # logger.debug(f"Column '{col}' processed: filled NaN, type enforced to string.")

            except Exception as read_e:
                 logger.error(f"Critical error reading or processing CSV file {csv_file}", exc_info=True)
                 return False # 如果读取或初步处理失败，则提前返回 False
            # --- 修改结束 ---

            # --- 原有逻辑: 准备要搜索的关键词列表 (基本不变) ---
            keywords_to_search = []
            indices_to_update = [] # Store indices corresponding to keywords
            for index, row in df.iterrows():
                 # 使用 .get() 并提供默认值，增加对列可能不存在的鲁棒性
                keyword = row.get('文件名', '')
                status = str(row.get('状态', '')) # 确保状态是字符串
                link = str(row.get('下载链接', '')) # 确保链接是字符串
                liblib_link = str(row.get('搜索链接', '')) # 确保链接是字符串

                if pd.isna(keyword) or keyword == '': continue

                is_processed = (status == '已处理')
                has_hf_link = link.strip() != ''
                # 检查 liblib 链接是否是有效的 URL (以 http 开头)
                has_liblib_link = liblib_link.strip().startswith('http')

                if is_processed and (has_hf_link or has_liblib_link):
                    logger.debug(f"Skipping already processed keyword: {keyword}")
                    continue

                # 在这里添加：处理中文前缀
                keyword = self.remove_chinese_prefix(keyword)
                logger.debug(f"Processed keyword: {keyword}")
                
                keywords_to_search.append(keyword)
                indices_to_update.append(index) # Keep track of the original df index

            if not keywords_to_search:
                logger.info("No keywords require searching in this CSV.")
                # 【注意】: 如果没有关键词需要搜索，原代码是返回 True。但此时可能仍需要生成HTML（显示所有都是已处理状态）
                # 因此，我们应该继续执行到 HTML 生成步骤，而不是直接返回 True。
                # 所以，这里的 return True 需要移除或注释掉，让流程继续。
                # return True # <--- 注释掉或者删除这一行
                pass # 让代码继续往下执行到浏览器设置和HTML生成部分
            else:
                 logger.info(f"Found {len(keywords_to_search)} keywords to search.")

            # --- Browser Setup ---
            logger.debug("Configuring browser options...")
            chrome_options = ChromiumOptions()
            chrome_path = find_chrome_path()
            if chrome_path:
                logger.info(f"Using Chrome browser at: {chrome_path}")
                chrome_options.set_browser_path(chrome_path)
                # Try setting user data path automatically (less reliable, might need manual config)
                try:
                    chrome_dir = os.path.dirname(chrome_path)
                    parent_dir = os.path.dirname(chrome_dir)
                    if os.path.basename(chrome_dir) == 'Application':
                        user_data_dir = os.path.join(parent_dir, 'User Data')
                        if os.path.exists(user_data_dir):
                             logger.debug(f"Attempting to use Chrome user data dir: {user_data_dir}")
                             chrome_options.set_user_data_path(user_data_dir)
                except Exception as path_e:
                    logger.warning(f"Could not auto-set user data path: {path_e}")
            else:
                 logger.error("Chrome browser not found. Cannot perform search.")
                 return False # Cannot proceed without browser

            chrome_options.set_argument('--disable-infobars')
            chrome_options.set_argument('--no-sandbox')
            chrome_options.set_argument('--start-maximized')
            # chrome_options.set_argument('--headless') # Run headless for background operation
            logger.debug("Browser options configured.")

            page = None
            try:
                logger.info("Initializing browser page...")
                page = ChromiumPage(chrome_options)
                logger.info("Browser page initialized.")

                total_keywords = len(keywords_to_search)
                for i, (keyword, df_index) in enumerate(zip(keywords_to_search, indices_to_update)):
                    logger.info(f"Searching ({i+1}/{total_keywords}): {keyword}")
                    if progress_callback: progress_callback(i+1, total_keywords)

                    search_url, search_query = self._get_search_url(keyword)
                    logger.debug(f"Navigating to {search_url} with query '{search_query}'")

                    try:
                        page.get(search_url, timeout=15) # Increased timeout
                        time.sleep(random.uniform(0.5, 1.5)) # Small random delay

                        search_box = page.ele("#sb_form_q", timeout=10)
                        if not search_box:
                             logger.warning(f"Could not find search box for keyword '{keyword}'. Skipping.")
                             df.loc[df_index, '状态'] = '搜索错误'
                             continue

                        search_box.clear()
                        search_box.input(search_query)
                        time.sleep(random.uniform(0.5, 1.0))
                        page.ele('#search_icon',timeout=5).click() # Click search button explicitly
                        # page.run_js("document.querySelector('#sb_form').submit();") # JS submit can be less reliable

                        page.wait.load_start(timeout=15) # Wait for page load after submit

                        # --- Extract results ---
                        # Use more robust selectors, wait for results container
                        results_container = page.ele('#b_results', timeout=10)
                        if not results_container:
                             logger.warning(f"Search results container not found for '{keyword}'.")
                             df.loc[df_index, '状态'] = '未找到'
                             continue

                        # Find first result link within the container
                        first_link_ele = results_container.ele("xpath:.//h2/a") # Relative xpath
                        if first_link_ele:
                            title = first_link_ele.text
                            original_link = first_link_ele.attr("href")
                            logger.info(f"Found result for '{keyword}': {title} -> {original_link}")

                            # Process link based on keyword type
                            if self._contains_chinese(keyword): # Expecting LibLib
                                if original_link and 'liblib.art' in original_link:
                                    logger.debug("Found LibLib link.")
                                    df.loc[df_index, '下载链接'] = '' # Clear HF column
                                    df.loc[df_index, '镜像链接'] = ''
                                    df.loc[df_index, '搜索链接'] = original_link # Store LibLib link here
                                    df.loc[df_index, '状态'] = '已处理'
                                else:
                                    logger.warning(f"Found result for Chinese keyword, but not a liblib.art link: {original_link}")
                                    df.loc[df_index, '状态'] = '未找到LibLib'
                                    # Keep the generated search link in '搜索链接' column
                            else: # Expecting Hugging Face
                                if original_link and 'huggingface.co' in original_link:
                                    logger.debug("Found Hugging Face link.")
                                    # Convert blob to resolve for download link
                                    download_link = original_link.replace("/blob/", "/resolve/") if "/blob/" in original_link else original_link
                                    mirror_link = get_mirror_link(original_link) # Use util function
                                    logger.debug(f"Generated links: Download={download_link}, Mirror={mirror_link}")
                                    df.loc[df_index, '下载链接'] = download_link
                                    df.loc[df_index, '镜像链接'] = mirror_link
                                    df.loc[df_index, '搜索链接'] = '' # Clear LibLib column
                                    df.loc[df_index, '状态'] = '已处理'
                                else:
                                     logger.warning(f"Found result for non-Chinese keyword, but not a huggingface.co link: {original_link}")
                                     df.loc[df_index, '状态'] = '未找到HF'
                                     # Keep the generated search link in '搜索链接' column
                        else:
                            logger.warning(f"No result links found (h2/a) for '{keyword}'.")
                            df.loc[df_index, '状态'] = '未找到'

                    except Exception as search_exc:
                        logger.error(f"Error during search or result processing for '{keyword}'", exc_info=True)
                        df.loc[df_index, '状态'] = '搜索错误'
                    finally:
                        # Save progress after each keyword attempt
                        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                        logger.debug(f"Saved progress after keyword '{keyword}' ({i+1}/{total_keywords})")
                        time.sleep(random.uniform(1.0, 2.5)) # Longer delay between searches

            finally:
                if page:
                    try:
                        logger.info("Closing browser page...")
                        page.quit()
                    except Exception as quit_e:
                        logger.error("Error closing browser page", exc_info=True)

            # --- Final Steps ---
            # Save final DataFrame state
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            logger.info(f"Final CSV saved: {csv_file}")

            # Create HTML view
            html_file = create_html_view(csv_file) # Use util function
            if html_file:
                logger.info(f"HTML view generated: {html_file}")
                return html_file
            else:
                 logger.error(f"Failed to generate HTML view for {csv_file}")
                 return True # Indicate search completed but HTML failed

        except Exception as e:
            logger.error(f"Critical error processing CSV file {csv_file}", exc_info=True)
            return False # Indicate failure
        
    def batch_process_workflows(self, directory, file_pattern="*.json", progress_callback=None):
        """Processes all workflow files in a directory."""
        logger.info(f"Starting batch process for directory: {directory}, pattern: {file_pattern}")
        import glob # Keep glob import here as it's specific to batch processing
        # ThreadPoolExecutor might be overkill for file checking, simple loop is fine
        # from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

        patterns = file_pattern.split(';')
        all_files = []
        for pattern in patterns:
            pattern = pattern.strip()
            if pattern:
                 try:
                     logger.debug(f"Globbing pattern: {os.path.join(directory, pattern)}")
                     files = glob.glob(os.path.join(directory, pattern))
                     all_files.extend(files)
                     logger.debug(f"Found {len(files)} files for pattern '{pattern}'. Total now: {len(all_files)}")
                 except Exception as glob_e:
                      logger.error(f"Error during globbing for pattern '{pattern}'", exc_info=True)

        if not all_files:
             logger.warning(f"No files found matching patterns in directory: {directory}")
             return False # Indicate no files found

        logger.info(f"Found {len(all_files)} potential files. Filtering for valid JSON workflows...")
        workflow_files = []
        skipped_files = 0
        json_check_timeout = 5 # Timeout for checking if a file is JSON

        for file_path in all_files:
            start_check = time.time()
            is_json = False
            try:
                 # Quick check: file extension (optional, but can speed up)
                 # if not file_path.lower().endswith('.json'): continue

                 # Check file size first?
                 # if os.path.getsize(file_path) > large_threshold: continue

                 # Try to load JSON (robust check)
                 with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                     json.load(f)
                 is_json = True
                 workflow_files.append(file_path)
                 logger.debug(f"Valid JSON workflow found: {file_path}")

            except json.JSONDecodeError:
                logger.debug(f"Skipping non-JSON file: {file_path}")
                skipped_files += 1
            except Exception as check_e:
                 logger.warning(f"Error checking file {file_path}, skipping.", exc_info=True)
                 skipped_files += 1
            finally:
                 if time.time() - start_check > json_check_timeout:
                     logger.warning(f"JSON check for {file_path} timed out after {json_check_timeout}s.")
                     if is_json: workflow_files.pop() # Remove if added but timed out overall
                     skipped_files += 1


        logger.info(f"JSON filtering complete. Valid workflows: {len(workflow_files)}, Skipped: {skipped_files}")
        if not workflow_files: return True # Indicate processing done, but no valid files

        workflow_files = sorted(workflow_files) # Process in consistent order
        results = []
        all_missing_files_dict = {} # Use dict for deduplication across files
        total_files = len(workflow_files)
        single_file_timeout = 30 # Timeout for processing a single workflow

        for i, wf_file in enumerate(workflow_files):
            if progress_callback: progress_callback(i + 1, total_files)
            logger.info(f"Processing batch file ({i+1}/{total_files}): {os.path.basename(wf_file)}")
            start_wf_time = time.time()
            try:
                # Call own find_missing_models method
                missing = self.find_missing_models(wf_file)

                if time.time() - start_wf_time > single_file_timeout:
                    logger.warning(f"Processing timed out for workflow: {wf_file}")
                    continue # Skip to next file

                if missing:
                    # Call own create_csv_file method
                    csv_file = self.create_csv_file(missing, os.path.basename(wf_file))
                    if csv_file:
                         results.append({'workflow': wf_file, 'csv': csv_file, 'missing_count': len(missing)})
                         # Add unique missing files to the overall dictionary
                         for item in missing:
                             if item['file_path'] not in all_missing_files_dict:
                                 all_missing_files_dict[item['file_path']] = item
                    else:
                         logger.error(f"Failed to create individual CSV for {wf_file}")

            except Exception as proc_e:
                 logger.error(f"Error processing workflow file {wf_file}", exc_info=True)
                 # Continue with next file

        # --- Create Summary Files ---
        summary_csv_path = None
        batch_results_csv_path = None

        # Create "汇总缺失文件.csv" if any missing files were found overall
        if all_missing_files_dict:
             logger.info(f"Found {len(all_missing_files_dict)} unique missing files across all workflows.")
             # Convert dict back to list for create_csv_file
             all_missing_list = list(all_missing_files_dict.values())
             summary_csv_path = self.create_csv_file(all_missing_list, "汇总缺失文件") # Use own method
             if not summary_csv_path: logger.error("Failed to create summary missing files CSV.")
        else:
             logger.info("No missing files found in any processed workflow.")


        # Create "批量处理结果.csv" if any individual CSVs were successfully created
        if results:
             logger.info(f"Creating batch results summary for {len(results)} workflows with missing files.")
             try:
                 batch_results_csv_path = get_output_path("批量处理结果", "csv") # Use file_manager util
                 abs_batch_path = os.path.abspath(batch_results_csv_path)
                 logger.debug(f"Batch results CSV path: {abs_batch_path}")

                 results = sorted(results, key=lambda x: x['workflow']) # Sort final results
                 with open(batch_results_csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                      fieldnames = ['工作流文件', 'CSV文件', '缺失数量']
                      writer = csv.DictWriter(f, fieldnames=fieldnames)
                      writer.writeheader()
                      for result in results:
                           writer.writerow({
                               '工作流文件': os.path.basename(result['workflow']),
                               'CSV文件': os.path.basename(result['csv']),
                               '缺失数量': result['missing_count']
                           })
                 logger.info(f"Batch results summary saved to: {abs_batch_path}")
             except Exception as batch_csv_e:
                  logger.error("Error creating batch results summary CSV", exc_info=True)
                  batch_results_csv_path = None # Mark as failed
        else:
             logger.info("No individual workflow results to summarize in batch results CSV.")


        logger.info("Batch processing finished.")
        # Return the path to the batch results summary, or True if no missing files found anywhere
        if not all_missing_files_dict:
             return True
        else:
             return batch_results_csv_path if batch_results_csv_path else False # Return path or False if summary failed