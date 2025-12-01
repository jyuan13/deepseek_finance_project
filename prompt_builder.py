# deepseek_finance_project_V2/prompt_builder.py

import json

class PromptBuilder:
    def __init__(self, sentiment_engine, rag_engine):
        self.sentiment_engine = sentiment_engine
        self.rag_engine = rag_engine

    def build_fund_analysis_prompt(self, payload):
        """
        [V5 Pro] 构建全维度基金分析提示词
        集成：影子净值 + 持仓透视 + 宏观环境 + 市场情绪
        """
        fund = payload.get('fund_profile', {})
        shadow = payload.get('shadow_nav_estimation', {})
        health = payload.get('portfolio_health_metrics', {})
        holdings = payload.get('top_holdings_xray', [])
        user_ctx = payload.get('user_context', {})
        macro = payload.get('macro_environment', {})
        sentiment = payload.get('market_sentiment', {})
        
        # 1. 格式化重仓股数据 (Markdown 表格)
        holdings_table = "| 股票 | 权重 | 现价 | 涨跌 | MA20状态 | MA60状态 | 信号 |\n|---|---|---|---|---|---|---|\n"
        for s in holdings:
            ma_metrics = s.get('ma_matrix', {})
            price = s['realtime']['price']
            ma20_status = "✅之上" if price > ma_metrics.get('ma20', 0) else "❌之下"
            ma60_status = "✅之上" if price > ma_metrics.get('ma60', 0) else "❌之下"
            
            holdings_table += f"| {s['name']} | {s['weight']}% | {price} | {s['realtime']['change_pct']}% | {ma20_status} | {ma60_status} | {s.get('technical_signal','')} |\n"

        prompt = f"""
# 角色设定
你是一位精通 **趋势交易** 和 **T+1 基金策略** 的资深基金经理。
你正在分析基金：**{fund.get('target_name')} ({fund.get('target_code')})**。

# 🌍 宏观气象站 (Macro Context)
- **核心指数**: 纳指({macro.get('Nasdaq','N/A')}), A50({macro.get('China_A50','N/A')})
- **流动性**: 美债10年收益率 {macro.get('US_10Y','N/A')}%
- **市场情绪**: {sentiment.get('summary', '中性')}

# 📊 基金核心数据 (Fund Payload)

## 1. 影子净值 (今日实时推演)
- **预估涨跌**: {shadow.get('estimated_change_pct'):+.2f}%
- **推演依据**: {shadow.get('primary_driver')}

## 2. 持仓健康度 (均线矩阵)
- **20日线(生命线)站上比例**: {health.get('ratio_above_ma20', 0)*100}% (权重占比)
- **60日线(决策线)站上比例**: {health.get('ratio_above_ma60', 0)*100}% (权重占比)
- **整体 RSI**: {health.get('weighted_rsi_14', 50):.1f}

## 3. 重仓股深度透视 (X-Ray)
{holdings_table}

## 4. 用户账户状态
- **持有成本**: {user_ctx.get('avg_cost')}
- **当前浮动盈亏**: {user_ctx.get('current_pnl_pct'):.2f}%

# 分析指令
请基于 **"宏观环境 + 持仓结构"** 进行深度推理（Chain of Thought）：

1. **环境确认**：当前宏观环境（A50/美债）是助涨还是拖累？
2. **趋势研判**：
   - 短期趋势：80%以上的重仓股是否站稳 MA20？
   - 中期趋势：权重股是否触碰到 MA60 压力位？
3. **归因分析**：
   - 今天的上涨是龙头股带动的真突破，还是跟风股的死猫跳？
4. **操作建议 (T+1 核心)**：
   - 用户当前处于 **{"盈利" if user_ctx.get('current_pnl_pct',0) > 0 else "亏损"}** 状态。
   - **判定法则**：
     - 若 (宏观向好 AND 持仓突破) -> **持有过夜 (博取更高收益)**。
     - 若 (宏观承压 OR 触及MA60压力) -> **今日确权离场 (T+1止盈/止损)**。

请输出 JSON 格式结论，包含字段：
- `trend_assessment`: (简短趋势描述)
- `action_signal`: (BUY / HOLD / SELL / WAIT)
- `reasoning`: (详细的逻辑推演，必须引用上述数据)
- `risk_warning`: (具体的风险点)
"""
        return prompt
    
    # 为了兼容性保留旧接口（可选）
    def build_comprehensive_prompt(self, *args, **kwargs):
        return "Legacy Prompt V4.6"