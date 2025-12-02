# deepseek_finance_project_V3/prompt_builder.py

import json

class PromptBuilder:
    """
    [V3.3] 提示词工厂 - 定义投资委员会的角色面具
    """
    def __init__(self, sentiment_engine=None, rag_engine=None):
        self.sentiment = sentiment_engine
        self.rag = rag_engine

    def build_macro_agent_prompt(self, macro_data, kronos_signal):
        """角色1: 宏观量化分析师"""
        return f"""
# 角色: 华尔街资深宏观策略师
# 任务: 分析全球市场数据，生成一份简短的【宏观天气简报】。

## 核心数据
1. **量化预测 (Kronos Model)**: {kronos_signal}
   *(注: 这是基于K线大模型生成的纳斯达克趋势预测)*
2. **市场数据**: 
{macro_data}

## 分析要求
1. **定性判断**: 结合 Kronos 信号和期货涨跌，判断今日市场基调 (牛/熊/震荡)。
2. **风险提示**: 黄金或美债是否有异常波动？
3. **输出结论**: 用一句话概括今日策略倾向 (例如: "顺势做多" 或 "避险观望")。

请直接输出简报内容，不要废话。
"""

    def build_sentiment_agent_prompt(self, news_list):
        """角色2: 舆情风控官"""
        # 简单清洗新闻列表，避免过长
        news_str = "\n".join([f"- {n}" for n in news_list[:8]]) if news_list else "暂无重大新闻"
        
        return f"""
# 角色: 舆情风控官
# 任务: 阅读以下新闻标题，生成【市场情绪简报】。

## 新闻流
{news_str}

## 分析要求
1. **情绪评分**: 0 (极度恐慌) - 10 (极度贪婪)。
2. **关键事件**: 指出可能影响大盘的单一重大事件 (如有)。
3. **噪音过滤**: 忽略无关紧要的个股新闻，关注宏观/政策/地缘影响。

请输出格式: "情绪评分: X/10\n摘要: ..."
"""

    def build_cio_agent_prompt(self, fund_ctx, macro_report, sentiment_report, risk_msg):
        """角色3: 首席投资官 (CIO) - 做最终决定"""
        return f"""
# 角色: 基金管理委员会 CIO
# 任务: 综合各部门报告，对标的【{fund_ctx['name']} ({fund_ctx['code']})】做出操作决定。

## 1. 参谋部情报
- **【宏观部】**: {macro_report}
- **【舆情部】**: {sentiment_report}
- **【风控部】**: {risk_msg}

## 2. 标的实时数据
- **类型**: {fund_ctx['type']}
- **影子净值 (T+0估算)**: {fund_ctx['shadow_change']:+}%
- **依据**: {fund_ctx['basis']}
- **持仓状态**: {fund_ctx['holding_status']}

## 决策逻辑
1. **风控一票否决**: 如果风控部示警 (⛔)，必须执行防御操作。
2. **顺势而为**: 如果宏观部看跌且影子净值下跌，不要试图抄底。
3. **定投修正**: 如果是定投策略，且当前跌幅较大，可考虑维持或微量增加定投；若暴涨，可暂停定投。

<thinking>
(在此处进行逻辑推演，权衡宏观、舆情与个股表现的冲突点...)
</thinking>

```json
{{
    "signal": "BUY/SELL/HOLD",
    "reason": "一句话决策理由",
    "suggested_operation": "具体操作建议 (如: 买入 500元)"
}}
"""