<div align="center">

# 🚀 DeepSeek Finance Project V3

**基于 LLM 双大脑 (DeepSeek + Qwen) 的全天候智能投顾系统**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![DeepSeek](https://img.shields.io/badge/AI-DeepSeek_V3-blue)](https://www.deepseek.com/)
[![Qwen](https://img.shields.io/badge/AI-Qwen_Turbo-green)](https://tongyi.aliyun.com/)
[![AkShare](https://img.shields.io/badge/Data-AkShare-orange)](https://akshare.xyz/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

## 📖 项目简介 (Introduction)

**DeepSeek Finance Project V3** 是一个为场外基金与股票投资者打造的自动化量化分析系统。它不仅仅是一个数据面板，更是一个具备**“双重人格”**的 AI 投资助理。

在 V3 版本中，我们引入了 **Qwen (通义千问)** 作为第二大脑，与 **DeepSeek** 形成“博弈与互证”机制——DeepSeek 负责深度逻辑推理与宏观把控，Qwen 负责实时数据校验与风险纠偏，从而显著降低大模型的“幻觉”风险。

系统的核心目标是解决场外基金交易中的**净值滞后痛点**，通过穿透持仓计算“影子净值 (Shadow NAV)”，助你在每日 14:30 做出精准决策。

## ✨ 核心特性 (Key Features)

### 🧠 双核智脑 (Dual-Core AI Brain)
- **DeepSeek (CIO 角色)**: 负责制定宏观策略，综合分析美债、汇率及行业趋势，给出最终的买卖建议。
- **Qwen (风控官 角色) [NEW]**: 引入 Qwen API 进行对抗性审查。当 DeepSeek 建议“激进加仓”时，Qwen 会基于实时舆情进行“反向压力测试”，确保决策稳健。

### 🔮 影子净值引擎 (Shadow NAV Engine)
- **持仓穿透**: 自动获取基金季报的前十大重仓股。
- **实时估值**: 并发抓取 A 股、港股、美股重仓股的实时报价，计算基金盘中涨跌幅。
- **T+0 决策**: 告别“盲买”，在收盘前 30 分钟预知当日净值。

### 🛡️ 双轨数据与容灾 (Dual-Source Data)
- **AkShare (主力)**: 覆盖 A 股全市场行情、资金流向、ETF 份额变动及新闻联播政策信号。
- **YFinance (辅助)**: 覆盖纳指、标普 500、黄金、原油及全球外汇数据。
- **自动切换**: 当某一数据源响应超时，系统自动切换至备用源，确保 14:30 任务必达。

### 🧬 策略进化与 RAG 记忆 (Evolution & RAG)
- **ChromaDB 向量库**: 存储历史研报、专家观点及过往的预测记录。
- **自我反思**: 系统会自动记录每日预测并在 5 天后回测。如果预测错误，AI 会强制进行“复盘反思”，并将教训写入长期记忆库。

## 🛠️ 技术架构 (Tech Stack)

| 模块 | 技术组件 | 职责 |
| :--- | :--- | :--- |
| **决策层** | `DeepSeek-V3`, `Qwen-Turbo` | 逻辑推理、策略生成、风险对抗 |
| **数据层** | `AkShare`, `YFinance`, `Pandas` | 行情获取、清洗、ETL |
| **计算层** | `TechnicalEngine` | 影子净值计算、均线形态识别、RSI/MACD 分析 |
| **记忆层** | `ChromaDB`, `SQLite` | 向量化知识库、策略回测数据库 |
| **舆情层** | `SentimentEngine` | 新闻联播关键词提取、市场热度逆向指标 |

## 🚀 快速开始 (Quick Start)

### 1. 环境准备
确保你的 Python 版本 >= 3.10。
```bash
git clone [https://github.com/your-repo/deepseek_finance_project.git](https://github.com/your-repo/deepseek_finance_project.git)
cd deepseek_finance_project_V3
pip install -r requirements.txt