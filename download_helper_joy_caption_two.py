import os
import shutil
import sys
from pathlib import Path

# 尝试导入tqdm，如果不存在则自动安装
try:
    from tqdm import tqdm
except ImportError:
    print("正在安装tqdm进度条库...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
    from tqdm import tqdm

# 尝试导入DrissionPage，如果不存在则自动安装
try:
    from DrissionPage import ChromiumPage
except ImportError:
    print("正在安装DrissionPage库...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "DrissionPage"])
    from DrissionPage import ChromiumPage

# 定义模型及其下载URL
MODELS = [
    {
        "name": "google/siglip-so400m-patch14-384",
        "foreign_url": "https://huggingface.co/google/siglip-so400m-patch14-384",
        "domestic_url": "https://hf-mirror.com/google/siglip-so400m-patch14-384",
        "target_path": "models/clip/siglip-so400m-patch14-384",
        "download_folder": "siglip-so400m-patch14-384"
    },
    {
        "name": "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
        "foreign_url": "https://huggingface.co/unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
        "domestic_url": "https://hf-mirror.com/unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
        "target_path": "models/LLM/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
        "download_folder": "Meta-Llama-3.1-8B-Instruct-bnb-4bit"
    },
    {
        "name": "unsloth/Meta-Llama-3.1-8B-Instruct",
        "foreign_url": "https://huggingface.co/unsloth/Meta-Llama-3.1-8B-Instruct",
        "domestic_url": "https://hf-mirror.com/unsloth/Meta-Llama-3.1-8B-Instruct",
        "target_path": "models/LLM/Meta-Llama-3.1-8B-Instruct",
        "download_folder": "Meta-Llama-3.1-8B-Instruct"
    },
    {
        "name": "Joy-Caption-alpha-two",
        "foreign_url": "https://huggingface.co/spaces/fancyfeast/joy-caption-alpha-two/tree/main/cgrkzexw-599808",
        "domestic_url": "https://huggingface.co/spaces/fancyfeast/joy-caption-alpha-two/tree/main/cgrkzexw-599808",
        "target_path": "models/Joy_caption_two",
        "download_folder": "joy-caption-alpha-two"
    }
]

def print_download_links():
    """打印所有模型的下载链接"""
    print("=== 模型下载链接 ===")
    print("请使用您喜欢的下载工具(如迅雷)下载以下模型:")
    print()
    
    print("模型名称：")
    for model in MODELS:
        print(f"{model['name']}")
    
    print("\nhuggingface链接:")
    for model in MODELS:
        print(f"{model['foreign_url']}")
    
    print("\nhf-mirror链接：")
    for model in MODELS:
        print(f"{model['domestic_url']}")
    
    print("\nComfyUI目标路径:")
    for model in MODELS:
        print(f"{model['target_path']}")
    
    print("\n下载完成后，使用此脚本将文件移动到正确位置。")
    print()

def get_dir_size(path):
    """计算目录中所有文件的总大小"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

def copy_with_progress(src, dst):
    """带进度条的文件复制"""
    file_size = os.path.getsize(src)
    with tqdm(total=file_size, unit='B', unit_scale=True, desc=f"复制 {os.path.basename(src)}") as pbar:
        with open(src, 'rb') as fsrc:
            with open(dst, 'wb') as fdst:
                copied = 0
                while True:
                    buf = fsrc.read(1024*1024)  # 1MB块
                    if not buf:
                        break
                    fdst.write(buf)
                    copied += len(buf)
                    pbar.update(len(buf))

def copy_tree_with_progress(src, dst):
    """带进度条的目录树复制"""
    if not os.path.exists(dst):
        os.makedirs(dst)
    
    items = os.listdir(src)
    for item in tqdm(items, desc=f"{os.path.basename(src)}中的文件"):
        src_item = os.path.join(src, item)
        dst_item = os.path.join(dst, item)
        
        if os.path.isdir(src_item):
            if os.path.exists(dst_item):
                shutil.rmtree(dst_item)
            print(f"复制目录: {item}")
            shutil.copytree(src_item, dst_item)
        else:
            # 对于大文件，显示单独的进度条
            if os.path.getsize(src_item) > 50 * 1024 * 1024:  # 50MB
                copy_with_progress(src_item, dst_item)
            else:
                shutil.copy2(src_item, dst_item)

def open_hf_mirror_links():
    """使用DrissionPage打开所有hf-mirror链接"""
    try:
        print("\n正在打开浏览器并加载hf-mirror链接...")
        
        # 创建浏览器页面对象
        page = ChromiumPage()
        
        # 打开第一个链接
        first_model = MODELS[0]
        print(f"打开第一个链接: {first_model['name']}")
        page.get(first_model['domestic_url'])
        
        # 为其余链接创建新标签页
        for model in MODELS[1:]:
            print(f"在新标签页中打开: {model['name']}")
            new_tab = page.new_tab()
            new_tab.get(model['domestic_url'])
        
        print("所有hf-mirror链接已在浏览器中打开。")
        print("您可以在浏览器中查看和下载模型文件。")
        
    except Exception as e:
        print(f"打开浏览器链接时出错: {e}")
        print("您可以手动复制以下链接到浏览器中:")
        for model in MODELS:
            print(f"  {model['domestic_url']}")

def move_model_files(download_path, comfyui_path):
    """将模型文件从下载位置移动到ComfyUI"""
    # 获取可用的模型（存在的目录）
    available_models = []
    for model in MODELS:
        source_dir = os.path.join(download_path, model["download_folder"])
        if os.path.exists(source_dir):
            available_models.append(model)
        else:
            print(f"警告: 源目录 {source_dir} 不存在，跳过...")
    
    if not available_models:
        print("在下载路径中没有找到模型目录。")
        return
    
    # 显示所有模型的进度
    for i, model in enumerate(available_models):
        source_dir = os.path.join(download_path, model["download_folder"])
        target_dir = os.path.join(comfyui_path, model["target_path"])
        
        # 如果目标目录不存在，创建它
        os.makedirs(target_dir, exist_ok=True)
        
        print(f"\n[{i+1}/{len(available_models)}] 移动 {model['name']} 文件")
        print(f"从: {source_dir}")
        print(f"到: {target_dir}")
        
        # 获取目录大小以便更好地报告进度
        dir_size = get_dir_size(source_dir)
        print(f"总大小: {dir_size / (1024*1024*1024):.2f} GB")
        
        # 使用进度条复制文件
        copy_tree_with_progress(source_dir, target_dir)
        
        print(f"成功移动 {model['name']} 到 {target_dir}")

def main():
    # 调试信息：显示所有命令行参数
    print(f"命令行参数数量: {len(sys.argv)}")
    print(f"命令行参数: {sys.argv}")
    
    # 检查是否有命令行参数传入ComfyUI路径
    comfyui_path = None
    
    # 方法1：从命令行参数获取
    if len(sys.argv) > 1:
        comfyui_path = sys.argv[1].strip('"\'')
        print(f"✓ 从命令行参数获取ComfyUI路径: {comfyui_path}")
    
    # 方法2：从环境变量获取
    elif 'COMFYUI_PATH' in os.environ:
        comfyui_path = os.environ['COMFYUI_PATH'].strip('"\'')
        print(f"✓ 从环境变量获取ComfyUI路径: {comfyui_path}")
    
    # 方法3：检查当前目录是否是ComfyUI目录
    elif os.path.exists('models') and os.path.exists('custom_nodes'):
        comfyui_path = os.getcwd()
        print(f"✓ 检测到当前目录是ComfyUI路径: {comfyui_path}")
    
    else:
        print("× 未从命令行或环境变量获取到ComfyUI路径")
    
    # 首先显示下载链接
    print_download_links()
    
    # 询问用户是否要继续移动文件
    proceed = input("是否继续移动下载的文件? (y/n): ").strip().lower()
    
    if proceed != 'y':
        print("退出。当您准备好移动文件时，可以再次运行此脚本。")
        return
    
    # 打开hf-mirror链接
    open_browser = input("是否在浏览器中打开hf-mirror下载链接? (y/n): ").strip().lower()
    if open_browser == 'y':
        open_hf_mirror_links()
        
        # 询问用户是否已完成下载
        download_complete = input("\n下载完成后，是否继续移动文件到ComfyUI目录? (y/n): ").strip().lower()
        if download_complete != 'y':
            print("您可以稍后再次运行此脚本来移动文件。")
            return
    
    # 从用户输入获取下载路径
    download_path = input("输入您下载模型文件的路径: ").strip()
    
    # 处理ComfyUI路径
    if comfyui_path is not None:
        print(f"✓ 使用自动检测的ComfyUI路径: {comfyui_path}")
        # 询问用户是否确认使用此路径
        confirm = input(f"是否使用此路径? (y/n): ").strip().lower()
        if confirm != 'y':
            comfyui_path = input("请输入正确的ComfyUI安装路径: ").strip()
            print(f"✓ 使用用户输入的ComfyUI路径: {comfyui_path}")
    else:
        comfyui_path = input("输入您的ComfyUI安装路径: ").strip()
        print(f"✓ 使用用户输入的ComfyUI路径: {comfyui_path}")
    
    # 如果用户复制了带引号的路径，去除引号
    download_path = download_path.strip('"\'')
    comfyui_path = comfyui_path.strip('"\'')
    
    # 验证路径是否存在
    if not os.path.exists(download_path):
        print(f"错误: 下载路径 {download_path} 不存在。")
        return
    
    if not os.path.exists(comfyui_path):
        print(f"错误: ComfyUI路径 {comfyui_path} 不存在。")
        return
    
    # 移动文件
    move_model_files(download_path, comfyui_path)
    print("所有文件已成功移动。")
    input("按回车键退出...")

if __name__ == "__main__":
    main() 