#!/usr/bin/env python3
"""
DeepSeek 金融分析系统 V5.0 - 主程序入口
集成 V5 趋势引擎、RAG 记忆、持仓管理、操作记录、系统维护
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
    print("    DeepSeek 金融分析系统 V5.0 (全天候趋势增强版)")
    print("    特性：影子净值 | 均线透视 | 盈亏感知 | RAG记忆")
    print("=" * 60)
    
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        api_key = input("请输入 DeepSeek API 密钥: ").strip()

    # 初始化核心组件
    client = DeepSeekClient(api_key=api_key)
    data_mgr = DataManager()
    port_mgr = PortfolioManager()
    op_logger = OperationLogger()
    email_sender = EmailSender()
    
    # V5 分析器初始化 (注入所有依赖)
    analyzer = FinancialAnalyzer(client, data_mgr, port_mgr, op_logger)

    while True:
        print("\n" + "="*30 + " 主菜单 " + "="*30)
        print("1. 🚀 智能金融分析 (V5 双轨引擎)")
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