"""
Core function module
Contains core functions such as detecting missing model files and finding download links
"""

import os
import sys
import json
import time
import csv
import traceback
import re
from .utils import get_mirror_link, create_html_view
from .licensing import license_manager, LICENSE_VALID, MEMBERSHIP_FREE, MEMBERSHIP_BASIC, MEMBERSHIP_PRO

def contains_chinese(text):
    """Check if the string contains Chinese characters"""
    if not isinstance(text, str):
        return False
    # Use Unicode range to detect Chinese characters
    pattern = re.compile(r'[\u4e00-\u9fff]')
    return bool(pattern.search(text))

def get_search_url(keyword):
    """Generate different search URLs based on keyword characteristics"""
    if contains_chinese(keyword):
        # Use liblib.art search for Chinese model names
        return f"https://www.bing.com/?setlang=en-US", f'site:liblib.art \"{keyword}\"'
    else:
        # Use huggingface search for non-Chinese names
        return f"https://www.bing.com/?setlang=en-US", f'site:huggingface.co \"{keyword}\"'

def find_missing_models(workflow_file):
    """Extract missing model files from the workflow file"""

    # License check
    can_use, reason = license_manager.can_use_feature("single_analysis", credits_cost=2)
    if not can_use:
        if reason == "Use Credits": # Check for specific reason code
            print("Analyzing using credits...")
            if not license_manager.use_credits(2):
                print("Credit deduction failed, analysis cannot proceed")
                return [], "Insufficient credits"
        else:
            print(f"Cannot perform analysis: {reason}")
            print("Please upgrade membership or acquire more credits.")
            return [], reason
    
    # Record usage
    license_manager.record_usage("single_analysis")

    print(f"Analyzing workflow file: {workflow_file}")
    
    # Get the directory of the workflow file
    base_dir = os.path.dirname(os.path.abspath(workflow_file))
    
    # Load workflow JSON
    try:
        with open(workflow_file, 'r', encoding='utf-8', errors='ignore') as f:
            # Set file size limit (50MB)
            max_file_size = 50 * 1024 * 1024
            file_size = os.path.getsize(workflow_file)
            
            if file_size > max_file_size:
                print(f"Warning: File size ({file_size/1024/1024:.2f}MB) exceeds limit, processing may be slow")
            
            # Load JSON with timeout
            start_time = time.time()
            timeout = 10  # 10 second timeout
            
            try:
                workflow_json = json.load(f)
                elapsed_time = time.time() - start_time
                print(f"JSON loading time: {elapsed_time:.2f} seconds")
                
                if elapsed_time > 5:
                    print("Warning: Long JSON loading time, possibly a complex workflow")
            except Exception as e:
                print(f"JSON parsing failed: {e}")
                # Try reading JSON line by line to identify the issue
                print("Attempting to read JSON line by line...")
                f.seek(0)
                for i, line in enumerate(f):
                    if i % 10000 == 0:
                        print(f"Read {i} lines")
                        # Check timeout
                        if time.time() - start_time > timeout:
                            print("JSON reading timed out, aborting processing")
                            return [], "JSON reading timed out"
                
                return [], "JSON reading timed out"
    except MemoryError:
        print("Insufficient memory to load the workflow file")
        return [], "Insufficient memory"
    except Exception as e:
        print(f"Error loading workflow file: {e}")
        return [], f"Error loading workflow file: {e}"
    
    # Check workflow JSON format
    if not isinstance(workflow_json, dict):
        print(f"Incorrect workflow file format: Root object is not a dictionary")
        return [], "Incorrect workflow file format"
    
    # Find file references
    file_references = []
    model_extensions = ('.safetensors', '.pth', '.ckpt', '.pt', '.bin', '.onnx')
    
    # Model-related node types - based on common ComfyUI model loading nodes
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
    
    # Limit the number of nodes to avoid excessive processing time
    max_nodes = 1000
    nodes = workflow_json.get('nodes', [])
    
    if len(nodes) > max_nodes:
        print(f"Warning: Node count ({len(nodes)}) exceeds limit, only processing the first {max_nodes} nodes")
        nodes = nodes[:max_nodes]
    
    # Process all nodes
    start_time = time.time()
    processed_nodes = 0
    
    try:
        # Process all nodes
        for node in nodes:
            processed_nodes += 1
            
            # Check timeout every 50 processed nodes
            if processed_nodes % 50 == 0:
                elapsed = time.time() - start_time
                if elapsed > 20:  # 20 second timeout
                    print(f"Node processing timed out, processed {processed_nodes}/{len(nodes)} nodes")
                    break
            
            node_id = node.get('id')
            node_type = node.get('type', '')
            widgets_values = node.get('widgets_values', [])
            
            # Get node properties
            properties = node.get('properties', {})
            property_node_name = properties.get('Node name for S&R', '')
            
            # If properties contain a model-related node name, use it as the node type
            if property_node_name and property_node_name in model_node_types:
                node_type = property_node_name
            
            # Check if it is a model node type (using ComfyUI's heuristic method)
            is_model_node = node_type in model_node_types or "Loader" in node_type
            
            # If not a model node, skip
            if not is_model_node:
                continue
                
            # Skip empty widgets_values
            if not widgets_values:
                continue
            
            # In ComfyUI, the model file is usually the first parameter
            # Check if the first widgets_value could be a model file
            if len(widgets_values) > 0 and isinstance(widgets_values[0], str):
                value = widgets_values[0].strip()
                
                # Skip empty strings
                if not value:
                    continue
                
                # Skip strings containing newlines (filenames don't have newlines)
                if '\\n' in value or '\\r' in value:
                    continue
                
                # Exclude some common non-model option values
                common_non_model_options = ["default", "none", "empty", "auto", "off", "on"]
                if value.lower() in common_non_model_options:
                    continue
                    
                # Extract filename (remove path)
                if '\\\\' in value or '/' in value:
                    value = os.path.basename(value.replace('\\\\', '/'))
                
                # Add to reference list
                file_references.append({
                    'node_id': node_id,
                    'node_type': node_type,
                    'file_path': value
                })
    except Exception as e:
        print(f"Error processing nodes: {e}")
        traceback.print_exc()
    
    print(f"Node processing completed, time taken: {time.time() - start_time:.2f} seconds")
    
    if not file_references:
        print("No file references found in the workflow.")
        return [], "No file references found"
    
    print(f"Found {len(file_references)} model file references in the workflow.")
    
    # Check if files exist - using ComfyUI's logic
    missing_files = []
    
    # Cache results of file existence checks for efficiency
    file_existence_cache = {}
    
    for ref in file_references:
        try:
            file_path = ref['file_path']
            name, ext = os.path.splitext(file_path)
            
            # Handle different path formats
            paths_to_check = [file_path, os.path.join(base_dir, file_path)]
            
            # If no extension, add all possible extensions
            if not ext:
                for model_ext in model_extensions:
                    paths_to_check.append(f"{file_path}{model_ext}")
                    paths_to_check.append(os.path.join(base_dir, f"{file_path}{model_ext}"))
            
            # Check if the file exists in any possible path
            file_exists = False
            for p in paths_to_check:
                if p in file_existence_cache:
                    # Use cached result
                    if file_existence_cache[p]:
                        file_exists = True
                        break
                else:
                    # Check and cache result
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
            print(f"Error checking existence of file {ref.get('file_path', 'unknown')}: {e}")
    
    if not missing_files:
        print("\\nAll referenced files exist!")
        return [], "All files exist"
    
    # Count missing files
    print(f"\\nTotal missing model files: {len(missing_files)}")
    
    # Print list of missing files
    print("\\nMissing file list:")
    print("-" * 50)
    for i, missing in enumerate(missing_files, 1):
        print(f"{i}. {missing['file_path']}")
    
    # Return sorted list
    missing_files = sorted(missing_files, key=lambda x: x['file_path'])
    return missing_files, "Success"

