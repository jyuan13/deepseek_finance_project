# deepseek_finance_project_V3/finance_analyzer.py

from shadow_engine import ShadowEngine
from rbsa_engine import RBSAEngine
from risk_guard import RiskGuard
from prompt_builder import PromptBuilder
from technical_engine import TechnicalEngine
from macro_analyzer import MacroAnalyzer
from sentiment_engine import SentimentEngine
from financial_brain import FinancialBrainRAG
from strategy_evolution import StrategyEvolutionEngine
from kronos_adapter import KronosAdapter

from finance_core import FinanceCore
from finance_report import FinanceReporter

class FinancialAnalyzer:
    def __init__(self, deepseek_client, fund_data_mgr, portfolio_manager, operation_logger):
        self.client = deepseek_client
        self.fdm = fund_data_mgr
        self.pm = portfolio_manager
        self.logger = operation_logger
        
        # 初始化所有子引擎 (保持依赖注入)
        self.rbsa = RBSAEngine(self.fdm.db)
        self.shadow = ShadowEngine(self.fdm, self.rbsa)
        self.guard = RiskGuard()
        self.tech_engine = TechnicalEngine()
        self.macro_analyzer = MacroAnalyzer()
        self.sentiment_engine = SentimentEngine()
        self.rag_engine = FinancialBrainRAG(persist_directory="./brain_memory")
        self.evolution_engine = StrategyEvolutionEngine(db_path='financial_memory.db', deepseek_client=deepseek_client)
        self.prompt_builder = PromptBuilder(self.sentiment_engine, self.rag_engine)
        
        self._kronos_instance = None
        
        # 初始化 核心逻辑层 和 报告层
        self.core = FinanceCore(
            client=self.client,
            fdm=self.fdm,
            shadow_engine=self.shadow,
            risk_guard=self.guard,
            macro_analyzer=self.macro_analyzer,
            prompt_builder=self.prompt_builder,
            kronos_provider=lambda: self.kronos # 延迟获取 Kronos
        )
        self.reporter = FinanceReporter()

    @property
    def kronos(self):
        if self._kronos_instance is None:
            try:
                self._kronos_instance = KronosAdapter(model_size="small")
            except Exception: self._kronos_instance = None
        return self._kronos_instance

    def run_analysis_menu(self):
        print("\n🚀 V3.7 智能金融分析引擎 (Full Vision)")
        print("=" * 45)
        
        if self.kronos and self.kronos.is_active:
            print("✅ Kronos 预测服务: 在线")
        else:
            print("⚠️  Kronos 预测服务: 离线")

        while True:
            print("\n1. 💰 持仓全景分析 (生成统一日报)")
            print("2. 🔍 任意标的自由透视")
            print("3. 📊 宏观扫描 & Kronos 预测")
            print("4. 🧠 RAG 知识库管理")
            print("5. 🐞 分步调试模式")
            print("99. 🧹 系统重置")
            print("0. 返回")
            
            choice = input("请选择功能 (0-99): ").strip()
            if choice == "1": self._analyze_portfolio_all()
            elif choice == "2": self._analyze_free_target()
            elif choice == "3": self.core.scan_macro_environment(predict=True, debug=True)
            elif choice == "4": self.manage_rag_system()
            elif choice == "5": self._run_step_debug_mode()
            elif choice == "99": self.perform_system_reset()
            elif choice == "0": break
            else: print("❌ 无效输入")

    def _ask_debug_mode(self):
        return input("是否开启调试模式? (y/n): ").lower() == 'y'

    def _analyze_portfolio_all(self):
        """调用 Core 分析，使用 Reporter 报告"""
        debug = self._ask_debug_mode()
        macro_context = self.core.scan_macro_environment(predict=True, debug=debug)
        
        report_cards = []
        
        # 1. 基金分析
        funds = self.pm.get_fund_positions()
        if funds:
            print(f"\n📨 正在分析基金持仓 ({len(funds)} 个)...")
            for pos in funds:
                self.client.clear_history()
                # 调用 Core 获取数据
                data_json = self.core.analyze_fund(
                    fund_code=pos['symbol'],
                    user_cost=pos.get('cost_price', 0),
                    holding_qty=pos.get('current_shares', 0),
                    max_invest_limit=pos.get('max_invest_limit', 0),
                    dca_amount=pos.get('dca_config', {}).get('base_amount', 0),
                    target_amount=pos.get('target_amount', 0), # [New V3.6]
                    macro_context=macro_context,
                    debug=debug,
                    fund_comment=pos.get('comment', '')
                )
                if data_json:
                    # 调用 Reporter 打印和生成 HTML
                    self.reporter.print_console_summary(data_json)
                    html = self.reporter.generate_html_card(data_json)
                    report_cards.append(html)

        # 2. 指数分析
        indices = self.pm.get_index_positions()
        if indices:
            print(f"\n📨 正在分析指数持仓 ({len(indices)} 个)...")
            usd_cny_rate, usd_cny_chg = self.fdm.provider.get_exchange_rate("CNY")
            print(f"   💱 当前美元汇率: {usd_cny_rate:.4f} (变动 {usd_cny_chg:+.2f}%)")
            
            for pos in indices:
                self.client.clear_history()
                data_json = self.core.analyze_index(
                    symbol=pos['symbol'],
                    market_value=pos['market_value_cny'],
                    pnl_rate=pos['pnl_rate'],
                    target_amount=pos.get('target_amount', 0), # [New V3.6]
                    name=pos.get('name', ''),
                    comment=pos.get('comment', ''),
                    macro_context=macro_context,
                    fx_data=(usd_cny_rate, usd_cny_chg),
                    debug=debug
                )
                if data_json:
                    self.reporter.print_console_summary(data_json)
                    html = self.reporter.generate_html_card(data_json)
                    report_cards.append(html)
        
        if report_cards:
            self.reporter.generate_unified_report(macro_context, report_cards)
        else:
            print("⚠️ 未生成有效报告")

    def _analyze_free_target(self):
        code = input("请输入基金代码: ").strip()
        if not code: return
        self.client.clear_history()
        debug = self._ask_debug_mode()
        macro = self.core.scan_macro_environment(predict=True, debug=debug)
        
        data_json = self.core.analyze_fund(code, 0, 0, 0, 0, 0, macro, debug)
        if data_json:
            self.reporter.print_console_summary(data_json)
            html = self.reporter.generate_html_card(data_json)
            self.reporter.save_report(code, html)

    def _run_step_debug_mode(self):
        print("\n🐞 进入分步调试模式")
        code = input("请输入要调试的基金代码 (如 013403): ").strip()
        if not code: return
        
        # 此处为了简单，直接复用 analyze_fund 的 debug 功能
        # 如果需要更细粒度的控制，可以在 Core 中拆分步骤
        print("注意：新版架构下，分步调试将直接运行全流程并开启详细 Debug 日志。")
        macro = self.core.scan_macro_environment(predict=True, debug=True)
        self.core.analyze_fund(code, 0, 0, 0, 0, 0, macro, debug=True)

    def manage_rag_system(self):
        print("\n🧠 RAG 知识库管理")
        print("=" * 40)
        try:
            stats = self.rag_engine.get_collection_stats()
            print(f"当前状态: 研报({stats.get('knowledge_base',0)}) | 经验({stats.get('experience_base',0)}) | 新闻({stats.get('news_base',0)})")
        except:
            print("当前状态: 知识库未初始化")
            
        while True:
            print("\n1. 自动抓取顶级投行观点 (EastMoney)")
            print("2. 导入本地PDF研报")
            print("0. 返回")
            choice = input("选择: ").strip()
            
            if choice == "1":
                self.rag_engine.auto_fetch_institutional_views(top_n=20)
            elif choice == "2":
                path = input("请输入PDF文件路径: ").strip()
                if path and path.endswith('.pdf'):
                    self.rag_engine.ingest_pdf_report(path)
                else:
                    print("❌ 无效的文件路径或非PDF文件")
            elif choice == "0":
                break

    def perform_system_reset(self):
        print("\n⚠️  [危险操作] 正在请求系统重置...")
        print("此操作将清除缓存数据库、日志和AI记忆，但会【保留】您的持仓配置。")
        confirm = input("确认要重置吗？请输入 'RESET' 继续: ").strip()
        if confirm != 'RESET':
            print("❌ 操作已取消")
            return

        print("\n⏳ 正在执行深度清理...")
        self.logger.clear_logs()
        self.client.clear_all_conversations()
        self.fdm.db.clear_all_data()
        self.rag_engine.reset_all_memories()
        self.evolution_engine.reset_evolution_data()
        print("\n✨ 系统缓存已清理！持仓文件已保留。请重启程序。")