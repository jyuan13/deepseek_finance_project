"""
==========================================================================================
【文件定义】
文件名: market_engine_v5.py
类名  : DeepSeekMarketEngineV5
==========================================================================================
【函数清单与逻辑流 (Function Logic Flow)】

1. __init__(tushare_token, deepseek_client, rag_persist_dir)
   [初始化子引擎] -> (Macro, ETF, Sentiment, Evolution, RAG, DarkFlow, Prompt)
         ↓
   [Ready]

2. analyze_market_context(indices_config)
   [MacroAnalyzer Calls] -> (Liquidity + CrossBorder + Indices Trend)
         ↓
   [Market Breadth Calc] -> [Return Market Context Dict]

3. analyze_etf_targets(etf_list)
   [ETFAnalyzer Analysis] -> [Loop ETFs]
         ↓
   [DarkFlowDetector Analysis] -> [Merge Data] -> [Return Analysis Dict]

4. get_rag_context(etf_list, market_context)
   [Loop ETFs] -> [RAG Engine Query (Symbol+Sector+Macro)]
         ↓
   [Aggregate Context] -> [Return Dict]

5. get_comprehensive_analysis(indices_config, etf_list)
   [Parallel Calls: Market Context, ETF Analysis, Sentiment, RAG Context]
         ↓
   [Aggregate All Data + Timestamp] -> [Return Huge Dict]

6. generate_analysis_prompt(indices_config, etf_list)
   [Call get_comprehensive_analysis] -> [Evolution Engine Get Wisdom]
         ↓
   [Prompt Builder Build Prompt] -> [Return String]

7. log_predictions(etf_list, ai_responses)
   [Get Current Analysis] -> [Loop ETFs]
         ↓
   [Evolution Engine Log Prediction] -> [RAG Engine Memorize State]

8. verify_historical_predictions(days_ago)
   [Evolution Engine Verify] -> [Update RAG Memory (Optional)]
         ↓
   [Return Verification Results]

9. get_rag_stats
   [Call RAG Engine Stats] -> [Return Dict]

10. get_performance_report
    [Call Evolution Engine Report] -> [Return Dict]

11. _get_market_breadth(indices_config)
    [Placeholder Logic] -> [Return Breadth Dict]

12. close
    [Close Evolution Engine Connection]
==========================================================================================
"""

import datetime
from typing import Dict, Any, List

from macro_analyzer import MacroAnalyzer
from etf_analyzer import ETFAnalyzer
from sentiment_engine import SentimentEngine
from strategy_evolution import StrategyEvolutionEngine
from financial_brain import FinancialBrainRAG
from dark_flow_detector import DarkFlowDetector
from prompt_builder import PromptBuilder

