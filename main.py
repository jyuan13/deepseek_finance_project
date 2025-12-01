#!/usr/bin/env python3
"""
DeepSeek Finance Project V2 (Qwen/DeepSeek 双引擎版) - 主程序入口
已增强为优先支持 Qwen API (具备深度思考能力)
"""

import os
from deepseek_client import DeepSeekClient
from data_manager import DataManager
from portfolio_manager import PortfolioManager
from operation_logger import OperationLogger
from finance_analyzer import FinancialAnalyzer
from email_sender import EmailSender

def main():
    print("=" * 60)
    print("    智能金融分析系统 V5.0 (Qwen/DeepSeek 双引擎增强版)")
    print("    特性：深度思考(Qwen) | 影子净值 | 均线透视 | RAG记忆")
    print("=" * 60)
    
    # 1. 智能检测 API Key，优先使用 Qwen
    qwen_key = os.environ.get("Qwen_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    
    api_key = None
    provider = "qwen"  # 默认首选
    
    if qwen_key:
        print("✅ 检测到 Qwen API Key，正在激活 Qwen-Plus 思考模式...")
        api_key = qwen_key
        provider = "qwen"
    elif deepseek_key:
        print("✅ 检测到 DeepSeek API Key，正在激活 DeepSeek 引擎...")
        api_key = deepseek_key
        provider = "deepseek"
    else:
        print("⚠️  未检测到环境变量中的 API Key")
        provider_input = input("请选择提供商 [1] Qwen (默认) / [2] DeepSeek: ").strip()
        if provider_input == "2":
            provider = "deepseek"
            api_key = input("请输入 DeepSeek API Key: ").strip()
        else:
            provider = "qwen"
            api_key = input("请输入 Qwen (DashScope) API Key: ").strip()

    # 初始化核心组件
    try:
        client = DeepSeekClient(api_key=api_key, provider=provider)
        # 测试连接提示
        print(f"🚀 已连接到 {provider.upper()} 服务 (Model: {client.models['chat']})")
    except Exception as e:
        print(f"❌ 客户端初始化失败: {e}")
        return

    data_mgr = DataManager()
    port_mgr = PortfolioManager()
    op_logger = OperationLogger()
    email_sender = EmailSender()
    
    # V5 分析器初始化 (注入所有依赖)
    analyzer = FinancialAnalyzer(client, data_mgr, port_mgr, op_logger)

    while True:
        print("\n" + "="*30 + f" 主菜单 ({provider.upper()}) " + "="*30)
        print("1. 🚀 智能金融分析 (深度思考模式)")
        print("2. 💼 投资组合管理 (持仓/现金)")
        print("3. 📝 记录交易操作 (买入/卖出)")
        print("4. 🧠 RAG 记忆库管理 (研报/观点)")
        print("5. 📧 邮件通知配置")
        print("-" * 66)
        print("99. 🧹 系统重置 (清除所有数据)")
        print("0.  退出")
        print("=" * 66)
        
        choice = input("请选择: ").strip()
        
        if choice == "1":
            # 进入分析菜单
            analyzer.run_analysis_menu()
        elif choice == "2":
            port_mgr.manage_portfolio()
        elif choice == "3":
            op_logger.quick_log_operation()
        elif choice == "4":
            analyzer.manage_rag_system()
        elif choice == "5":
            email_sender.setup_email_config()
        elif choice == "99":
            analyzer.perform_system_reset()
        elif choice == "0":
            print("👋 再见！祝您投资顺利！")
            break
        else:
            print("❌ 无效输入，请重试")

if __name__ == "__main__":
    main()