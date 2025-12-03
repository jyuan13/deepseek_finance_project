# 🚀 DeepSeek Finance Project V3
**版本**: V3.1-01 (Stable Build)
**定位**: 面向场外基金投资者的“私人 AI 首席投资官 (CIO)”
**核心架构**: 投资委员会 (Investment Committee) + 影子净值 (Shadow NAV) + Kronos 时序预测 + 多源双轨数据

---

## 📖 项目简介 (Introduction)

**DeepSeek Finance Project V3** 是一个专为场外基金与全球资产配置打造的**“机构级”个人量化系统**。

本项目不仅仅是一个数据面板，而是一个由 **CIO (DeepSeek/Qwen)**、**风控官 (RiskGuard)**、**量化研究员 (Kronos)** 和 **数据分析师 (Shadow Engine)** 组成的**虚拟投资委员会**。系统旨在解决个人投资者面临的三大痛点：

1.  **盲盒交易**：场外基金净值滞后，通过**Shadow NAV**实现盘中（14:30）精准决策。
2.  **数据孤岛**：整合 **AkShare、YFinance、Baostock** 等多源数据，打破单一接口限制。
3.  **幻觉风险**：多重风控 (Risk Guard) + RAG 记忆库，防止 AI “一本正经地胡说八道”。

---

## 🏗️ 系统架构与数据流 (System Architecture)

### 1. 全域感知层 (Multi-Source Data Layer)
* **双轨制 (Dual-Track)**: 核心数据均配备**主备接口**，自动降级，拒绝崩溃。
    * **A股/港股**: AkShare (主) + Baostock (备)。
    * **美股/宏观**: YFinance (实时) + AkShare (历史/备选)。
* **港股穿透**: 独创的 **ETF Mapping** 技术，穿透 QDII 联接基金，直连目标 ETF 实时行情 (00700, 09988 等)。
* **舆情监控**: 聚合新闻联播、财联社电报及 DuckDuckGo 搜索结果。

### 2. 硬核计算层 (Quant Engines)
* **🔮 影子净值引擎 (Shadow NAV)**:
    * **毫秒级快照**: 使用 `_hk_cache` 缓存技术，并发扫描 50+ 重仓股，计算 T+0 盘中涨跌幅。
    * **动态权重**: 自动清洗持仓数据，智能处理百分比格式，确保计算零误差。
* **🤖 Kronos 时序预测**:
    * **Transformer 模型**: 本地加载深度学习模型，预测纳斯达克/沪深300 的 T+1 走势。
    * **Realtime Injection**: 强制注入今日实时 K 线，消除预测滞后。
* **🛡️ 动态风控卫士**: 根据资产类型（股票/债券/混合）加载不同的止损与回撤阈值。

### 3. 双脑决策层 (Dual-Brain Decision)
* **AI 切换**: 支持 **DeepSeek** (深度推理) 和 **Qwen** (阿里百炼) 无缝切换。
* **Step Debugger**: 内置分步调试器，可单步执行“基础信息”、“影子净值”、“舆情”、“技术面”、“风控”等环节，透明化决策过程。

---

## 📅 更新日志 (Changelog)

### V3.1-01 (2025-12-03) - 重大更新
* **[修复] Shadow NAV 0% 问题**:
    * 新增 `_hk_cache` 港股全市场缓存，解决 50+ 只港股并发请求导致的超时封锁。
    * 新增 `etf_mapping`，完美支持 QDII 联接基金穿透。
    * 增加 `to_numeric` 强制类型转换，修复权重百分比字符串导致的计算错误。
* **[修复] Kronos 模型崩溃**:
    * 修复 Pandas `DatetimeIndex` 与 `Series` 的兼容性 Bug (`.dt` 属性错误)。
* **[新增] 分步调试模式 (Step Debugger)**:
    * 在主菜单新增 `5. 🐞 分步调试模式`，支持对任意基金的分析流程进行断点调试。
* **[新增] 宏观数据双轨制**:
    * 当 YFinance 提示 `Data Insufficient` 时，自动切换至 AkShare 新浪源，确保宏观数据 100% 可用。
* **[优化] 启动自检**:
    * 程序启动时自动检查并更新 `akshare` 和 `baostock` 库，防止接口过期。

---

## 🗺️ 后续计划 (Roadmap)

### 1. 功能完整性检查 (Integrity Check)
全面复查以下模块的边界情况与异常处理：
* 🔮 **持仓 & 影子净值**: 验证极端市场（如熔断、停牌）下的估值准确性。
* 📰 **舆情数据**: 优化新闻清洗逻辑，去除无关的个股通稿。
* 📈 **技术指标**: 引入更多因子（如 RSI, MACD, Bollinger Bands）。
* 🛡️ **风控检查**: 增加基于波动率 (ATR) 的动态止损。
* 🧠 **提示词生成**: 优化 Prompt 结构，减少 Token 消耗并提升指令依从性。

### 2. 多源数据融合 (Multi-Source Fusion)
进一步接入并深度集成以下 API，实现数据的交叉验证：
* **Baostock**: 作为 A 股历史数据的强力备份。
* **DuckDuckGo**: 增强海外标的（美股/QDII）的实时新闻搜索。
* **Finnhub / AlphaVantage / FMP**: 引入美股基本面数据（EPS、PE、财报日期），为价值投资提供依据。

### 3. 多角色 AI 委员会 (AI Agent Committee)
重构决策流程，将单一 LLM 拆解为多个独立 Agent，在每个处理环节介入审查：
* **🕵️ 数据清洗员 (Data Analyst Agent)**: 在 Step 1 & 2 介入，检查持仓数据是否异常（如权重之和 != 100%）。
* **⚖️ 舆情风控官 (Sentiment Officer Agent)**: 在 Step 3 介入，专门阅读新闻，给出 -10 到 +10 的情绪打分。
* **🛡️ 合规审查员 (Compliance Agent)**: 在 Step 5 介入，强制执行“铁律”（如：亏损超 10% 必须止损），拥有一票否决权。
* **👑 首席投资官 (CIO Agent)**: 仅在 Step 6 介入，综合上述所有 Agent 的报告做最终拍板。

---

## ⚠️ 免责声明
本项目仅供技术研究与学习使用，不构成任何投资建议。金融市场有风险，模型预测仅供参考，请根据自身风险承受能力独立决策。