def create_csv_file(missing_files, output_file, filename_prefix="Missing_Models_"):
    """Create a CSV file to save the list of missing files."""
    try:
        # Use file manager module to create structured output path
        from .file_manager import get_output_path
        # Use the prefix for the output filename
        csv_file = get_output_path(output_file, "csv", prefix=filename_prefix)
        
        # Get the absolute path
        abs_csv_path = os.path.abspath(csv_file)
        
        # Merge entries with the same file name (even if node IDs differ)
        merged_files = {}
        
        for missing in missing_files:
            file_path = missing['file_path']
            node_id = missing['node_id']
            node_type = missing['node_type']
            
            if file_path in merged_files:
                # If exists, update node information
                existing = merged_files[file_path]
                
                # Check if it's a new node type
                if node_type != existing['node_type']:
                    # Merge node ID and type
                    existing['node_id'] = f"{existing['node_id']},{node_id}"
                    existing['node_type'] = f"{existing['node_type']},{node_type}"
                else:
                    # Same type, only merge ID
                    existing['node_id'] = f"{existing['node_id']},{node_id}"
            else:
                # If it's a new file path, add to dictionary
                merged_files[file_path] = {
                    'node_id': str(node_id),
                    'node_type': node_type,
                    'file_path': file_path
                }
        
        # Convert merged dictionary to list
        merged_list = list(merged_files.values())
        
        # Sort
        merged_list = sorted(merged_list, key=lambda x: x['file_path'])
        
        # Write to CSV file
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            # Use English field names
            fieldnames = ['No', 'Node ID', 'Node Type', 'File Name', 'Status', 'Download Link', 'Mirror Link', 'Search Link']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for i, merged in enumerate(merged_list, 1):
                file_path = merged['file_path']
                # Removed Chinese check and specific LibLib search link generation
                search_link = '' # Placeholder or generic search can be added here if needed
                                
                writer.writerow({
                    'No': i,
                    'Node ID': merged['node_id'],
                    'Node Type': merged['node_type'],
                    'File Name': file_path,
                    'Status': '', # Initial status is empty
                    'Download Link': '',
                    'Mirror Link': '',
                    'Search Link': search_link
                })
        
        print(f"\\nCSV file saved as: {abs_csv_path}")
        return csv_file
    except Exception as e:
        print(f"\\nError creating CSV file: {e}")
        traceback.print_exc()
        return None


