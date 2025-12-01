# deepseek_finance_project_V2/finance_analyzer.py

import json
from datetime import datetime
import pandas as pd
from fund_data_manager import FundDataManager
from technical_engine import TechnicalEngine
from prompt_builder import PromptBuilder
from sentiment_engine import SentimentEngine
from financial_brain import FinancialBrainRAG
from strategy_evolution import StrategyEvolutionEngine
from macro_analyzer import MacroAnalyzer

class FinancialAnalyzer:
    def __init__(self, deepseek_client, data_manager, portfolio_manager, operation_analyzer):
        self.client = deepseek_client
        self.data_manager = data_manager
        self.portfolio_manager = portfolio_manager
        self.operation_analyzer = operation_analyzer
        
        # --- V5 核心组件 ---
        self.fund_data_manager = FundDataManager()
        self.tech_engine = TechnicalEngine()
        self.macro_analyzer = MacroAnalyzer()
        
        # --- 智能认知组件 ---
        self.sentiment_engine = SentimentEngine()
        self.rag_engine = FinancialBrainRAG(persist_directory="./brain_memory")
        
        self.evolution_engine = StrategyEvolutionEngine(
            db_path='financial_memory.db', 
            deepseek_client=deepseek_client
        )
        
        self.prompt_builder = PromptBuilder(self.sentiment_engine, self.rag_engine)
        
        self.indices_config = {
            'Nasdaq': '^IXIC', 'China_A50': '000016.SH', 'Gold': 'GC=F'
        }

    def run_analysis_menu(self):
        print("\n🚀 V5 智能金融分析引擎 (全天候完全体)")
        print("=" * 45)
        while True:
            print("\n1. 💰 持仓基金深度透视 (Portfolio X-Ray)")
            print("2. 🔍 任意标的自由透视 (Free Style Analysis)")
            print("3. 📊 核心指数与宏观扫描 (Macro Pulse) - [开发中]")
            print("0. 返回主菜单")
            
            choice = input("请选择功能 (0-3): ").strip()
            if choice == "1":
                self._analyze_portfolio_funds()
            elif choice == "2":
                self._analyze_free_target()
            elif choice == "3":
                print("🚧 宏观扫描板块正在升级中...")
            elif choice == "0":
                break

    def _ask_debug_mode(self):
        ans = input("是否开启调试模式(查看Prompt和原始数据)? (y/n): ").lower()
        return ans == 'y'

    def _analyze_portfolio_funds(self):
        """分析持仓中的所有基金"""
        positions = self.portfolio_manager.get_current_positions()
        if not positions:
            print("⚠️ 当前无持仓配置")
            return
        
        debug = self._ask_debug_mode()

        print("🌍 正在扫描宏观环境 (美债/A50/纳指)...")
        try:
            macro_data = self.macro_analyzer.analyze_indices_trend(self.indices_config)
            macro_liquidity = self.macro_analyzer.analyze_macro_liquidity()
            macro_context = {**macro_data, "US_10Y": macro_liquidity.get("us_10y")}
        except Exception as e:
            print(f"⚠️ 宏观数据获取失败: {e}，将使用默认值")
            macro_context = {}

        for pos in positions:
            self._analyze_fund_trend(
                fund_code=pos['symbol'],
                user_cost=pos.get('cost_price', 0),
                macro_context=macro_context,
                debug=debug
            )

    def _analyze_free_target(self):
        """分析任意输入的基金代码"""
        code = input("请输入基金代码 (如 513120.SS 或 000001): ").strip()
        if not code: return
        
        debug = self._ask_debug_mode()
        
        print("🌍 正在扫描宏观环境...")
        try:
            macro_data = self.macro_analyzer.analyze_indices_trend(self.indices_config)
            macro_liquidity = self.macro_analyzer.analyze_macro_liquidity()
            macro_context = {**macro_data, "US_10Y": macro_liquidity.get("us_10y")}
        except:
            macro_context = {}
        
        self._analyze_fund_trend(
            fund_code=code,
            user_cost=0,
            macro_context=macro_context,
            debug=debug
        )

    def _analyze_fund_trend(self, fund_code, user_cost, macro_context, debug=False):
        """
        [V5 通用分析内核] 
        """
        print(f"\n🔍 正在透视基金: {fund_code} ...")
        
        # 1. 基础信息
        basic_info = self.fund_data_manager.get_fund_basic_info(fund_code)
        
        # 2. 持仓穿透
        print("   - 正在穿透持仓结构...")
        holdings = self.fund_data_manager.get_top_holdings(fund_code)
        if not holdings:
            print(f"   ⚠️ 无法获取 {fund_code} 持仓数据，跳过分析")
            return

        # 3. 技术形态并发计算
        print(f"   - 正在并发扫描 {len(holdings)} 只重仓股 K 线形态...")
        tech_analysis = self.tech_engine.analyze_holdings_health(holdings)
        if not tech_analysis:
            print("   ⚠️ 技术指标计算失败")
            return

        # 4. 市场情绪
        market_sentiment = {"summary": "Sentiment Engine Pending"}

        # 5. 估算盈亏
        est_change = tech_analysis['health_metrics']['shadow_nav_change']
        user_pnl_pct = 0.0 
        # 此处简化处理，完整版可结合历史净值计算

        # 6. 构建完整 Payload
        payload = {
            "fund_profile": {
                "target_code": fund_code,
                "target_name": basic_info['name'],
                "type": basic_info['type']
            },
            "shadow_nav_estimation": {
                "estimated_change_pct": round(est_change, 2),
                "primary_driver": "Holdings_Analysis"
            },
            "portfolio_health_metrics": tech_analysis['health_metrics'],
            "top_holdings_xray": tech_analysis['holdings_xray'],
            "macro_environment": macro_context,
            "market_sentiment": market_sentiment,
            "user_context": {
                "avg_cost": user_cost,
                "current_pnl_pct": user_pnl_pct
            }
        }

        # 7. 调试输出
        if debug:
            print("\n🐞 [DEBUG] Payload Data:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))

        # 8. AI 推理
        print("   🧠 DeepSeek 正在结合宏观与持仓进行 T+1 决策...")
        prompt = self.prompt_builder.build_fund_analysis_prompt(payload)
        
        if debug:
            print("\n🐞 [DEBUG] Prompt Content:")
            print("-" * 20)
            print(prompt)
            print("-" * 20)

        response = self.client.chat(prompt, use_history=False)
        
        print("\n" + "="*20 + " 💡 投资建议 " + "="*20)
        print(response['content'])
        print("="*50)
        
        self._save_report(fund_code, response['content'])

    def _save_report(self, symbol, content):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"V5_Report_{symbol}_{timestamp}"
        self.data_manager.save_data(pd.DataFrame({'report': [content]}), filename, 'csv')

    def perform_system_reset(self):
        """执行全系统重置"""
        print("\n⚠️  [危险操作] 正在请求系统重置...")
        print("此操作将【永久删除】以下所有数据：")
        print("1. 投资组合配置文件 (my_portfolio.json)")
        print("2. 交易操作日志 (investment_operations.csv)")
        print("3. 所有历史对话记录")
        print("4. 所有已保存的分析报告")
        print("5. RAG 知识库向量数据")
        print("6. 策略进化数据库")
        print("=" * 40)
        
        confirm = input("确认要重置吗？请输入 'RESET' 继续: ").strip()
        if confirm != 'RESET':
            print("❌ 操作已取消")
            return

        print("\n⏳ 正在执行深度清理...")
        self.portfolio_manager.reset_portfolio()
        self.operation_analyzer.clear_logs()
        self.client.clear_all_conversations()
        self.data_manager.clear_all_data()
        self.rag_engine.reset_all_memories()
        self.evolution_engine.reset_evolution_data()
        print("\n✨ 系统已成功恢复出厂设置！请重启程序。")

    def manage_rag_system(self):
        """RAG 知识库管理菜单"""
        print("\n🧠 RAG 知识库管理")
        print("=" * 40)
        stats = self.rag_engine.get_collection_stats()
        print(f"当前状态: 研报({stats.get('knowledge_base',0)}) | 经验({stats.get('experience_base',0)}) | 新闻({stats.get('news_base',0)})")
        
        while True:
            print("\n1. 自动抓取顶级投行观点 (EastMoney)")
            print("2. 导入本地PDF研报")
            print("3. 查看知识库统计")
            print("0. 返回")
            choice = input("选择: ").strip()
            
            if choice == "1":
                self.rag_engine.auto_fetch_institutional_views(top_n=20)
            elif choice == "2":
                path = input("请输入PDF文件路径或文件夹路径: ").strip()
                if path:
                    if path.endswith('.pdf'):
                        self.rag_engine.ingest_pdf_report(path)
                    else:
                        print("⚠️ 暂只支持单个PDF路径")
            elif choice == "3":
                print(self.rag_engine.get_collection_stats())
            elif choice == "0":
                break