# deepseek_finance_project_V2/finance_analyzer.py

from datetime import datetime
import pandas as pd
import os
import sys
import json
import time  # 引入time用于增加延迟
from email_sender import EmailSender
from macro_analyzer import MacroAnalyzer
from sentiment_engine import SentimentEngine
from dark_flow_detector import DarkFlowDetector
from financial_brain import FinancialBrainRAG
from strategy_evolution import StrategyEvolutionEngine
from prompt_builder import PromptBuilder

# 导入拆分后的模块
from etf_holdings import ETFHoldingsManager
from technical_engine import TechnicalEngine

class FinancialAnalyzer:
    def __init__(self, deepseek_client, data_manager):
        self.client = deepseek_client
        self.data_manager = data_manager
        
        self.available_etfs = {
            "513120.SS": "港股创新药ETF",
            "513180.SS": "恒生科技指数ETF", 
            "512890.SS": "红利低波ETF",
            "159995.SZ": "芯片ETF"
        }
        
        # 初始化组件
        self.holdings_manager = ETFHoldingsManager()
        self.tech_engine = TechnicalEngine()  # 新增技术引擎
        self.email_sender = EmailSender()
        
        self.available_indices = {}
        self.available_commodities = {}
        
        # ========== V5引擎初始化 ==========
        print("🔄 初始化V5市场引擎...")
        self.macro_analyzer = MacroAnalyzer()
        self.sentiment_engine = SentimentEngine()
        self.dark_flow_detector = DarkFlowDetector()
        self.rag_engine = FinancialBrainRAG(persist_directory="./brain_memory")
        self.evolution_engine = StrategyEvolutionEngine(
            db_path='financial_memory.db', 
            deepseek_client=deepseek_client
        )
        self.prompt_builder = PromptBuilder(self.sentiment_engine, self.rag_engine)
        
        self.indices_config = {
            'Nasdaq': '^IXIC',
            'S&P500': '^GSPC', 
            'HangSeng_Tech': '3032.HK',
            'Gold': 'GC=F',
            'China_A50': '000016.SH'
        }
        
        # 包含完整的4只ETF配置
        self.etf_config_v5 = [
            {'symbol': '513120.SS', 'name': '港股创新药ETF', 'market': 'CN', 'sector': 'pharma'},
            {'symbol': '513180.SS', 'name': '恒生科技指数ETF', 'market': 'CN', 'sector': 'tech'},
            {'symbol': '512890.SS', 'name': '红利低波ETF', 'market': 'CN', 'sector': 'financial'},
            {'symbol': '159995.SZ', 'name': '芯片ETF', 'market': 'CN', 'sector': 'chips'}
        ]
        print("✅ V5市场引擎初始化完成")

    def _print_debug_data(self, title, data):
        """[调试模式] 打印数据回显，无长度限制"""
        print(f"\n🐞 [DEBUG] >>> 获取到 {title} 数据:")
        
        # 将复杂对象转换为字符串
        if isinstance(data, (dict, list)):
            try:
                content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
            except:
                content = str(data)
        else:
            content = str(data)
            
        # 已移除长度限制，输出完整内容
        print(content)
        print("-" * 50)

    def run_analysis_menu(self):
        """统一的智能金融分析入口"""
        print("\n🚀 V5 智能金融分析引擎\n" + "=" * 40)
        print("这里提供最高性能的全维度分析，结合宏观、技术、资金、舆情与AI记忆。")
        
        while True:
            print("\n可选模式:")
            print("1. 🌍 全市场扫描 (批量分析默认配置ETF)")
            print("2. 🔍 单标的深度透视 (选择具体ETF进行V5深度分析)")
            print("3. 🐞 调试模式运行 (全市场扫描+详细数据回显)")
            print("4. 🐞 调试模式运行 (单标的深度透视+详细数据回显)")
            print("0. 返回主菜单")
            
            choice = self.input_with_exit_check("请选择模式 (0-4): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self._run_full_v5_pipeline(self.etf_config_v5, debug=False)
            elif choice == "2":
                self._handle_single_target_analysis(debug=False)
            elif choice == "3":
                print("\n🐞 已开启全市场调试模式：将显示所有中间过程数据...")
                self._run_full_v5_pipeline(self.etf_config_v5, debug=True)
            elif choice == "4":
                print("\n🐞 已开启单标的调试模式：将显示所有中间过程数据...")
                self._handle_single_target_analysis(debug=True)
            else:
                print("❌ 无效选择")

    def _handle_single_target_analysis(self, debug=False):
        """处理单标的分析选择"""
        print("\n选择要分析的ETF:")
        etf_list = list(self.available_etfs.items())
        for i, (symbol, name) in enumerate(etf_list, 1):
            print(f"{i}. {symbol}: {name}")
            
        choice = self.input_with_exit_check("请输入编号: ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(etf_list):
                symbol, name = etf_list[idx]
                
                # 构建单标的配置
                target_config = next((item for item in self.etf_config_v5 if item['symbol'] == symbol), None)
                if not target_config:
                    target_config = {'symbol': symbol, 'name': name, 'market': 'CN', 'sector': 'general'}
                
                print(f"\n🎯 启动对 {name}({symbol}) 的V5深度分析...")
                self._run_full_v5_pipeline([target_config], debug=debug)
            else:
                print("❌ 无效编号")
        else:
            print("❌ 请输入数字")

    def _run_full_v5_pipeline(self, target_etfs, debug=False):
        """执行全功能的V5分析管道"""
        try:
            # 增加全局延迟，防止初始化过快触发风控
            time.sleep(2)
            
            print("🔍 验证历史预测准确性...")
            verification_results = self.evolution_engine.verify_predictions(days_ago=5)
            if debug and verification_results:
                self._print_debug_data("历史预测验证结果", verification_results)
            
            print("📊 执行多维度市场分析...")
            # 核心：获取包含技术面、宏观、资金面的全量数据
            analysis_data = self._get_comprehensive_analysis(target_etfs, debug=debug)
            
            print("🤖 生成智能分析提示词...")
            prompt = self.prompt_builder.build_comprehensive_prompt(
                analysis_data, 
                target_etfs,
                self.evolution_engine.get_accumulated_wisdom()
            )
            if debug:
                self._print_debug_data("最终发送给AI的Prompt (完整版)", prompt)
            
            print("💭 调用DeepSeek进行深度推理...")
            result = self.client.chat(
                message=prompt, 
                model_type="chat", 
                system_prompt="你是专业的智能投顾，擅长结合技术面细节与宏观大势进行分析", 
                use_history=False
            )
            
            if "content" in result:
                print("\n" + "=" * 60 + "\n📋 V5 深度分析报告:\n" + "=" * 60 + "\n" + result["content"] + "\n" + "=" * 60)
                predictions = self._parse_ai_predictions(result["content"])
                if predictions:
                    self._log_v5_predictions(predictions, analysis_data, target_etfs)
                
                # 自动保存报告
                self.save_analysis_report("V5_Analysis", result, {})

                send = self.input_with_exit_check("\n是否发送邮件? (y/n): ").lower()
                if send == 'y':
                    if not self.email_sender.sender_email: self.email_sender.setup_email_config()
                    recipient = self.input_with_exit_check("请输入接收邮箱: ").strip()
                    if recipient:
                        self.email_sender.send_analysis_report(recipient, "V5_Analysis", {
                            'content': result["content"], 'cost': result.get("cost", 0), 'symbol_name': '智能投顾深度报告'
                        })
        except Exception as e:
            print(f"❌ 分析过程失败: {e}")
            import traceback
            traceback.print_exc()

    def _get_comprehensive_analysis(self, target_etfs, debug=False):
        """获取综合分析数据（含技术面增强）"""
        analysis_data = {
            'timestamp': datetime.now().isoformat(), 
            'market_context': {}, 
            'etf_analysis': {}, 
            'sentiment_data': {}, 
            'rag_context': {}
        }
        
        try:
            # 1. 宏观分析
            print("   📈 1. 分析宏观流动性与趋势...")
            macro_data = {
                'macro_liquidity': self.macro_analyzer.analyze_macro_liquidity(),
                'cross_border_flow': self.macro_analyzer.analyze_cross_border_flow(),
                'major_indices_trend': self.macro_analyzer.analyze_indices_trend(self.indices_config)
            }
            analysis_data['market_context'] = macro_data
            if debug: self._print_debug_data("宏观市场数据", macro_data)
            
            # 2. 舆情分析
            print("   😊 2. 扫描市场舆情...")
            time.sleep(1) # 增加延迟
            symbols = [etf['symbol'].split('.')[0] for etf in target_etfs]
            sentiment_data = self.sentiment_engine.get_sentiment_data(symbols)
            analysis_data['sentiment_data'] = sentiment_data
            if debug: self._print_debug_data("市场舆情数据", sentiment_data)
            
            # 3. 深度扫描 ETF
            print(f"   🎯 3. 深度扫描 {len(target_etfs)} 个目标 (技术+资金+记忆)...")
            for etf in target_etfs:
                symbol = etf['symbol']
                print(f"      >> 处理 {etf['name']} ({symbol})...")
                time.sleep(1) # 增加延迟
                
                # A. 暗流数据
                dark_flow = self.dark_flow_detector.analyze_dark_flow(symbol, etf.get('market', 'CN'))
                if debug: self._print_debug_data(f"{etf['name']} 暗流数据", dark_flow)
                
                # B. 深度技术面分析
                tech_summary = self._generate_tech_summary(symbol, debug=debug)
                if debug: self._print_debug_data(f"{etf['name']} 技术面摘要", tech_summary)
                
                # C. RAG记忆检索
                context = self.rag_engine.get_context_for_analysis(
                    symbol, etf.get('sector', 'general'), analysis_data['market_context']
                )
                analysis_data['rag_context'][symbol] = context
                if debug: self._print_debug_data(f"{etf['name']} RAG记忆", context)
                
                # 组装数据
                analysis_data['etf_analysis'][symbol] = {
                    'name': etf['name'], 
                    'dark_flow': dark_flow,
                    'technical_review': tech_summary,
                    'valuation': {'pe_ttm': 'N/A', 'pb': 'N/A', 'dividend': 'N/A'} 
                }
                
        except Exception as e:
            print(f"   ❌ 数据采集出错: {e}")
        return analysis_data

    def _generate_tech_summary(self, symbol, debug=False):
        """生成标准化的技术面+持仓分析摘要"""
        try:
            summary = []
            # 1. 获取ETF自身数据
            all_data = self.tech_engine.get_multiple_periods_data(symbol)
            if debug and all_data:
                # 打印原始K线数据的最后几行作为调试
                latest_raw = all_data.get('6mo', {}).get('raw')
                if latest_raw is not None:
                    self._print_debug_data(f"{symbol} 6个月K线数据(Preview)", latest_raw.tail())

            if not all_data or '6mo' not in all_data:
                return "数据获取失败"
            
            # 提取6个月的数据和源信息
            main_period = all_data['6mo']
            latest = main_period['technical'].iloc[-1]
            source_info = main_period.get('source_info', {})
            
            # 构建摘要开头 - 增加数据源状态
            source_status_icon = "✅" if source_info.get('status') == "Success" else "⚠️"
            summary.append(f"【数据源验证】 {source_status_icon} {source_info.get('msg', '未知状态')}")
            
            ma_trend = self.tech_engine.analyze_ma_trend(latest)
            rsi = latest['RSI']
            summary.append(f"【ETF走势】\n- 现价: {latest['Close']:.2f}\n- 均线形态: {ma_trend}\n- RSI指标: {rsi:.1f} ({'超买' if rsi>70 else '超卖' if rsi<30 else '中性'})")
            
            # 2. 获取前5大持仓数据
            holdings = self.holdings_manager.get_holdings(symbol)
            if holdings:
                if debug: self._print_debug_data(f"{symbol} 持仓配置", holdings)
                
                summary.append("\n【重仓股透视】")
                top_holdings = sorted(holdings.items(), key=lambda x: x[1], reverse=True)[:5]
                strong_count = 0
                for stock, weight in top_holdings:
                    # 简化处理，只取最新数据
                    s_data, _ = self.tech_engine.get_stock_data_dual_source(stock, "3mo")
                    
                    if s_data is not None and not s_data.empty:
                        curr = s_data['Close'].iloc[-1]
                        ma20 = s_data['Close'].rolling(20).mean().iloc[-1]
                        status = "强势" if curr > ma20 else "弱势"
                        if curr > ma20: strong_count += 1
                        summary.append(f"- {stock}: 权重{weight}% [{status}] (现价{curr:.1f} vs MA20 {ma20:.1f})")
                
                summary.append(f"\n>> 持仓综述: 前5大重仓股中有 {strong_count} 只处于20日线之上。")
            
            return "\n".join(summary)
        except Exception as e:
            return f"技术分析生成失败: {str(e)}"

    def _parse_ai_predictions(self, ai_response):
        import re, json
        match = re.search(r'【预测开始】\s*(.*?)\s*【预测结束】', ai_response, re.DOTALL)
        if match:
            try: return json.loads(match.group(1))
            except: print("❌ 预测结果解析失败")
        return {}

    def _log_v5_predictions(self, predictions, analysis_data, target_etfs):
        for symbol, prediction in predictions.items():
            etf_info = next((etf for etf in target_etfs if etf['symbol'] == symbol), None)
            if etf_info:
                self.evolution_engine.log_prediction(symbol, etf_info['name'], analysis_data, prediction)

    def manage_rag_system(self):
        """管理RAG记忆系统"""
        print("\n🧠 RAG记忆系统管理")
        while True:
            print("\n1. 查看统计\n2. 导入PDF\n3. 导入URL")
            print("4. 🤖 自动抓取机构研报 (摩根/高盛/中金)")
            print("0. 返回")
            choice = self.input_with_exit_check("操作: ")
            if choice == "0": break
            elif choice == "1":
                stats = self.rag_engine.get_collection_stats()
                print(f"统计: 知识库{stats.get('knowledge_base',0)}, 经验库{stats.get('experience_base',0)}")
            elif choice == "2":
                path = self.input_with_exit_check("PDF路径: ")
                tag = self.input_with_exit_check("标签: ")
                self.rag_engine.ingest_pdf_report(path, tag)
            elif choice == "3":
                url = self.input_with_exit_check("URL: ")
                tag = self.input_with_exit_check("标签: ")
                self.rag_engine.ingest_online_research(url, tag)
            elif choice == "4":
                print("⏳ 正在扫描全市场最新研报...")
                self.rag_engine.auto_fetch_institutional_views()

    def show_performance_report(self):
        print("\n📈 系统性能报告")
        perf = self.evolution_engine.get_performance_report()
        print(f"准确率: {perf['overall_accuracy']:.1%} (共{perf['total_predictions']}次)")
        wisdom = self.evolution_engine.get_accumulated_wisdom(3)
        if wisdom:
            print("💡 最近经验:"); 
            for w in wisdom: print(f"  - {w[:50]}...")
    
    def manage_etf_holdings(self):
        self.holdings_manager.show_holdings("513120.SS")
        print("此功能可在代码中扩展详细交互")

    def save_analysis_report(self, prefix, analysis_result, extra_data):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if analysis_result and "content" in analysis_result:
                report_data = {
                    'timestamp': [timestamp],
                    'analysis_report': [analysis_result["content"]],
                    'cost': [analysis_result.get("cost", 0)]
                }
                self.data_manager.save_data(pd.DataFrame(report_data), f"{prefix}_report_{timestamp}", 'csv')
                print(f"✅ 报告已归档: {prefix}_{timestamp}")
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")

    def check_global_exit(self, user_input):
        return user_input.lower().strip() in ['quit', 'exit', '退出', 'q', '0']

    def input_with_exit_check(self, prompt):
        user_input = input(prompt).strip()
        if self.check_global_exit(user_input):
            raise KeyboardInterrupt("用户请求退出")
        return user_input