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
- **实时估值**: 并