class DeepSeekMarketEngineV5:
    """
    V5 市场引擎 - 集成RAG记忆和暗流探测
    """
    
    def __init__(self, tushare_token=None, deepseek_client=None, rag_persist_dir="./brain_memory"):
        self.macro_analyzer = MacroAnalyzer()
        self.etf_analyzer = ETFAnalyzer(tushare_token)
        self.sentiment_engine = SentimentEngine(tushare_token)
        self.evolution_engine = StrategyEvolutionEngine(deepseek_client=deepseek_client)
        self.rag_engine = FinancialBrainRAG(rag_persist_dir)
        self.dark_flow_detector = DarkFlowDetector()
        self.prompt_builder = PromptBuilder(self.sentiment_engine, self.rag_engine)
    
    def analyze_market_context(self, indices_config: Dict[str, str]) -> Dict[str, Any]:
        """分析市场大环境"""
        return {
            'macro_liquidity': self.macro_analyzer.analyze_macro_liquidity(),
            'cross_border_flow': self.macro_analyzer.analyze_cross_border_flow(),
            'major_indices_trend': self.macro_analyzer.analyze_indices_trend(indices_config),
            'market_breadth': self._get_market_breadth(indices_config)
        }
    
    def analyze_etf_targets(self, etf_list: List[Dict]) -> Dict[str, Any]:
        """分析ETF目标"""
        etf_analysis = self.etf_analyzer.analyze_etf_targets(etf_list)
        
        # 为每个ETF添加暗流分析
        for symbol, data in etf_analysis.items():
            etf_info = next((etf for etf in etf_list if etf['symbol'] == symbol), {})
            market = etf_info.get('market', 'CN')
            
            # 暗流分析
            dark_flow_data = self.dark_flow_detector.analyze_dark_flow(symbol, market)
            data['dark_flow'] = dark_flow_data
            
        return etf_analysis
    
    def get_rag_context(self, etf_list: List[Dict], market_context: Dict) -> Dict[str, Any]:
        """获取RAG上下文"""
        rag_context = {}
        
        for etf in etf_list:
            symbol = etf['symbol']
            sector = etf.get('sector', 'general')
            
            context = self.rag_engine.get_context_for_analysis(
                symbol=symbol,
                sector=sector,
                current_macro=market_context
            )
            rag_context[symbol] = context
        
        return rag_context
    
    def get_comprehensive_analysis(self, indices_config: Dict[str, str], etf_list: List[Dict]) -> Dict[str, Any]:
        """获取综合分析结果"""
        print("🚀 启动V5综合分析引擎...")
        
        # 并行分析多个维度
        market_context = self.analyze_market_context(indices_config)
        etf_analysis = self.analyze_etf_targets(etf_list)
        sentiment_data = self.sentiment_engine.get_sentiment_data(
            [etf['symbol'].split('.')[0] for etf in etf_list]
        )
        rag_context = self.get_rag_context(etf_list, market_context)
        
        return {
            'timestamp': datetime.datetime.now().isoformat(),
            'market_context': market_context,
            'etf_analysis': etf_analysis,
            'sentiment_data': sentiment_data,
            'rag_context': rag_context
        }
    
    def generate_analysis_prompt(self, indices_config: Dict[str, str], etf_list: List[Dict]) -> str:
        """生成完整的分析提示词"""
        analysis_data = self.get_comprehensive_analysis(indices_config, etf_list)
        
        # 获取历史经验教训
        wisdom = self.evolution_engine.get_accumulated_wisdom()
        
        return self.prompt_builder.build_comprehensive_prompt(
            analysis_data, etf_list, wisdom
        )
    
    def log_predictions(self, etf_list: List[Dict], ai_responses: Dict[str, Dict]):
        """记录AI预测结果"""
        analysis_data = self.get_comprehensive_analysis({}, etf_list)
        
        for etf in etf_list:
            symbol = etf['symbol']
            if symbol in ai_responses:
                # 记录到进化引擎
                self.evolution_engine.log_prediction(
                    symbol=symbol,
                    etf_name=etf['name'],
                    input_data=analysis_data,
                    ai_response=ai_responses[symbol]
                )
                
                # 记录到RAG记忆
                self.rag_engine.memorize_market_state(
                    date=datetime.datetime.now().strftime('%Y-%m-%d'),
                    macro_summary=analysis_data['market_context'],
                    ai_prediction=ai_responses[symbol].get('outlook', 'Unknown'),
                    actual_outcome="待验证"
                )
    
    def verify_historical_predictions(self, days_ago: int = 5):
        """验证历史预测"""
        print(f"🔍 验证 {days_ago} 天前的预测...")
        results = self.evolution_engine.verify_predictions(days_ago)
        
        # 更新RAG记忆中的实际结果
        for result in results:
            # 这里可以添加更新RAG记忆的逻辑
            pass
            
        return results
    
    def get_rag_stats(self) -> Dict[str, int]:
        """获取RAG系统统计"""
        return self.rag_engine.get_collection_stats()
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return self.evolution_engine.get_performance_report()
    
    def _get_market_breadth(self, indices_config: Dict[str, str]) -> Dict[str, Any]:
        """获取市场广度（简化版）"""
        breadth = {}
        for name in indices_config.keys():
            breadth[name] = {
                'stocks_above_20ma': '待实现',
                'stocks_above_60ma': '待实现',
                'advance_decline_ratio': '待实现'
            }
        return breadth
    
    def close(self):
        """关闭引擎"""
        self.evolution_engine.close()