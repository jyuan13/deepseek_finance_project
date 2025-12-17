# deepseek_finance_project_V3/kronos_adapter.py

"""
==========================================================================================
【文件定义】
文件名: kronos_adapter.py
类名  : KronosAdapter
==========================================================================================
【函数清单与逻辑流 (Function Logic Flow)】

1. __init__(model_size, device)
   [环境设置] -> [添加 sys.path] -> [检测 CUDA]
          ↓
   [尝试导入 model.Kronos] -> (成功: 加载 Tokenizer/Model) / (失败: 标记不可用)

2. predict(symbol, history_df)
   [输入校验] -> [调用 _predict_real_logic] -> [返回标准化结果]

3. _predict_real_logic(df_kline, pred_len)
   [列名标准化] -> [焦土式数据清洗 (DropNa/FillZero/Inf)] 
          ↓
   [截取 Context (Max 512)] -> [调用 self.predictor.predict 执行推理]
          ↓
   [生成 T+1~T+5 序列] -> [计算波动率与置信度] -> [返回详情列表]
==========================================================================================
"""

import torch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# [关键] 显式添加当前目录到 sys.path，确保能找到 model 文件夹
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 尝试导入 Kronos 模型
try:
    from model import Kronos, KronosTokenizer, KronosPredictor
    KRONOS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 未检测到 'model' 模块或导入失败: {e}")
    KRONOS_AVAILABLE = False

