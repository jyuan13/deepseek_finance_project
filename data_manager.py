import os
import pandas as pd
import json
from datetime import datetime

class DataManager:
    def __init__(self, data_dir="financial_data"):
        self.data_dir = data_dir
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
    
    def list_saved_data(self):
        """列出已保存的数据文件"""
        data_files = []
        for file in os.listdir(self.data_dir):
            if file.endswith('.csv') or file.endswith('.json'):
                data_files.append(file)
        return data_files
    
    def save_data(self, data, filename, format='csv'):
        """保存数据到文件"""
        filepath = os.path.join(self.data_dir, f"{filename}.{format}")
        try:
            if format == 'csv':
                data.to_csv(filepath)
            elif format == 'json':
                data.to_json(filepath, orient='records')
            print(f"✅ 数据已保存到: {filepath}")
            return True
        except Exception as e:
            print(f"❌ 保存数据失败: {e}")
            return False
    
    def load_data(self, filename):
        """从文件加载数据"""
        filepath = os.path.join(self.data_dir, filename)
        try:
            if filename.endswith('.csv'):
                return pd.read_csv(filepath, index_col=0, parse_dates=True)
            elif filename.endswith('.json'):
                return pd.read_json(filepath, orient='records')
        except Exception as e:
            print(f"❌ 加载数据失败: {e}")
            return None
    
    def manage_data(self):
        """数据管理交互界面"""
        print("\n🗂️  数据管理")
        print("=" * 40)
        
        while True:
            print("\n1. 查看已保存的数据")
            print("2. 删除数据文件") 
            print("3. 清理缓存数据")
            print("0. 返回主菜单")
            print("-" * 40)
            
            choice = input("请选择操作: ").strip()
            
            if choice == "1":
                files = self.list_saved_data()
                if files:
                    print("\n已保存的数据文件:")
                    for i, file in enumerate(files, 1):
                        print(f"{i}. {file}")
                else:
                    print("❌ 没有找到数据文件")
            
            elif choice == "2":
                files = self.list_saved_data()
                if files:
                    print("\n选择要删除的文件:")
                    for i, file in enumerate(files, 1):
                        print(f"{i}. {file}")
                    
                    try:
                        file_choice = int(input("请输入文件编号: ")) - 1
                        if 0 <= file_choice < len(files):
                            file_to_delete = os.path.join(self.data_dir, files[file_choice])
                            os.remove(file_to_delete)
                            print(f"✅ 已删除: {files[file_choice]}")
                        else:
                            print("❌ 无效的选择")
                    except (ValueError, IndexError):
                        print("❌ 请输入有效的编号")
                else:
                    print("❌ 没有可删除的文件")
            
            elif choice == "3":
                # 清理30天前的缓存文件
                print("清理功能开发中...")
            
            elif choice == "0":
                break
            
            else:
                print("❌ 无效的选择")