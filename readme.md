# DeepSeek金融分析系统

基于DeepSeek API的智能金融数据分析与投资研究平台，集成了AI技术分析、多周期数据挖掘、持仓股深度研究和自动化报告生成等功能。

## 🚀 核心功能

### 🤖 智能对话系统
- **多轮对话管理**：自动保存对话历史，支持会话的创建、加载和管理
- **双模型支持**：支持DeepSeek Chat和Reasoner模型
- **使用统计**：实时显示Token消耗和费用估算
- **流式响应**：享受流畅的AI对话体验

### 📈 专业金融分析
- **ETF深度分析**：支持港股创新药ETF(513120)、恒生科技ETF(513180)等主流ETF
- **多周期技术分析**：1个月、3个月、6个月、1年多维度分析
- **持仓股穿透分析**：自动分析ETF重仓股票的技术指标
- **技术指标计算**：RSI、MACD、布林带、移动平均线等完整指标体系

### 🎯 技术分析特性
- **智能图表生成**：自动绘制K线图、技术指标图表
- **均线系统分析**：5日、10日、20日、60日、200日完整均线分析
- **趋势判断**：多周期趋势综合分析，识别关键支撑阻力位
- **风险评估**：系统化风险评估和仓位管理建议

### 📊 数据管理
- **本地数据存储**：CSV/JSON格式保存分析结果
- **数据文件管理**：查看、删除、清理缓存数据
- **分析报告归档**：自动时间戳命名，便于历史回溯

### 📧 邮件自动化
- **分析报告发送**：HTML格式精美报告，支持中英文
- **技术图表附件**：自动生成并发送技术分析图表
- **多邮箱支持**：163邮箱SMTP服务，支持授权码登录

## 🛠 安装部署

### 环境要求
- Python 3.7+
- DeepSeek API密钥

### 依赖安装
```bash
# 一键安装所有依赖
pip install -r requirements.txt

# 或手动安装核心依赖
pip install openai pandas numpy yfinance talib-binary matplotlib mplfinance smtplib



API密钥设置：
# 方法1：环境变量
DEEPSEEK_API_KEY="your_api_key_here"


deepseek_finance_project/
├── main.py                 # 主程序入口
├── deepseek_client.py      # DeepSeek API客户端
├── finance_analyzer.py     # 金融分析核心引擎
├── data_manager.py         # 数据管理模块
├── email_sender.py         # 邮件发送服务
├── requirements.txt        # 依赖库列表
├── financial_data/         # 数据存储目录
├── conversations/          # 对话历史存储
└── README.md              # 项目文档