#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试批量处理功能
"""

import os
import sys
import traceback
import time

def main():
    try:
        # 添加当前目录到搜索路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        print("=" * 50)
        print("开始测试批量处理功能")
        print("=" * 50)
        
        from model_finder.core import batch_process_workflows
        
        # 要处理的目录
        test_directory = r"C:/Users/huhaibin/Desktop/商业中文工作流"
        
        # 设置开始时间
        start_time = time.time()
        
        # 执行批量处理
        print(f"处理目录: {test_directory}")
        result = batch_process_workflows(test_directory, "*.json;*")
        
        # 计算总处理时间
        elapsed_time = time.time() - start_time
        print(f"\n总处理时间: {elapsed_time:.2f}秒")
        
        # 检查结果
        if result:
            print("批量处理成功完成")
            if isinstance(result, str):
                print(f"结果文件: {result}")
        else:
            print("批量处理失败或未找到匹配的文件")
        
    except Exception as e:
        print(f"测试过程中出错: {e}")
        traceback.print_exc()
    
    print("\n按任意键退出...")
    input()

if __name__ == "__main__":
    main() 