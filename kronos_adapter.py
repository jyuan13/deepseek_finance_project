# deepseek_finance_project_V3/kronos_adapter.py

import torch
import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys

# [修复] 显式添加当前目录到 sys.path，确保能找到 model 文件夹
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 尝试导入 Kronos 模型
try:
    from model import Kronos, KronosTokenizer, KronosPredictor
    print("✅ 成功导入本地 Kronos 模型库")
    KRONOS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 未检测到 'model' 模块或导入失败: {e}")
    print(f"   当前搜索路径: {sys.path}")
    print(f"   请确认 deepseek_finance_project_V3/model/ 文件夹是否存在且包含 __init__.py")
    KRONOS_AVAILABLE = False

class KronosAdapter:
    """
    [V3.0-11] Kronos 预测适配器 (NaN Proof Edition)
    职责: 加载预训练模型 -> 预处理 K 线 -> 生成未来趋势预测
    更新: 
    1. 实施焦土式数据清洗，确保 Volume 列绝对无 NaN。
    2. 增加最终防线，防止模型推理因数据问题崩溃。
    """
    
    def __init__(self, model_size="small", device=None):
        self.is_active = KRONOS_AVAILABLE
        if not self.is_active:
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
            
            self.predictor = KronosPredictor(self.model, self.tokenizer, device=self.device, max_context=512)
            print("   ✅ Kronos 加载完成")
            
        except Exception as e:
            print(f"   ❌ Kronos 加载失败: {e}")
            self.is_active = False

    def predict_trend(self, df_kline: pd.DataFrame, pred_len=5, debug=False):
        """
        预测未来趋势
        """
        if not self.is_active or df_kline.empty:
            return "模型未就绪", 0.0, None
            
        try:
            # 1. 数据格式适配
            df = df_kline.copy()
            df.columns = [c.lower() for c in df.columns]
            
            required = ['open', 'high', 'low', 'close']
            if not all(c in df.columns for c in required):
                return "数据列缺失", 0.0, None
                
            if 'date' in df.columns:
                df['timestamps'] = pd.to_datetime(df['date'])
            else:
                df['timestamps'] = pd.date_range(start="2020-01-01", periods=len(df), freq="D")

            # 2. 截取上下文 (最大 512，取最近 400)
            lookback = min(len(df), 400)
            if lookback < 50:
                return "历史数据不足", 0.0, None
                
            x_df = df.iloc[-lookback:].reset_index(drop=True)
            x_timestamp = x_df['timestamps']

            # [Fix Ultimate] 焦土式清洗
            
            # A. 确保 Volume 存在且无 NaN/Inf
            if 'volume' not in x_df.columns:
                x_df['volume'] = 0.0
            
            x_df['volume'] = pd.to_numeric(x_df['volume'], errors='coerce')
            x_df['volume'] = x_df['volume'].fillna(0)
            x_df['volume'] = x_df['volume'].replace([np.inf, -np.inf], 0)

            # B. 清洗价格列 (Open/High/Low/Close)
            for col in ['open', 'high', 'low', 'close']:
                x_df[col] = pd.to_numeric(x_df[col], errors='coerce')
                # 价格不应为0或Inf，视为缺失
                x_df[col] = x_df[col].replace([np.inf, -np.inf, 0], np.nan)
                # 前向填充 + 后向填充
                x_df[col] = x_df[col].ffill().bfill()
            
            # C. 最终行级清洗 (如果某行价格全空，丢弃)
            x_df = x_df.dropna(subset=['open', 'high', 'low', 'close'])
            
            # D. 最后一道防线：如果仍有遗漏的 NaN (理论上不应有)，强制填0，防止报错
            if x_df.isnull().values.any():
                x_df = x_df.fillna(0)

            if x_df.empty or len(x_df) < 10:
                return "数据无效(清洗后过短)", 0.0, None

            if debug:
                print(f"\n🐛 [Kronos Debug] 输入数据概览 (Context Len: {len(x_df)}):")
                print("   Input Tail (Last 5 rows):")
                print(x_df[['date', 'open', 'close', 'high', 'low']].tail(5).to_string(index=False))
                print("-" * 50)
            
            last_time = x_timestamp.iloc[-1]
            y_timestamp = pd.date_range(start=last_time + pd.Timedelta(days=1), periods=pred_len, freq="D")
            
            # 3. 执行推理
            pred_df = self.predictor.predict(
                df=x_df,
                x_timestamp=x_timestamp,
                y_timestamp=y_timestamp,
                pred_len=pred_len,
                T=0.8, 
                top_p=0.9,
                sample_count=1,
                verbose=False
            )
            
            # 4. 核心计算 (T+1 Logic)
            current_close = x_df.iloc[-1]['close']
            
            pred_df['date'] = y_timestamp
            pred_df['cum_pct_chg'] = ((pred_df['close'] - current_close) / current_close) * 100
            
            target_close = pred_df['close'].iloc[0] 
            pred_close_avg = pred_df['close'].mean()
            
            chg_pct = ((target_close - current_close) / current_close) * 100
            
            trend = "震荡"
            if chg_pct > 1.0: trend = "看涨 (Bullish)"  
            elif chg_pct < -1.0: trend = "看跌 (Bearish)"
            
            # 5. 置信度计算
            if len(pred_df) > 1:
                pred_std = pred_df['close'].std()
                volatility = pred_std / pred_close_avg
            else:
                pred_std = 0.0
                volatility = 0.0
            
            raw_confidence = 1.0 - volatility * 5
            confidence = max(0.1, min(0.95, raw_confidence))
            
            if debug:
                print(f"🐛 [Kronos Debug] 预测序列 (Pred Len: {len(pred_df)}):")
                print(pred_df[['date', 'close', 'cum_pct_chg']].to_string())
                print(f"   Target(T+1): {target_close:.2f} (Base: {current_close:.2f})")
                print(f"   Stats: Mean={pred_close_avg:.2f}, Std={pred_std:.4f}, Volatility={volatility:.4f}")
                print(f"   Calc: 1.0 - {volatility:.4f}*5 = {raw_confidence:.4f} -> Final Conf: {confidence}")
                print("-" * 50)
            
            desc = f"{trend}, 预期涨幅 {chg_pct:.2f}%"
            return desc, round(confidence, 2), pred_df[['date', 'close', 'cum_pct_chg']]
            
        except Exception as e:
            print(f"⚠️ Kronos 推理出错: {e}")
            import traceback
            traceback.print_exc()
            return f"推理错误: {str(e)}", 0.0, None

if __name__ == "__main__":
    adapter = KronosAdapter(model_size="small")
    if adapter.is_active:
        dates = pd.date_range(end=datetime.now(), periods=100)
        data = {
            'date': dates,
            'open': np.random.rand(100) * 10 + 100,
            'high': np.random.rand(100) * 10 + 110,
            'low': np.random.rand(100) * 10 + 90,
            'close': np.random.rand(100) * 10 + 100,
            'volume': np.random.rand(100) * 1000
        }
        df = pd.DataFrame(data)
        res, conf, pdf = adapter.predict_trend(df, pred_len=5, debug=True)
        print(f"预测结果: {res} (置信度: {conf})")