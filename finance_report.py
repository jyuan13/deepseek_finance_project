# deepseek_finance_project_V3/finance_report.py

"""
==========================================================================================
【文件定义】
文件名: finance_report.py
类名  : FinanceReporter
==========================================================================================
【函数清单与逻辑流 (Function Logic Flow)】

1. __init__
   [初始化报告目录] -> [创建 data 文件夹]

2. generate_html_card(data_json)
   [接收单只标的分析结果]
          ↓
   [解析信号颜色 _get_signal_style] -> (Fix: 增强关键词匹配，确保买入变红)
          ↓
   [构建 HTML 卡片] -> (包含: 标题, 核心指标, AI建议, 理由, 风险提示)
          ↓
   [返回 HTML 字符串]

3. print_console_summary(data)
   [控制台打印简报] -> (用于运行时快速查看)

4. generate_unified_report(macro_data, cards_html)
   [接收宏观数据 & 所有标的卡片]
          ↓
   [构建 HTML 头部 (CSS样式, 强制UTF-8)]
          ↓
   [生成宏观概览区域 _render_macro_section] -> (Fix: 补全中文映射 US_10Y等)
          ↓
   [拼接标的分析卡片]
          ↓
   [写入 HTML 文件] -> [自动打开浏览器]

5. save_report(symbol, html_content)
   [保存单只标的报告]

6. _get_signal_style(signal)
   [Helper] -> [根据 Buy/Sell/Hold 返回 CSS] -> (Red/Green/Orange)

7. _render_macro_section(macro_data)
   [Helper] -> [生成宏观环境表格 + Kronos 5日详情表]

8. _render_kronos_table(details)
   [Helper] -> [生成 Kronos 预测数据表格]
==========================================================================================
"""

import os
import json
import webbrowser
from datetime import datetime

class FinanceReporter:
    """
    负责生成可视化分析报告 (HTML/Console)
    [V4.06 Final Fix]
    1. 修复 HTML 渲染格式错误
    2. 增强 Kronos 5日预测展示
    3. 彻底修复买入信号颜色 (红色)
    4. 补全所有宏观指标汉化
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

    def _render_kronos_table(self, details):
        """生成 Kronos 5日预测详情表"""
        if not details or not isinstance(details, list):
            return "<p class='text-muted ml-3'>⚠️ 暂无详细预测数据</p>"
            
        rows = ""
        for item in details:
            # item: {'name': '...', 'date': 'T+1', 'close': '...', 'chg': '...', 'conf': ...}
            chg_str = str(item.get('chg', '0%'))
            
            # 涨跌颜色判断
            is_up = False
            if "+" in chg_str: is_up = True
            elif "%" in chg_str:
                try:
                    val = float(chg_str.replace('%', ''))
                    if val > 0: is_up = True
                except: pass
            
            color_style = "color: #d32f2f;" if is_up else "color: #388e3c;" # 红涨绿跌
            
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
            <h5 class="mb-3">🤖 Kronos AI 未来5日趋势预测 (Trend Forecast)</h5>
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
        """生成宏观数据面板 (全量汉化)"""
        # 中文名称映射表
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
        
        # 遍历宏观数据
        for k, v in macro_data.items():
            if k == "Kronos_Detail":
                kronos_details = v
                continue
            
            # 跳过太长的文本描述，只展示指标
            if k == "Kronos_Prediction" and len(str(v)) > 20:
                v = "请查看下方详情表"

            display_name = name_map.get(k, k)
            
            # 简单的颜色标记
            val_str = str(v)
            badge_class = "secondary"
            if "Bull" in val_str or "Strong" in val_str: badge_class = "danger" # 红
            elif "Bear" in val_str: badge_class = "success" # 绿
            elif "Consolidation" in val_str: badge_class = "warning" # 黄
            
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
            
        # 生成 Kronos 表格
        kronos_html = self._render_kronos_table(kronos_details)
        
        return f"""
        <div class="row">
            {items_html}
        </div>
        {kronos_html}
        """

    def generate_html_card(self, data):
        """生成单个标的的 HTML 卡片"""
        signal_style = self._get_signal_style(data.get('signal', 'HOLD'))
        
        fund_name = data.get('fund_name', 'Unknown')
        code = data.get('fund_code', '000000')
        signal = data.get('signal', 'HOLD')
        reason = data.get('reason', '暂无理由').replace('\n', '<br>')
        suggested = data.get('suggested_amount', '0')
        shadow_nav = data.get('shadow_nav', 'N/A')
        comment = data.get('comment', '')
        risk_msg = data.get('risk_msg', '')
        
        # 风险提示样式
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
                
                {risk_html}
            </div>
        </div>
        """

    def generate_unified_report(self, macro_context, report_cards):
        """生成统一日报 HTML"""
        filename = f"Daily_Report_{datetime.now().strftime('%Y%m%d')}.html"
        filepath = os.path.join(self.output_dir, filename)
        
        # 1. 生成宏观部分
        macro_html = self._render_macro_section(macro_context)
        
        # 2. 拼接卡片
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