# 📘 DeepSeek Finance Project V2 (Current Architecture Snapshot)

**版本状态**: V2.0 (Internal Code V5.0)
**核心定位**: 基于 LLM + RAG 的全天候场外基金智能投顾系统
**最后更新**: 2025

---

## 1. 项目概述 (Project Overview)

本项目是一个高度自动化的个人量化投顾系统，旨在解决场外基金“净值滞后”和“决策缺乏依据”的两大痛点。系统集成了 **DeepSeek 大模型** 作为决策大脑，辅以 **AkShare/YFinance 双轨数据源**，并拥有 **RAG (检索增强生成)** 记忆能力，能够进行宏观分析、持仓穿透、技术面诊断及舆情监控。

### 核心解决问题
1.  **盲盒交易**: 通过穿透基金持仓计算“影子净值 (Shadow NAV)”，在 14:30 预测当日涨跌。
2.  **数据孤岛**: 综合宏观（美债/汇率）、中观（行业热度）、微观（K线形态）多维数据。
3.  **记忆缺失**: 通过向量数据库 (ChromaDB) 存储研报和历史经验，避免 AI "狗熊掰棒子"。
4.  **策略僵化**: 具备“策略进化引擎”，能记录预测结果并进行反思迭代。

---

## 2. 系统架构 (System Architecture)

系统采用模块化设计，以 `finance_analyzer.py` 为中枢，向下调用各专业引擎，向上对接 DeepSeek API。

```mermaid
graph TD
    User[用户] --> Main[main.py (CLI入口)]
    Main --> Analyzer[finance_analyzer.py (分析中枢)]
    
    subgraph "Data Layer (数据感知)"
        DataMgr[fund_data_manager.py] --> AkShare[AkShare API]
        TechEng[technical_engine.py] --> YFinance[YFinance API]
        Macro[macro_analyzer.py] --> FRED[FRED/Bond Data]
        Senti[sentiment_engine.py] --> EastMoney[东方财富/财联社]
    end
    
    subgraph "Memory Layer (记忆存储)"
        RAG[financial_brain.py] --> ChromaDB[(Chroma Vector DB)]
        Evo[strategy_evolution.py] --> SQLite[(Financial Memory DB)]
        Port[portfolio_manager.py] --> JSON[Portfolio Config]
    end
    
    subgraph "Brain Layer (决策大脑)"
        Analyzer --> Prompt[prompt_builder.py]
        Prompt --> DeepSeek[DeepSeek API]
        DeepSeek --> Decision[投资建议]
    end

    Analyzer --> DataMgr
    Analyzer --> TechEng
    Analyzer --> Macro
    Analyzer --> Senti
    Analyzer --> RAG
    Analyzer --> Evo