# deepseek_finance_project_V3/finance_report.py

import os
import json
import glob
from datetime import datetime

class FinanceReporter:
    """
    负责所有输出展示：HTML报告生成、控制台打印、文件保存
    [V3.6 Update] 支持文件名自动递增，防止覆盖
    """
    def __init__(self):
        pass

    def print_console_summary(self, data):
        """打印控制台摘要"""
        color_code = "\033[91m" if data.get('signal') == "BUY" else "\033[92m" if data.get('signal') == "SELL" else "\033[90m"
        reset_code = "\033[0m"
        print(f"   🎯 结论: {color_code}{data.get('signal')}{reset_code} | 金额: {data.get('suggested_amount')}")
        print(f"   📝 理由: {data.get('reason')}")
        print("   " + "-"*30)

    def save_report(self, symbol, content):
        """保存单卡片 HTML"""
        try:
            if not os.path.exists("data"): os.makedirs("data")
            path = f"data/Advice_{symbol}_{datetime.now().strftime('%Y%m%d')}.html"
            mode = 'a' if os.path.exists(path) else 'w'
            with open(path, mode, encoding='utf-8') as f: f.write(content)
            print(f"   💾 卡片已存: {path}")
        except Exception as e: 
            print(f"❌ 报告保存失败: {e}")

    def generate_html_card(self, data):
        """生成单张分析卡片的 HTML"""
        color_map = {"BUY": "#d63031", "SELL": "#00b894", "HOLD": "#636e72"}
        sig = data.get('signal', 'HOLD').upper()
        color = color_map.get(sig, "#636e72")
        
        html = f"""
        <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 16px; background-color: white; font-family: 'Segoe UI', sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <div style="display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid #eee; padding-bottom: 8px; margin-bottom: 12px;">
                <div>
                    <span style="font-size: 18px; font-weight: bold; color: #2d3436;">{data.get('fund_name')}</span>
                    <span style="font-size: 14px; color: #636e72; margin-left: 8px;">{data.get('fund_code')}</span>
                </div>
                <div style="font-size: 12px; color: #b2bec3;">{data.get('time')}</div>
            </div>
            
            <div style="margin-bottom: 8px;">
                <span style="background-color: #f1f2f6; color: #2d3436; padding: 2px 6px; border-radius: 4px; font-size: 12px;">{data.get('comment')}</span>
            </div>

            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                <div style="background-color: {color}; color: white; padding: 6px 12px; border-radius: 4px; font-weight: bold; font-size: 16px;">
                    {data.get('signal')}
                </div>
                <div style="margin-left: 16px; font-size: 14px;">
                    建议金额: <span style="font-weight: bold; color: {color};">{data.get('suggested_amount')}</span>
                </div>
            </div>

            <div style="background-color: #f9f9f9; padding: 12px; border-radius: 4px; color: #2d3436; font-size: 14px; line-height: 1.5;">
                {data.get('reason')}
            </div>

            <div style="margin-top: 12px; font-size: 12px; color: #636e72; display: flex; gap: 16px;">
                <span>🔮 影子净值/估值: <b>{data.get('shadow_nav')}</b></span>
                <span>🛡️ 风控/收益: {data.get('risk_msg')}</span>
            </div>
        </div>
        """
        return html

    def generate_unified_report(self, macro_data, cards_html):
        """生成每日汇总日报 HTML (自动递增文件名)"""
        date_str = datetime.now().strftime('%Y-%m-%d')
        today_compact = datetime.now().strftime('%Y%m%d')
        
        macro_html = ""
        if macro_data:
            # 1. 基础宏观数据
            macro_items = ""
            for k, v in macro_data.items():
                if k != 'Kronos_Detail':
                    macro_items += f"<div style='display:inline-block; background:#dfe6e9; padding:8px 15px; margin:5px; border-radius:20px; font-size:14px;'><b>{k}:</b> {v}</div>"
            macro_html = f"<div style='margin-bottom:20px;'>{macro_items}</div>"
            
            # 2. Kronos 趋势详情表
            if 'Kronos_Detail' in macro_data and macro_data['Kronos_Detail']:
                kronos_table = """
                <div style="margin-top: 15px; background: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 4px solid #6c5ce7;">
                    <h4 style="margin: 0 0 10px 0; color: #6c5ce7;">🤖 Kronos AI Forecast (Global T+1)</h4>
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <tr style="background: #e1e4e8;">
                            <th style="padding: 6px; text-align: left;">Index</th>
                            <th style="padding: 6px; text-align: left;">Date</th>
                            <th style="padding: 6px; text-align: right;">Target</th>
                            <th style="padding: 6px; text-align: right;">Chg%</th>
                            <th style="padding: 6px; text-align: right;">Conf</th>
                        </tr>
                """
                for row in macro_data['Kronos_Detail']:
                    color = "red" if float(row['chg'].replace('%','')) > 0 else "green"
                    kronos_table += f"""
                        <tr>
                            <td style="padding: 6px; border-bottom: 1px solid #eee;">{row['name']}</td>
                            <td style="padding: 6px; border-bottom: 1px solid #eee;">{row['date']}</td>
                            <td style="padding: 6px; border-bottom: 1px solid #eee; text-align: right;">{row['close']}</td>
                            <td style="padding: 6px; border-bottom: 1px solid #eee; text-align: right; color: {color}; font-weight: bold;">{row['chg']}</td>
                            <td style="padding: 6px; border-bottom: 1px solid #eee; text-align: right;">{row['conf']}</td>
                        </tr>
                    """
                kronos_table += "</table></div>"
                macro_html += kronos_table

        full_html = f"""
        <html>
        <head>
            <title>DeepSeek Finance Daily Report - {date_str}</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f5f6fa; color: #2d3436; padding: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .section-title {{ color: #2c3e50; border-left: 5px solid #0984e3; padding-left: 10px; margin-top: 30px; margin-bottom: 20px; }}
                .macro-box {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 30px; }}
                .grid-container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 DeepSeek Finance Daily Report</h1>
                <p style="color: #636e72;">Generated on {date_str}</p>
            </div>
            
            <h2 class="section-title">🌍 Global Macro Overview</h2>
            <div class="macro-box">
                {macro_html if macro_html else "<p>暂无宏观数据</p>"}
            </div>

            <h2 class="section-title">💼 Portfolio Analysis ({len(cards_html)} Positions)</h2>
            <div class="grid-container">
                {"".join(cards_html)}
            </div>
            
            <div style="text-align: center; margin-top: 50px; color: #b2bec3; font-size: 12px;">
                Powered by DeepSeek Finance V3
            </div>
        </body>
        </html>
        """
        
        try:
            if not os.path.exists("data"): os.makedirs("data")
            
            # [Fix] 自动文件递增逻辑
            base_filename = f"Daily_Report_{today_compact}"
            filename = f"{base_filename}.html"
            
            # 检查是否有重名文件
            counter = 1
            while os.path.exists(os.path.join("data", filename)):
                filename = f"{base_filename}_{counter:02d}.html"
                counter += 1
            
            full_path = os.path.join("data", filename)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(full_html)
            print(f"\n📊 统一日报已生成: {full_path}")
            
        except Exception as e:
            print(f"❌ 统一日报保存失败: {e}")