class KronosAdapter:
    """
    [V4.07 Real Engine] Kronos 预测适配器 (Full PyTorch Version)
    职责: 加载真实预训练模型 -> 严苛数据清洗 -> 生成未来5日趋势
    """
    
    def __init__(self, model_size="small", device=None):
        self.is_active = KRONOS_AVAILABLE
        if not self.is_active:
            print("❌ Kronos 依赖缺失，进入被动模式。")
            return

        # 自动检测设备
        if device:
            self.device = device
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
        print(f"🔧 初始化 Kronos ({model_size}) on {self.device}...")
        
        try:
            repo_name = f"NeoQuasar/Kronos-{model_size}"
            tokenizer_repo = "NeoQuasar/Kronos-Tokenizer-base"
            
            print(f"   📥 加载 Tokenizer: {tokenizer_repo}")
            self.tokenizer = KronosTokenizer.from_pretrained(tokenizer_repo)
            
            print(f"   📥 加载 Model: {repo_name}")
            self.model = Kronos.from_pretrained(repo_name)
            self.model.to(self.device)
            
            # 初始化预测器
            self.predictor = KronosPredictor(self.model, self.tokenizer, device=self.device, max_context=512)
            print("   ✅ Kronos 引擎加载完成")
            
        except Exception as e:
            print(f"   ❌ Kronos 模型加载失败: {e}")
            self.is_active = False

    def predict(self, symbol, history_df=None):
        """
        统一对外接口，返回 (summary, conf, details_list)
        """
        if not self.is_active or history_df is None or history_df.empty:
            return "模型未就绪或数据为空", 0.0, []

        try:
            # 调用真实推理逻辑，预测未来 5 天
            pred_df, confidence = self._predict_real_logic(history_df, pred_len=5)
            
            if pred_df is None or pred_df.empty:
                return "数据清洗后不足或推理失败", 0.0, []

            # 格式化输出结果
            predictions = []
            base_price = float(history_df.iloc[-1]['close']) if 'close' in history_df.columns else 100.0
            
            for i, row in pred_df.iterrows():
                # 计算相对于基准日（T+0）的累计涨跌幅
                # 注意：_predict_real_logic 返回的 close 是预测的绝对价格
                pred_price = float(row['close'])
                chg_pct = ((pred_price - base_price) / base_price) * 100
                
                predictions.append({
                    "name": symbol,
                    "date": f"T+{i+1} ({row['date'].strftime('%m-%d')})",
                    "close": f"{pred_price:.2f}",
                    "chg": f"{chg_pct:+.2f}%",
                    "conf": confidence  # 使用序列整体置信度
                })

            # 生成摘要 (基于 T+1)
            t1 = predictions[0]
            t1_chg = float(t1['chg'].strip('%'))
            direction = "看涨" if t1_chg > 0 else "看跌"
            if abs(t1_chg) < 0.5: direction = "震荡"
            
            summary = f"{symbol} | T+1: {direction}, 预期 {t1['chg']} | Conf: {confidence:.2f}"
            
            return summary, confidence, predictions

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"推理异常: {str(e)}", 0.0, []

    def _predict_real_logic(self, df_kline: pd.DataFrame, pred_len=5):
        """
        [Core] 执行真实的数据清洗和模型推理
        """
        # 1. 数据列标准化
        df = df_kline.copy()
        df.columns = [c.lower() for c in df.columns]
        
        # 2. 焦土式数据清洗 (Scorched Earth Cleaning)
        # 确保 volume 存在且无 NaN/Inf
        if 'volume' not in df.columns:
            df['volume'] = 0.0
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).replace([np.inf, -np.inf], 0)

        # 清洗价格列
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if col not in df.columns:
                # 缺失列尝试用 close 补全
                if 'close' in df.columns: df[col] = df['close']
                else: return None, 0.0
            
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].replace([np.inf, -np.inf, 0], np.nan)
            df[col] = df[col].ffill().bfill() # 前向+后向填充

        # 最终行级清洗
        df = df.dropna(subset=price_cols)
        
        if len(df) < 30: # 长度不足
            print("   ⚠️ 历史数据过短，无法推理")
            return None, 0.0

        # 3. 构造上下文
        # 补充 timestamp 列供模型使用
        if 'date' in df.columns:
            # 尝试解析多种日期格式
            try:
                df['timestamps'] = pd.to_datetime(df['date'])
            except:
                df['timestamps'] = pd.date_range(end=datetime.now(), periods=len(df), freq="D")
        else:
            df['timestamps'] = pd.date_range(end=datetime.now(), periods=len(df), freq="D")

        # 截取最近窗口 (模型限制)
        lookback = min(len(df), 400)
        x_df = df.iloc[-lookback:].reset_index(drop=True)
        x_timestamp = x_df['timestamps']

        last_time = x_timestamp.iloc[-1]
        y_timestamp = pd.date_range(start=last_time + timedelta(days=1), periods=pred_len, freq="D")

        # 4. 模型推理
        try:
            # 调用内部 predictor
            # 参数说明: T=temperature(采样多样性), top_p=核采样
            pred_df = self.predictor.predict(
                df=x_df,
                x_timestamp=x_timestamp,
                y_timestamp=y_timestamp,
                pred_len=pred_len,
                T=0.7,      # 降低随机性，求稳
                top_p=0.85,
                sample_count=1,
                verbose=False
            )
            
            # 5. 计算置信度 (基于预测序列的平滑度)
            # 如果预测结果剧烈波动，说明模型不确定；平滑则置信度高
            changes = pred_df['close'].pct_change().dropna().abs()
            volatility = changes.mean() if not changes.empty else 0.01
            
            # 简单的置信度映射: 波动越小，置信度越高 (Max 0.95)
            confidence = max(0.5, 0.95 - (volatility * 10))
            
            # 将生成的 timestamp 赋回去
            pred_df['date'] = y_timestamp
            
            return pred_df, confidence

        except Exception as e:
            print(f"   ⚠️ 推理层报错: {e}")
            return None, 0.0

if __name__ == "__main__":
    # 单元测试
    adapter = KronosAdapter(model_size="small")
    if adapter.is_active:
        # 造假数据测试
        dates = pd.date_range(end=datetime.now(), periods=100)
        data = {
            'date': dates,
            'open': np.linspace(100, 120, 100) + np.random.normal(0, 1, 100),
            'close': np.linspace(100, 120, 100) + np.random.normal(0, 1, 100),
            'high': np.linspace(105, 125, 100),
            'low': np.linspace(95, 115, 100),
            'volume': np.random.rand(100) * 1000
        }
        df = pd.DataFrame(data)
        
        print("\n🔎 开始测试预测...")
        summary, conf, details = adapter.predict("TEST_SIM", df)
        print(f"摘要: {summary}")
        print("详情:")
        for d in details:
            print(d)