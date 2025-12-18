# deepseek_finance_project_V3/finance_report.py

"""
==========================================================================================
【文件定义】
文件名: finance_report.py
类名  : FinanceReporter
==========================================================================================
"""

import os
import json
import webbrowser
from datetime import datetime

class FinanceReporter:
    """
    负责生成可视化分析报告 (HTML/Console)
    [V4.10 Final Fix]
    1. 新增: 每个标的卡片支持显示 5日趋势预测详情表 (forecast_df)
    2. 优化: 统一表格样式，支持 DataFrame 和 List[Dict] 格式
    3. 修复: 买入/卖出信号颜色适配 A股习惯 (红涨绿跌)
    """
    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def _get_signal_style(self, signal):
        """
        根据信号返回 CSS 样式
        逻辑: 
        - 买入/看涨 (Buy/Bull/Long) -> 红色 (Red)
        - 卖出/看跌 (Sell/Bear/Short) -> 绿色 (Green)
        - 持有/震荡 (Hold/Consolidation) -> 橙色 (Orange)
        """
        s = str(signal).upper().strip()
        
        # 红色关键词 (买入/利好)
        red_keys = ["BUY", "买入", "BULL", "STRONG BULL", "LONG", "增持", "建仓", "机会"]
        if any(k in s for k in red_keys):
            return "background-color: #ffebee; color: #c62828; border: 1px solid #ffcdd2;"
        
        # 绿色关键词 (卖出/利空) - 符合A股涨跌颜色习惯(红涨绿跌)
        green_keys = ["SELL", "卖出", "BEAR", "STRONG BEAR", "SHORT", "减持", "清仓", "风险"]
        if any(k in s for k in green_keys):
            return "background-color: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9;"
        
        # 橙色/灰色 (持有/观望)
        return "background-color: #fff3e0; color: #ef6c00; border: 1px solid #ffe0b2;"

    def _df_to_html_table(self, df_data):
        """
        [新增] 将预测 DataFrame (或字典列表) 转换为 HTML 表格
        """
        if df_data is None:
            return ""
            
        # 兼容性处理: 如果是 DataFrame，先转为 list of dict
        data_list = df_data
        if hasattr(df_data, 'to_dict'):
            data_list = df_data.to_dict(orient='records')
        
        if not isinstance(data_list, list) or len(data_list) == 0:
            return ""

        html = '<div class="table-responsive mt-3 mb-2">'
        html += '<h6 class="text-muted mb-2" style="font-size: 0.9rem;">📉 未来5日趋势预测 (Trend Forecast)</h6>'
        html += '<table class="table table-sm table-bordered table-hover" style="font-size: 0.85rem; text-align: center;">'
        
        # 表头
        html += '<thead class="thead-light"><tr>'
        html += '<th>日期 (Date)</th><th>预测价 (Forecast)</th><th>累计涨跌 (Cum Chg%)</th>'
        html += '</tr></thead><tbody>'

        for i, row in enumerate(data_list):
            # 1. 处理日期
            # 优先取 'date', 其次 'ds', 再次用 T+n
            date_val = row.get('date', row.get('ds', f"T+{i+1}"))
            # 如果是 timestamp 对象，转字符串
            if hasattr(date_val, 'strftime'):
                date_val = date_val.strftime('%m-%d')
            else:
                date_val = str(date_val)[:10]

            # 2. 处理价格 (close 或 yhat)
            price_val = row.get('close', row.get('yhat', 0))
            try: 
                price_str = f"{float(price_val):.2f}"
            except: 
                price_str = str(price_val)
            
            # 3. 处理涨跌幅 (cum_pct_chg)
            chg_val = row.get('cum_pct_chg', 0)
            try:
                chg_float = float(chg_val)
                sign = "+" if chg_float >= 0 else ""
                # A股习惯: 红涨绿跌
                color_class = "text-danger" if chg_float >= 0 else "text-success"
                chg_str = f'<span class="{color_class} font-weight-bold">{sign}{chg_float:.2f}%</span>'
            except:
                chg_str = str(chg_val)

            html += f'<tr><td>{date_val}</td><td>{price_str}</td><td>{chg_str}</td></tr>'

        html += '</tbody></table></div>'
        return html

    def _render_kronos_table(self, details):
        """生成宏观界面的 Kronos 综合预测表 (保持原样或复用逻辑)"""
        if not details or not isinstance(details, list):
            return "<p class='text-muted ml-3'>⚠️ 暂无详细预测数据</p>"
            
        rows = ""
        for item in details:
            chg_str = str(item.get('chg', '0%'))
            
            is_up = False
            if "+" in chg_str: is_up = True
            elif "%" in chg_str:
                try:
                    val = float(chg_str.replace('%', ''))
                    if val > 0: is_up = True
                except: pass
            
            # 红涨绿跌
            color_style = "color: #d32f2f;" if is_up else "color: #388e3c;"
            
            rows += f"""
            <tr>
                <td><strong>{item.get('name')}</strong></td>
                <td>{item.get('date')}</td>
                <td>{item.get('close')}</td>
                <td style="{color_style} font-weight: bold;">{chg_str}</td>
                <td>
                    <div class="progress" style="height: 6px; width: 60px;">
                        <div class="progress-bar bg-info" role="progressbar" style="width: {float(item.get('conf', 0))*100}%"></div>
                    </div>
                    <small>{item.get('conf', 0):.2f}</small>
                </td>
            </tr>
            """
            
        return f"""
        <div class="kronos-section mt-3">
            <h5 class="mb-3">🤖 Kronos AI 综合预测 (Global Forecast)</h5>
            <div class="table-responsive">
                <table class="table table-sm table-hover table-bordered">
                    <thead class="thead-light">
                        <tr>
                            <th>标的名称</th>
                            <th>预测周期</th>
                            <th>预期点位</th>
                            <th>预期涨跌</th>
                            <th>置信度 (Confidence)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>
        </div>
        """

    def _render_macro_section(self, macro_data):
        """生成宏观数据面板"""
        name_map = {
            "Nasdaq": "纳斯达克 (Nasdaq)",
            "SP500": "标普500 (S&P 500)",
            "Shanghai": "上证指数 (Shanghai)",
            "CSI300": "沪深300 (CSI 300)",
            "HangSeng": "恒生指数 (Hang Seng)",
            "HSTech": "恒生科技 (HS Tech)",
            "Nikkei225": "日经225 (Nikkei)",
            "Gold": "黄金 (Gold)",
            "US_10Y": "10年美债收益率",
            "Kronos_Prediction": "Kronos 综合预测",
            "USD_CNY": "美元/人民币汇率"
        }

        items_html = ""
        kronos_details = []
        
        for k, v in macro_data.items():
            if k == "Kronos_Detail":
                kronos_details = v
                continue
            
            if k == "Kronos_Prediction" and len(str(v)) > 20:
                v = "请查看下方详情表"

            display_name = name_map.get(k, k)
            
            val_str = str(v)
            badge_class = "secondary"
            if "Bull" in val_str or "Strong" in val_str: badge_class = "danger" # Red
            elif "Bear" in val_str: badge_class = "success" # Green
            elif "Consolidation" in val_str: badge_class = "warning" # Orange
            
            items_html += f"""
            <div class="col-md-3 col-sm-6 mb-3">
                <div class="card h-100 shadow-sm">
                    <div class="card-body p-3 text-center d-flex flex-column justify-content-center">
                        <small class="text-muted mb-1">{display_name}</small>
                        <div class="font-weight-bold text-{badge_class}" style="font-size: 1.1em;">{v}</div>
                    </div>
                </div>
            </div>
            """
            
        kronos_html = self._render_kronos_table(kronos_details)
        
        return f"""
        <div class="row">
            {items_html}
        </div>
        {kronos_html}
        """

    def generate_html_card(self, data):
        """生成单个标的的 HTML 卡片 (包含 5日预测表)"""
        signal_style = self._get_signal_style(data.get('signal', 'HOLD'))
        
        fund_name = data.get('fund_name', 'Unknown')
        code = data.get('fund_code', '000000')
        signal = data.get('signal', 'HOLD')
        reason = data.get('reason', '暂无理由').replace('\n', '<br>')
        suggested = data.get('suggested_amount', '0')
        shadow_nav = data.get('shadow_nav', 'N/A')
        comment = data.get('comment', '')
        risk_msg = data.get('risk_msg', '')
        
        # [修改点] 渲染 5日预测表格
        forecast_html = ""
        if 'forecast_df' in data:
            forecast_html = self._df_to_html_table(data['forecast_df'])
        
        # 风险提示
        risk_html = ""
        if risk_msg and risk_msg != 'None' and risk_msg != '':
            risk_html = f"""
            <div class="alert alert-warning mt-3 mb-0 py-2">
                <i class="bi bi-exclamation-triangle-fill"></i> 
                <strong>风控提示:</strong> {risk_msg}
            </div>
            """

        return f"""
        <div class="card mb-4 shadow-sm border-0">
            <div class="card-header d-flex justify-content-between align-items-center py-3" style="{signal_style}">
                <h5 class="mb-0 text-dark">
                    <strong>{fund_name}</strong> 
                    <span class="badge badge-light ml-2 text-muted">{code}</span>
                </h5>
                <span class="badge badge-light px-3 py-2" style="font-size: 1em; border: 1px solid #ccc;">{signal}</span>
            </div>
            <div class="card-body">
                <div class="row mb-3 text-center">
                    <div class="col-4 border-right">
                        <small class="text-muted d-block mb-1">实时估值/涨跌</small>
                        <h4 class="text-primary mb-0">{shadow_nav}</h4>
                    </div>
                    <div class="col-4 border-right">
                        <small class="text-muted d-block mb-1">建议操作金额</small>
                        <h4 class="text-dark mb-0">{suggested} <small>CNY</small></h4>
                    </div>
                    <div class="col-4">
                        <small class="text-muted d-block mb-1">策略备注</small>
                        <p class="mb-0 font-weight-bold">{comment if comment else '-'}</p>
                    </div>
                </div>
                
                <div class="card bg-light border-0">
                    <div class="card-body py-2">
                        <h6 class="card-subtitle mb-2 text-muted">🧠 AI 决策逻辑:</h6>
                        <p class="card-text text-dark" style="line-height: 1.6;">{reason}</p>
                    </div>
                </div>
                
                {forecast_html}
                
                {risk_html}
            </div>
        </div>
        """

    def generate_unified_report(self, macro_context, report_cards):
        """生成统一日报 HTML"""
        filename = f"Daily_Report_{datetime.now().strftime('%Y%m%d')}.html"
        filepath = os.path.join(self.output_dir, filename)
        
        macro_html = self._render_macro_section(macro_context)
        cards_html = "\n".join(report_cards)
        
        html_template = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>每日金融分析日报 - {datetime.now().strftime('%Y-%m-%d')}</title>
            <link href="https://cdn.bootcdn.net/ajax/libs/twitter-bootstrap/4.6.2/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
            <style>
                body {{ background-color: #f4f6f9; font-family: 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', sans-serif; }}
                .container {{ max-width: 1000px; margin-top: 40px; margin-bottom: 60px; }}
                .header-section {{ 
                    background: white; 
                    padding: 30px; 
                    border-radius: 12px; 
                    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                    margin-bottom: 30px; 
                    border-left: 5px solid #007bff;
                }}
                .section-title {{ 
                    font-size: 1.25rem; 
                    font-weight: 700; 
                    color: #2c3e50; 
                    margin-bottom: 20px; 
                    border-bottom: 2px solid #e9ecef; 
                    padding-bottom: 10px;
                }}
                .footer {{ color: #adb5bd; font-size: 0.85rem; }}
                .table td, .table th {{ vertical-align: middle; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header-section">
                    <h1 class="text-primary mb-2">📈 每日金融分析日报</h1>
                    <p class="text-muted mb-0">
                        生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &nbsp;|&nbsp; 
                        引擎: DeepSeek-V3 + Kronos AI
                    </p>
                </div>
                
                <div class="mb-5">
                    <h3 class="section-title">🌍 全球宏观市场环境 (Macro Overview)</h3>
                    {macro_html}
                </div>
                
                <div>
                    <h3 class="section-title">💼 持仓深度分析 (Portfolio Analysis)</h3>
                    {cards_html}
                </div>
                
                <div class="footer text-center mt-5">
                    <p>Generated by DeepSeek Finance Project V4.05</p>
                    <p>投资有风险，决策需谨慎</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_template)
            
        print(f"\n📊 统一日报已生成: {filepath}")
        
        try:
            webbrowser.open(f"file://{os.path.abspath(filepath)}")
        except: pass

    def print_console_summary(self, data):
        print(f"\n   🎯 结论: {data.get('signal')} | 金额: {data.get('suggested_amount')}")
        print(f"   📝 理由: {data.get('reason')}")
        print("   " + "-"*30)

    def save_report(self, symbol, html_content):
        filename = f"Report_{symbol}_{datetime.now().strftime('%Y%m%d')}.html"
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"   📄 报告已保存: {path}")