def search_model_links(csv_file, status_callback=None, progress_callback=None):
    """Use Bing search engine to find model download links"""
    try:
        # Import dependencies
        import pandas as pd
        from DrissionPage import ChromiumPage, ChromiumOptions
        from .utils import find_chrome_path

        # Read CSV file
        try:
            # Changed column name to English
            df = pd.read_csv(csv_file, encoding='utf-8')
        except Exception:
            # Changed column name to English
            df = pd.read_csv(csv_file, encoding='utf-8-sig')
        
        # Check if necessary columns exist (using English names)
        if 'File Name' not in df.columns:
            print("Error: CSV file must contain 'File Name' column")
            return False
        
        # Add necessary columns (using English names)
        for col in ['Download Link', 'Mirror Link', 'Status']:
            if col not in df.columns:
                print(f"Adding missing column: '{col}'")
                df[col] = ''
        
        # Add search link column (using English name)
        if 'Search Link' not in df.columns:
            df['Search Link'] = ''
        
        # Get list of keywords to process
        keywords = []
        # Use English column name
        for index, row in df.iterrows():
            keyword = row['File Name']
            if pd.isna(keyword) or keyword == '':
                continue
                
            # Check if already processed - modified logic, skip only if status is 'Processed' and download link exists
            # Use English column names
            if row['Status'] == 'Processed' and not pd.isna(row['Download Link']) and row['Download Link'].strip() != '':
                print(f"Skipping processed keyword: {keyword}")
                continue
                
            keywords.append(keyword)
        
        if not keywords:
            print("No keywords found to process")
            return True
            
        print(f"Found {len(keywords)} keywords to process")
        
        # Create browser configuration
        print("Preparing browser configuration...")
        chrome_options = ChromiumOptions()
        
        # Use enhanced Chrome path detection
        chrome_path = find_chrome_path()
        if chrome_path:
            print(f"Using detected Chrome browser: {chrome_path}")
            chrome_options.set_browser_path(chrome_path)
            
            # Get Chrome user data directory
            chrome_dir = os.path.dirname(chrome_path)
            parent_dir = os.path.dirname(chrome_dir)
            if os.path.basename(chrome_dir) == 'Application':
                user_data_dir = os.path.join(parent_dir, 'User Data')
                if os.path.exists(user_data_dir):
                    print(f"Using Chrome user data directory: {user_data_dir}")
                    chrome_options.set_user_data_path(user_data_dir)
        
        # Configure other browser arguments
        chrome_options.set_argument('--disable-infobars')
        chrome_options.set_argument('--no-sandbox')
        
        # Create browser instance
        page = None
        try:
            print("Initializing browser...")
            page = ChromiumPage(chrome_options)
            
            # Process each keyword
            for i, keyword in enumerate(keywords):
                print(f"Searching model ({i+1}/{len(keywords)}): {keyword}")
                
                # Update progress
                if progress_callback:
                    progress_callback(i+1, len(keywords))
                
                try:
                    # Select search engine and query based on keyword characteristics
                    url, search_query = get_search_url(keyword)
                    
                    # Visit search engine
                    page.get(url)
                    time.sleep(1)
                    
                    # Get search box element
                    search_box = page.ele("#sb_form_q")
                    
                    if search_box:
                        # Clear search box and input new search keyword
                        search_box.clear()
                        
                        # Input search keyword
                        search_box.input(search_query)
                        time.sleep(1)
                        
                        # Submit search form
                        page.run_js("document.querySelector('#sb_form').submit();")
                        time.sleep(1)
                        
                        # Try to extract search results
                        search_results = page.eles("xpath://*[@id='b_results']//h2/a")
                        
                        if search_results and len(search_results) > 0:
                            # Get the first search result
                            first_result = search_results[0]
                            title = first_result.text
                            original_link = first_result.attr("href")
                            
                            print(f"Found search result: {title}")
                            
                            # Process different search results based on keyword
                            # Use English column name
                            row_idx = df.index[df['File Name'] == keyword].tolist()
                            if row_idx and len(row_idx) > 0:  # Ensure the index list is not empty
                                idx = row_idx[0]  # Get the first matching index as integer
                                
                                # Determine if searching for Chinese or international resource
                                if contains_chinese(keyword):
                                    # Chinese resource - liblib.art
                                    if 'liblib.art' in original_link:
                                        # Use the link from the first search result directly, not the search link
                                        # Use English column names
                                        df.at[idx, 'Download Link'] = ''  # Do not show liblib link in the huggingface column
                                        df.at[idx, 'Status'] = 'Processed'
                                        # Still keep the search link for user manual lookup
                                        search_link = f"https://www.bing.com/search?q=site:liblib.art+{keyword.replace(' ', '+')}"
                                        df.at[idx, 'Search Link'] = original_link  # Save liblib link to liblib column (or Search Link)
                                        
                                        print(f"Success: Found direct liblib link: {original_link}")
                                        
                                        # Ensure user knows there's a download link
                                        if status_callback:
                                            status_callback(f"Found model: {keyword} → {original_link}")
                                    else:
                                        print(f"Warning: Found result but not a liblib.art link: {original_link}")
                                        # Use English column names
                                        df.at[idx, 'Status'] = 'Not Found'
                                        # Still generate search link
                                        search_link = f"https://www.bing.com/search?q=site:liblib.art+{keyword.replace(' ', '+')}"
                                        df.at[idx, 'Search Link'] = search_link
                                        
                                        if status_callback:
                                            status_callback(f"Liblib link not found: {keyword}")
                                else:
                                    # International resource - huggingface
                                    if 'huggingface.co' in original_link:
                                        # In original link, if it's a blob path, convert to resolve path for download
                                        if "/blob/" in original_link:
                                            download_link = original_link.replace("/blob/", "/resolve/")
                                        else:
                                            download_link = original_link
                                            
                                        # Construct mirror link
                                        mirror_link = get_mirror_link(original_link)
                                        
                                        # Save result (using English column names)
                                        df.at[idx, 'Download Link'] = download_link
                                        df.at[idx, 'Mirror Link'] = mirror_link
                                        df.at[idx, 'Status'] = 'Processed'
                                        
                                        print(f"Generated download link: {download_link}")
                                        print(f"Generated mirror link: {mirror_link}")
                                    else:
                                        print(f"Found result but not a Hugging Face link")
                                        # Use English column name
                                        df.at[idx, 'Status'] = 'Not Found'
                        else:
                            print(f"No search results found")
                            # Use English column name
                            row_idx = df.index[df['File Name'] == keyword].tolist()
                            if row_idx and len(row_idx) > 0:
                                idx = row_idx[0]
                                df.at[idx, 'Status'] = 'Not Found'
                                
                                # Generate search link even if no result found
                                if contains_chinese(keyword):
                                    search_link = f"https://www.bing.com/search?q=site:liblib.art+{keyword.replace(' ', '+')}"
                                    # Use English column name
                                    df.at[idx, 'Search Link'] = search_link
                    else:
                        print(f"Search box not found")
                        # Use English column name
                        row_idx = df.index[df['File Name'] == keyword].tolist()
                        if row_idx and len(row_idx) > 0:
                            idx = row_idx[0]
                            df.at[idx, 'Status'] = 'Processing Error'
                        
                except Exception as e:
                    print(f"Error processing keyword {keyword}: {str(e)}")
                    
                    # Use English column name
                    row_idx = df.index[df['File Name'] == keyword].tolist()
                    if row_idx and len(row_idx) > 0:
                        idx = row_idx[0]
                        df.at[idx, 'Status'] = 'Processing Error'
                
                # Save progress after processing each keyword
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                print(f"Saved current progress ({i+1}/{len(keywords)})")
                
                # Add wait time between two searches
                # time.sleep(1)
        
        finally:
            # Ensure browser instance is closed
            if page:
                try:
                    print("Closing browser...")
                    page.quit()
                except Exception as e:
                    print(f"Error closing browser: {str(e)}")
        
        # Create HTML view
        html_file = create_html_view(csv_file)
        if html_file:
            print(f"Generated HTML result file: {html_file}")
            return html_file
        else:
            print("Warning: Failed to generate HTML result file")
            # Return CSV file path even if HTML generation fails, for subsequent processing
            return csv_file
    
    except Exception as e:
        print(f"Error processing CSV file: {str(e)}")
        print("Error details:")
        traceback.print_exc()
        return False

