from typing import Dict, Any, List
from sentiment_engine import SentimentEngine
from financial_brain import FinancialBrainRAG

class PromptBuilder:
    """
    提示词构建器 - 集成RAG记忆
    """
    
    def __init__(self, sentiment_engine: SentimentEngine = None, rag_engine: FinancialBrainRAG = None):
        self.sentiment_engine = sentiment_engine
        self.rag_engine = rag_engine
    
    def build_comprehensive_prompt(self, analysis_data: Dict[str, Any], 
                                 etf_list: List[Dict], 
                                 historical_lessons: List[str] = None) -> str:
        """构建综合分析提示词"""
        
        market_context = analysis_data['market_context']
        etf_analysis = analysis_data['etf_analysis']
        rag_context = analysis_data.get('rag_context', {})
        
        # 生成各个部分
        sentiment_segment = ""
        if self.sentiment_engine:
            sentiment_segment = self.sentiment_engine.generate_nlp_prompt_segment(etf_list)
        
        rag_segment = self._build_rag_segment(rag_context, etf_list)
        wisdom_segment = self._format_historical_wisdom(historical_lessons)
        
        prompt = f"""
# 📊 DeepSeek金融分析系统 V5.0 - 智能投顾报告
分析时间: {analysis_data['timestamp']}

{wisdom_segment}

{rag_segment}

## 🌍 宏观环境分析

### 流动性状况
- 中美利差: {market_context['macro_liquidity'].get('spread_cn_us', 'N/A')}
- 美元指数: {market_context['macro_liquidity'].get('dxy', 'N/A')}
- 美国10年期国债: {market_context['macro_liquidity'].get('us_10y', 'N/A')}
- 中国10年期国债: {market_context['macro_liquidity'].get('cn_10y', 'N/A')}

### 资金流向
- 北向资金: {market_context['cross_border_flow'].get('north_money', 'N/A')}
- 南向资金: {market_context['cross_border_flow'].get('south_money', 'N/A')}

### 指数趋势
{self._format_indices_trend(market_context['major_indices_trend'])}

## 🎯 ETF深度分析 (含暗流与技术面)

{self._format_etf_analysis(etf_analysis)}

{sentiment_segment}

## 📋 分析要求

请基于以上多维数据(宏观、暗流、技术、舆情)，提供专业的投资分析：

### 1. 宏观趋势判断
- 当前市场整体处于什么周期？（Risk-on/Risk-off）
- 流动性环境对各类资产的影响

### 2. ETF投资建议（结合技术面与暗流信号）
- 对各ETF的买入/持有/卖出建议
- **特别注意**：暗流信号(筹码/做空)与技术面(均线/RSI)是否共振
- 仓位管理和分批建仓建议

### 3. 预测输出格式
**请为每个ETF单独输出预测**，格式如下：

【预测开始】
{{
  "513120.SH": {{"outlook": "Bullish", "confidence": 0.75, "timeframe": 5, "reasoning": "简要分析理由"}},
  "512890.SH": {{"outlook": "Neutral", "confidence": 0.60, "timeframe": 5, "reasoning": "简要分析理由"}},
  "159995.SZ": {{"outlook": "Bearish", "confidence": 0.80, "timeframe": 5, "reasoning": "简要分析理由"}}
}}
【预测结束】

### 4. 风险提示
- 需要重点关注的风险因素
- 技术面破位或过热风险

请结合专家观点、历史经验和实时数据，提供全面客观的分析。
"""
        return prompt
    
    def _build_rag_segment(self, rag_context: Dict[str, Any], etf_list: List[Dict]) -> str:
        """构建RAG记忆片段"""
        if not rag_context or not self.rag_engine:
            return ""
        
        segment = """
## 🧠 智能记忆分析 (RAG系统)

"""
        for etf in etf_list:
            symbol = etf['symbol']
            if symbol in rag_context:
                context = rag_context[symbol]
                
                segment += f"### {etf['name']} ({symbol}) 相关记忆\n"
                
                # 专家观点
                if context.get('expert_views'):
                    segment += "**📚 专家观点:**\n"
                    for i, view in enumerate(context['expert_views'][:2]):
                        segment += f"{i+1}. {view[:100]}...\n"
                
                # 历史模式
                if context.get('historical_patterns'):
                    segment += "\n**🕰️ 历史相似模式:**\n"
                    for pattern in context['historical_patterns']:
                        segment += f"- {pattern[:80]}...\n"
                
                # 行业新闻
                if context.get('sector_news'):
                    segment += "\n**📰 相关资讯:**\n"
                    for news in context['sector_news'][:2]:
                        segment += f"- {news}\n"
                
                segment += "\n"
        
        return segment
    
    def _format_historical_wisdom(self, lessons: List[str]) -> str:
        """格式化历史经验"""
        if not lessons:
            return ""
        
        formatted = """
## ⚠️ 历史经验教训 (基于过往错误总结)

"""
        for i, lesson in enumerate(lessons, 1):
            formatted += f"{i}. {lesson}\n"
        
        formatted += "\n**请特别注意这些基于真实错误总结的经验法则**\n"
        return formatted
    
    @staticmethod
    def _format_indices_trend(trends: Dict[str, str]) -> str:
        lines = []
        for name, trend in trends.items():
            lines.append(f"- {name}: {trend}")
        return "\n".join(lines) if lines else "暂无趋势数据"
    
    @staticmethod
    def _format_etf_analysis(etf_analysis: Dict[str, Any]) -> str:
        lines = []
        for symbol, data in etf_analysis.items():
            lines.append(f"### {data['name']} ({symbol})")
            
            # 基础估值
            lines.append(f"- 估值(PE): {data.get('valuation', {}).get('pe_ttm', 'N/A')}")
            
            # 技术面深度分析 (新功能)
            tech_review = data.get('technical_review')
            if tech_review:
                lines.append(f"\n💻 技术面深度分析:\n{tech_review}")
            
            # 暗流数据
            dark_flow = data.get('dark_flow', {})
            if dark_flow.get('signal') != 'Neutral':
                lines.append(f"- 🎯 暗流信号: {dark_flow.get('signal')} - {dark_flow.get('desc', '')}")
            
            lines.append("")
        return "\n".join(lines)