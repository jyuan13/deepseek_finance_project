"""
==========================================================================================
【文件定义】
文件名: email_sender.py
类名  : EmailSender
==========================================================================================
【函数清单与逻辑流 (Function Logic Flow)】

1. __init__
   [初始化 SMTP 配置] -> {Server: smtp.163.com, Port: 465}
         ↓
   [初始化凭证变量 (Email, Pass, Recipient) 为 None]

2. setup_email_config
   [尝试读取环境变量] -> {缺失?} -> (交互式输入: 账号/授权码/默认收件人)
         ↓
   [调用 test_connection] -> {连接成功?} -> [返回 True/False]

3. test_connection
   [建立 SMTP_SSL 连接] -> [尝试 Login 验证] -> [Quit 关闭连接]
         ↓
   (Catch Exception) -> [返回连接状态 True/False]

4. send_analysis_report(recipient_email, symbol, analysis_result, ...)
   {检查配置} -> [构建 MIMEMultipart] -> [渲染 HTML/Text 模板]
         ↓
   [SMTP_SSL 连接] -> [Login] -> [Send Message] -> [Quit]

5. send_technical_chart(recipient_email, symbol, chart_filepath)
   {检查配置} -> [读取 Chart 文件] -> [构建 MIMEApplication 附件]
         ↓
   [SMTP_SSL 连接] -> [Login] -> [Send Message] -> [Quit]

6. set_default_recipient(recipient_email)
   [接收参数] -> [更新 self.default_recipient]
         ↓
   [打印设置成功信息]
==========================================================================================
"""

import smtplib
from email.mime.text import MIMEText  # 修正：改为 MIMEText
from email.mime.multipart import MIMEMultipart  # 修正：改为 MIMEMultipart
from email.mime.application import MIMEApplication  # 修正：改为 MIMEApplication
import os
from datetime import datetime

class EmailSender:
    def __init__(self):
        self.smtp_server = "smtp.163.com"
        self.smtp_port = 465
        self.sender_email = None
        self.sender_password = None
        self.default_recipient = None
        
    def setup_email_config(self):
        """设置邮箱配置"""
        print("\n📧 邮箱配置设置")
        print("=" * 40)
        
        # 尝试从环境变量获取配置
        self.sender_email = os.environ.get("EMAIL_SENDER")
        self.sender_password = os.environ.get("EMAIL_PASSWORD")
        self.default_recipient = os.environ.get("EMAIL_RECIPIENT")
        
        if not self.sender_email:
            self.sender_email = input("请输入163邮箱地址: ").strip()
        
        if not self.sender_password:
            print("💡 提示：需要使用163邮箱的授权码，不是登录密码")
            self.sender_password = input("请输入邮箱授权码: ").strip()
        
        if not self.default_recipient:
            set_recipient = input("是否设置默认收件人? (y/n): ").strip().lower()
            if set_recipient == 'y':
                self.default_recipient = input("请输入默认收件人邮箱: ").strip()
                print(f"✅ 已设置默认收件人: {self.default_recipient}")
        
        # 测试连接
        if self.test_connection():
            print("✅ 邮箱配置成功!")
            return True
        else:
            print("❌ 邮箱配置失败，请检查邮箱和授权码")
            return False
    
    def test_connection(self):
        """测试邮箱连接"""
        try:
            server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            server.login(self.sender_email, self.sender_password)
            server.quit()
            return True
        except Exception as e:
            print(f"❌ 邮箱连接测试失败: {e}")
            return False
    
    def send_analysis_report(self, recipient_email, symbol, analysis_result, subject_prefix="金融分析报告"):
        """发送分析报告邮件"""
        if not self.sender_email or not self.sender_password:
            print("❌ 请先设置邮箱配置")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart()  # 修正：改为 MIMEMultipart
            
            # 邮件主题
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            subject = f"{subject_prefix} - {symbol} - {timestamp}"
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            
            # 邮件正文
            symbol_name = analysis_result.get('symbol_name', '未知标的')
            analysis_content = analysis_result.get('content', '无分析内容')
            cost = analysis_result.get('cost', 0)
            
            # 构建HTML格式的邮件内容
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #f0f8ff; padding: 15px; border-radius: 5px; }}
                    .content {{ margin: 20px 0; line-height: 1.6; }}
                    .footer {{ margin-top: 30px; padding: 10px; background-color: #f9f9f9; border-radius: 5px; }}
                    .symbol {{ color: #2c3e50; font-weight: bold; }}
                    .timestamp {{ color: #7f8c8d; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>📊 金融分析报告</h2>
                    <p><span class="symbol">{symbol} - {symbol_name}</span> | <span class="timestamp">{timestamp}</span></p>
                </div>
                
                <div class="content">
                    {analysis_content.replace(chr(10), '<br>')}
                </div>
                
                <div class="footer">
                    <p><strong>分析信息:</strong></p>
                    <ul>
                        <li>分析标的: {symbol} ({symbol_name})</li>
                        <li>分析时间: {timestamp}</li>
                        <li>API费用估算: ￥{cost:.6f}</li>
                        <li>发送方式: DeepSeek金融分析系统</li>
                    </ul>
                </div>
            </body>
            </html>
            """
            
            # 添加HTML内容
            html_part = MIMEText(html_content, 'html', 'utf-8')  # 修正：改为 MIMEText
            msg.attach(html_part)
            
            # 添加纯文本版本（备用）
            text_content = f"""
金融分析报告 - {symbol} - {timestamp}

标的: {symbol} ({symbol_name})
分析时间: {timestamp}

分析内容:
{analysis_content}

---
分析信息:
- 分析标的: {symbol} ({symbol_name})
- 分析时间: {timestamp} 
- API费用估算: ￥{cost:.6f}
- 发送方式: DeepSeek金融分析系统
            """
            text_part = MIMEText(text_content, 'plain', 'utf-8')  # 修正：改为 MIMEText
            msg.attach(text_part)
            
            # 发送邮件
            server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()
            
            print(f"✅ 分析报告已发送到: {recipient_email}")
            return True
            
        except Exception as e:
            print(f"❌ 发送邮件失败: {e}")
            return False
    
    def send_technical_chart(self, recipient_email, symbol, chart_filepath):
        """发送技术分析图表邮件"""
        if not self.sender_email or not self.sender_password:
            print("❌ 请先设置邮箱配置")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart()  # 修正：改为 MIMEMultipart
            
            # 邮件主题
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            subject = f"技术分析图表 - {symbol} - {timestamp}"
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            
            # 邮件正文
            text_content = f"""
技术分析图表 - {symbol}

已为您生成 {symbol} 的技术分析图表，请查看附件。

生成时间: {timestamp}

---
DeepSeek金融分析系统
            """
            text_part = MIMEText(text_content, 'plain', 'utf-8')  # 修正：改为 MIMEText
            msg.attach(text_part)
            
            # 添加附件
            with open(chart_filepath, "rb") as file:
                attach_part = MIMEApplication(file.read(), Name=os.path.basename(chart_filepath))  # 修正：改为 MIMEApplication
                attach_part['Content-Disposition'] = f'attachment; filename="{os.path.basename(chart_filepath)}"'
                msg.attach(attach_part)
            
            # 发送邮件
            server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()
            
            print(f"✅ 技术分析图表已发送到: {recipient_email}")
            return True
            
        except Exception as e:
            print(f"❌ 发送图表邮件失败: {e}")
            return False
    
    def set_default_recipient(self, recipient_email):
        """设置默认收件人"""
        self.default_recipient = recipient_email
        print(f"✅ 已设置默认收件人: {recipient_email}")