def batch_process_workflows(directory, file_pattern="*.json;*", progress_callback=None, specific_files=None): # Added specific_files parameter
    """Batch process workflow files in a directory"""
    # License check
    can_use, reason = license_manager.can_use_feature("batch_analysis", credits_cost=5)
    if not can_use:
        if reason == "Use Credits": # Check specific reason code
            print("Performing batch analysis using credits...")
            if not license_manager.use_credits(5):
                print("Credit deduction failed, cannot perform batch analysis")
                return False, "Insufficient credits"
        else:
            print(f"Cannot perform batch analysis: {reason}")
            print("Please upgrade membership or acquire more credits.")
            return False, reason
    
    # Record usage
    license_manager.record_usage("batch_analysis")

    import glob
    import json
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
    
    # Initialize variables to prevent callback reference errors
    i = 0
    
    all_workflow_files = []
    if specific_files is not None:
        # Use the provided list of specific files
        print(f"Processing {len(specific_files)} specific workflow files provided.")
        all_workflow_files = specific_files
    else:
        # Handle file pattern, supporting multiple patterns
        patterns = file_pattern.split(';')
        print(f"Starting file search in {directory}...")
        for pattern in patterns:
            pattern = pattern.strip()
            if pattern:
                # Use glob to find files matching the pattern
                try:
                    print(f"Searching pattern: {pattern}")
                    files = glob.glob(os.path.join(directory, pattern))
                    print(f"Found {len(files)} files matching {pattern}")
                    all_workflow_files.extend(files)
                except Exception as e:
                    print(f"Error searching pattern {pattern}: {e}")

    # Filter out only JSON format files (this check might be redundant if specific_files were already pre-validated)
    workflow_files = []
    skipped_files = 0
    
    print(f"Checking {len(all_workflow_files)} files for valid JSON format...")
    
    def check_json_file(file_path):
        # Try reading the file and check if it's JSON format
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Only read the first 10KB to verify if it's JSON
                content = f.read(10240)
                # Quick check for JSON characteristics
                if '{' in content and '}' in content:
                    # Further verify as complete JSON
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as full_f:
                        json.load(full_f)
                    return file_path, True
                return file_path, False
        except json.JSONDecodeError:
            return file_path, False
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return file_path, False
    
    # Use ThreadPool to process file validation in parallel
    with ThreadPoolExecutor(max_workers=8) as executor:
        # Submit all file check tasks
        future_to_file = {executor.submit(check_json_file, file): file for file in all_workflow_files}
        
        # Collect results
        for future in as_completed(future_to_file):
            file = future_to_file[future]
            try:
                result_file, is_valid = future.result(timeout=5)  # 5 second timeout
                if is_valid:
                    workflow_files.append(result_file)
                else:
                    skipped_files += 1
            except TimeoutError:
                print(f"File check timed out: {file}")
                skipped_files += 1
            except Exception as e:
                print(f"Error processing file {file}: {e}")
                skipped_files += 1
    
    print(f"Validation result: {len(workflow_files)} valid JSON files, skipped {skipped_files} invalid files")
    
    if not workflow_files:
        print(f"No matching workflow files found in {directory}")
        return False, "No matching workflow files found"
    
    # Sort by filename
    workflow_files = sorted(workflow_files)
    
    print(f"Found {len(workflow_files)} workflow files to process")
    
    # Collect all missing file information (for deduplication)
    all_missing_files = {}  # Use dictionary for deduplication
    individual_results = [] # Store results for each file
    
    # Process each workflow file
    results = [] # This seems redundant, individual_results is used
    
    for i, workflow_file in enumerate(workflow_files):
        try:
            print(f"\\nProcessing workflow ({i+1}/{len(workflow_files)}): {os.path.basename(workflow_file)}")
            
            # Update progress
            if progress_callback:
                progress_callback(i+1, len(workflow_files))
            
            # Set processing timeout for each file
            start_time = time.time()
            timeout = 30  # Max 30 seconds per file
            
            # Analyze workflow
            try:
                missing_files, status = find_missing_models(workflow_file)
                
                # Check timeout
                if time.time() - start_time > timeout:
                    print(f"Processing file {workflow_file} timed out, skipped")
                    continue
                
                current_file_results = {
                    'workflow': workflow_file,
                    'missing_count': 0,
                    'csv': None,
                    'status': status
                }

                if missing_files:
                    # Add to deduplication dictionary
                    for file_info in missing_files:
                        file_path = file_info['file_path']
                        if file_path not in all_missing_files:
                            all_missing_files[file_path] = file_info
                    
                    # Create CSV file (using English prefix)
                    output_file = os.path.basename(workflow_file)
                    csv_file = create_csv_file(missing_files, output_file, filename_prefix="Missing_Models_")
                    
                    if csv_file:
                        current_file_results['csv'] = csv_file
                        current_file_results['missing_count'] = len(missing_files)
                
                # Add individual result regardless of missing files
                individual_results.append(current_file_results)

            except Exception as e:
                print(f"Error processing file {workflow_file}: {e}")
                import traceback
                traceback.print_exc()
        except Exception as e:
            print(f"Error in processing loop: {e}")
            continue
        
        # Display progress summary every 5 files or at the end
        if (i+1) % 5 == 0 or i == len(workflow_files) - 1:
            print(f"Processed {i+1}/{len(workflow_files)} files, found {len(all_missing_files)} unique missing models")
    
    # Create a summary CSV file containing all unique missing files
    summary_csv = None
    if all_missing_files:
        try:
            # Use structured output directory
            from .file_manager import create_output_directory
            output_dir = create_output_directory()
            # Use English filename
            summary_csv = os.path.join(output_dir, "Summary_Missing_Files.csv")
            
            with open(summary_csv, 'w', newline='', encoding='utf-8-sig') as f:
                # Use the same English column names as create_csv_file
                fieldnames = ['No', 'Node ID', 'Node Type', 'File Name', 'Status', 'Download Link', 'Mirror Link', 'Search Link']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
        
                
                for i, (file_path, file_info) in enumerate(sorted(all_missing_files.items()), 1):
                    # Check if contains Chinese to generate search link for Chinese models
                    search_link = ''
                    if contains_chinese(file_path):
                        search_link = f"https://www.bing.com/search?q=site:liblib.art+{file_path.replace(' ', '+')}"
                    
                    writer.writerow({
                        'No': i, # Use English 'No'
                        'Node ID': file_info.get('node_id', ''),
                        'Node Type': file_info.get('node_type', ''),
                        'File Name': file_path, # Use English 'File Name'
                        'Status': '', # Use English 'Status'
                        'Download Link': '', # Use English 'Download Link'
                        'Mirror Link': '', # Use English 'Mirror Link'
                        'Search Link': search_link # Use English 'Search Link'
                    })
            
            print(f"Created summary missing files CSV: {summary_csv}")
        except Exception as e:
            print(f"Error creating summary CSV file: {e}")
            summary_csv = None # Ensure summary_csv is None if creation failed

    # Create batch processing results summary (using English filename)
    batch_summary_file = None
    if individual_results: # Use individual_results which is populated correctly
        try:
            # Use structured output directory
            from .file_manager import create_output_directory
            output_dir = create_output_directory()
            # Use English filename
            batch_summary_file = os.path.join(output_dir, "Batch_Processing_Results.csv")

            with open(batch_summary_file, 'w', newline='', encoding='utf-8-sig') as f:
                # Use English field names
                fieldnames = ['Workflow File', 'CSV File', 'Missing Count', 'Status']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                # Sort results by filename
                individual_results = sorted(individual_results, key=lambda x: x['workflow'])
                
                for result in individual_results:
                    csv_basename = os.path.basename(result['csv']) if result['csv'] else ''
                    writer.writerow({
                        'Workflow File': os.path.basename(result['workflow']),
                        'CSV File': csv_basename,
                        'Missing Count': result['missing_count'],
                        'Status': result.get('status', '')
                    })
            
            print(f"\\nBatch processing completed, results saved to: {batch_summary_file}")
            
            # Return a dictionary containing status, summary and individual results
            return True, {
                "summary_csv": summary_csv,
                "batch_summary_csv": batch_summary_file,
                "results": individual_results
            }
        except Exception as e:
            print(f"Error creating batch summary file: {e}")
            # Return False or a partial result if summary fails
            return True, {
                "summary_csv": summary_csv, # May exist even if batch summary fails
                "batch_summary_csv": None,
                "results": individual_results # Results are still useful
            }
            
    else:
        print("\\nBatch processing completed, no missing files found or no valid workflows processed.")
         # Return a result indicating completion but no findings
        return True, {
            "summary_csv": None,
            "batch_summary_csv": None,
            "results": []
        }