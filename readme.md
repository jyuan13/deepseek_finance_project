# 📊 DeepSeek 金融分析系统 (V5 增强版)

> **全维度智能投顾引擎**：集成宏观、技术、舆情、资金流与 RAG 记忆进化的 Python 量化分析系统。

## 🚀 项目简介

本项目是一个基于 DeepSeek 大模型（LLM）的自动化金融分析系统。V5 版本在原版基础上进行了深度重构，引入了**双轨数据源验证**、**RAG 检索增强生成**以及**AI 策略自我进化**机制，旨在提供更准确、更具深度的市场洞察。

## ✨ 核心特性

### 1. 🛡️ 双轨数据引擎 (Dual-Source)
- **多源验证**：同时接入 **YFinance** (全球行情) 和 **AkShare** (A股/港股深度数据)。
- **自动兜底**：当某一接口失效或被封锁时，自动切换至备用源。
- **数据裁判**：自动比对双源数据偏差，确保 K 线和技术指标的准确性。

### 2. 🧠 RAG 金融大脑 (Financial Brain)
- **研报知识库**：支持导入 PDF 研报或自动抓取顶级投行（摩根、高盛等）观点，存入本地向量数据库 (ChromaDB)。
- **上下文感知**：AI 在分析时会自动检索相关的历史研报和专家观点，拒绝“幻觉”。

### 3. 🧬 策略进化引擎 (Evolution)
- **闭环学习**：自动记录每日预测 -> 5天后自动回测验证 -> 错误时触发反思模式。
- **经验沉淀**：将反思总结出的“投资法则”存入数据库，下次分析时自动调用，避免重蹈覆辙。

### 4. 🔮 全维度扫描 (V5 Pipeline)
- **宏观 (Macro)**：监控美债收益率、美元指数、中美利差、跨境资金流向。
- **暗流 (Dark Flow)**：探测获利盘筹码分布、做空比例等隐蔽信号。
- **舆情 (Sentiment)**：抓取新闻联播政策信号、财联社快讯及散户热度逆向指标。
- **技术 (Technical)**：多周期 K 线形态识别、均线系统、RSI/MACD 背离分析。

## 📂 项目结构

```text
deepseek_finance_project_V2/
├── main.py                 # 主程序入口
├── finance_analyzer.py     # 业务控制中心 (V5 Pipeline)
├── technical_engine.py     # [核心] 双轨行情获取与指标计算
├── financial_brain.py      # [核心] RAG 向量数据库管理
├── strategy_evolution.py   # [核心] 预测记录与进化反思
├── sentiment_engine.py     # 舆情与新闻爬虫
├── macro_analyzer.py       # 宏观经济数据分析
├── dark_flow_detector.py   # 筹码与做空数据分析
├── etf_holdings.py         # ETF 持仓管理 (支持动态更新)
├── prompt_builder.py       # 提示词工程构建器
├── brain_memory/           # ChromaDB 向量数据库存储目录
└── financial_memory.db     # SQLite 策略进化数据库