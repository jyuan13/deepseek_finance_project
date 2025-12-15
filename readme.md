<div align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/AI-DeepSeek%20%7C%20Qwen-green.svg" alt="AI Models">
  <img src="https://img.shields.io/badge/Finance-AkShare%20%7C%20YFinance-orange.svg" alt="Data Sources">
  <img src="https://img.shields.io/badge/License-MIT-red.svg" alt="License">
</div>

# 🚀 DeepSeek Finance Project V3 (DSFP)

**DSFP V3** 是一个本地优先（Local-First）、高度模块化的智能金融分析系统。它结合了传统金融工程方法（如 RBSA、影子净值估算）与前沿的 AI 技术（DeepSeek LLM、RAG、Kronos 时序预测），旨在为个人投资者提供机构级的投资组合管理、风险监控和决策支持。

> **💡 核心理念**：数据私有化 · 分析透明化 · 决策智能化

---

## 📚 目录

- [核心功能](#-核心功能)
- [项目结构](#-项目结构与文件说明)
- [快速开始](#-快速开始)
- [后续开发计划 (Roadmap)](#-后续开发计划-roadmap)
- [免责声明](#-免责声明)

---

## ✨ 核心功能

### 1. 🔮 深度基金透视
* **影子净值 (Shadow NAV)**：不依赖滞后的官方净值，通过穿透持仓（支持港股/美股/A股）实时计算基金的估算净值。
* **RBSA (基于收益的风格分析)**：自动分析基金的历史收益序列，识别其真实的资产配置风格。
* **多轨行情数据**：集成 `AkShare` (A股/港股) 和 `YFinance` (美股/全球)，内置自动熔断和降级机制，确保数据高可用。

### 2. 🧠 智能 AI 分析师
* **Kronos 预测引擎**：基于 Transformer 的轻量级时序模型，对纳指、标普、黄金等 7 大核心资产进行 T+N 趋势预测。
* **Financial Brain (RAG)**：基于 `ChromaDB` 的检索增强生成系统，根据本地研报库和历史经验提供有据可依的分析。
* **自动 Prompt 构建**：根据宏观环境、技术指标和舆情动态，动态生成高质量的 LLM 提示词。

### 3. 🛡️ 风险与策略
* **Risk Guard (风控卫士)**：在生成建议前进行硬性风控审查（止损线、最大回撤、单一资产限额）。
* **策略进化引擎**：记录每一次决策的胜率，通过反馈循环（Feedback Loop）优化后续的分析策略。

### 4. 📰 全球舆情聚合
* 集成 `Finnhub`, `AlphaVantage`, `DuckDuckGo` 和 `AkShare` 新闻源，提供多维度的市场情绪分析。

---

## 📂 项目结构与文件说明

本项目采用模块化设计，逻辑分层如下：

### 🎮 核心入口与调度
| 文件名 | 说明 |
| :--- | :--- |
| `main.py` | **主程序入口**，提供 CLI 交互菜单，调度各子模块。 |
| `finance_analyzer.py` | **分析总线**，协调数据、模型、风控和 LLM，生成最终投资报告。 |

### 💾 数据层 (Data Layer)
* `data_provider.py`: **数据获取核心**，封装接口并实现多源降级/重试机制。
* `fund_data_manager.py`: **基金数据管家**，负责基金净值、持仓数据的缓存与读取。
* `data_manager.py`: **数据库接口**，管理 SQLite (`financial_data_v3.db`) 读写。
* `macro_analyzer.py`: **宏观分析器**，扫描全球指数、美债利率及流动性指标。

### ⚙️ 分析引擎 (Analysis Engines)
* `shadow_engine.py`: **影子净值引擎**，实时估算 ETF/基金 盘中净值。
* `technical_engine.py`: **技术分析引擎**，计算 MA, RSI, MACD 等指标。
* `rbsa_engine.py`: **风格分析引擎**，回归分析确定基金风格。
* `sentiment_engine.py`: **舆情引擎**，清洗和评分新闻数据。
* `risk_guard.py`: **风控模块**，执行交易前硬性规则检查。
* `strategy_evolution.py`: **策略进化**，基于历史胜率调整参数。

### 🤖 AI 与 LLM
* `deepseek_client.py`: **LLM 客户端**，适配 DeepSeek/OpenAI API。
* `kronos_adapter.py`: **时序预测适配器**，加载本地 Kronos 模型。
* `financial_brain.py`: **RAG 核心**，管理向量数据库与知识检索。
* `prompt_builder.py`: **提示词工厂**，组装结构化 Prompt。

---

## 🗺️ 后续开发计划 (Roadmap)

我们致力于将 **DSFP** 打造成一个多 Agent 协作的智能投研平台，未来的演进路线如下：

### Phase 1: 增强感知 (TrendRadar)
> 🎯 **目标**：从被动分析转向主动捕捉
-  **多源信息监控**：引入 TrendRadar 架构，整合社交媒体与传统财经流。
-  **实时推送与摘要**：全天候财经新闻自动抓取、清洗与 LLM 摘要。
-  **事件驱动信号**：基于特定关键词（如“加息”、“重组”）的交易信号触发。

### Phase 2: 多 Agent 架构 (Multi-Agent System)
> 🤖 **目标**：模拟真实的投研团队协作
-  📊 **数据分析师 Agent**：专注量化数据清洗、技术指标与基本面挖掘。
-  🌍 **宏观策略师 Agent**：专注全球流动性分析、央行政策与资产配置。
-  ⚖️ **交易执行官 Agent**：综合意见，计算买卖点位与定投计划。

### Phase 3: 对抗性审核 (Real-time Auditing)
> 🛡️ **目标**：降低 AI 幻觉风险
-  **引入 "审核师 (Auditor)"**：改变仅在最终阶段介入的模式，实现全流程监管。
-  **实时事实校验**：在数据获取、清洗、分析步骤进行数据源比对。
-  **逻辑对抗审查**：针对 AI 决策逻辑进行反向测试，确保严密性。

### Phase 4: 工程化与体验
> 💻 **目标**：提升交互体验与部署便捷性
-  **GUI 升级**：完善 `portfolio_gui.py`，提供现代化图形界面。
-  **跨平台打包**：使用 PyInstaller/Nuitka 打包为 `.exe` / `.app`。

