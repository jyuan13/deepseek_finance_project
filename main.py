#!/usr/bin/env python3
"""
DeepSeek金融分析系统 - 主程序入口
"""

import os
import sys
import importlib.util
import yfinance as yf

def check_dependencies():
    """检查必要的依赖库是否已安装"""
    required_packages = {
        'openai': 'OpenAI库',
        'pandas': 'Pandas数据处理',
        'numpy': 'NumPy数值计算',
        'yfinance': 'Yahoo财经数据',
        'talib': 'TA-Lib技术指标',
        'requests': 'HTTP请求库'
    }
    
    missing_packages = []
    for package, description in required_packages.items():
        try:
            if package == 'talib':
                import talib
            else:
                importlib.import_module(package)
            print(f"✓ {description} ({package})")
        except ImportError:
            missing_packages.append((package, description))
            print(f"✗ {description} ({package})")
    
    if missing_packages:
        print(f"\n❌ 缺少必要的依赖库:")
        for package, description in missing_packages:
            print(f"   - {description}: pip install {package}")
        print(f"\n💡 一键安装所有依赖: pip install -r requirements.txt")
        return False
    
    print(f"\n✅ 所有依赖库检查通过!")
    return True

def main():
    """主程序入口"""
    print("=" * 50)
    print("    DeepSeek金融分析系统")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        print("请先安装缺失的依赖库，然后重新运行程序。")
        sys.exit(1)
    
    # 检查API密钥
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("\n⚠ 未检测到DEEPSEEK_API_KEY环境变量")
        api_key = input("请输入你的DeepSeek API密钥: ").strip()
        if not api_key:
            print("❌ 必须提供API密钥才能运行程序")
            sys.exit(1)
    
    # 导入模块
    try:
        from deepseek_client import DeepSeekClient
        from finance_analyzer import FinancialAnalyzer
        from data_manager import DataManager
        from email_sender import EmailSender  # 新增导入
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("请确保所有.py文件都在同一目录下")
        sys.exit(1)
    
    # 初始化组件
    try:
        print("\n🔄 初始化系统组件...")
        
        # 初始化DeepSeek客户端
        deepseek_client = DeepSeekClient(
            api_key=api_key,
            conversation_dir="conversations"
        )
        
        # 初始化数据管理器
        data_manager = DataManager()
        
        # 初始化金融分析器（会自动初始化邮件发送器）
        finance_analyzer = FinancialAnalyzer(deepseek_client, data_manager)
        
        # 初始化独立的邮件发送器（用于主菜单）
        email_sender = EmailSender()
        
        print("✅ 系统初始化完成!")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        sys.exit(1)

    # 主菜单
    while True:
        print("\n" + "=" * 50)
        print("           主菜单")
        print("=" * 50)
        print("1. 💬 普通聊天模式")
        print("2. 📈 金融数据分析")
        print("3. 📊 查看对话历史")
        print("4. 🗂️  数据管理")
        print("5. 📧 邮件发送设置")  # 新增选项
        print("6. 🚪 退出程序")
        print("=" * 50)
        
        choice = input("请选择功能 (1-6): ").strip()
        
        if choice == "1":
            # 普通聊天模式
            print("\n💬 进入普通聊天模式...")
            deepseek_client.interactive_chat(
                model_type="chat",
                system_prompt="You are a helpful assistant that responds in Chinese"
            )
        
        elif choice == "2":
            # 金融数据分析模式
            print("\n📈 进入金融数据分析模式...")
            finance_analyzer.interactive_analysis()
        
        elif choice == "3":
            # 查看对话历史
            print("\n📊 对话历史管理")
            deepseek_client.show_conversation_list()
            if input("是否进入对话历史查看? (y/n): ").lower() == 'y':
                deepseek_client.interactive_chat()
        
        elif choice == "4":
            # 数据管理
            print("\n🗂️  数据管理")
            data_manager.manage_data()
        
        elif choice == "5":
            # 邮件发送设置
            print("\n📧 邮件发送设置")
            email_sender.setup_email_config()
        
        elif choice == "6":
            print("\n👋 感谢使用，再见!")
            break
        
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == "__main__":
    main()