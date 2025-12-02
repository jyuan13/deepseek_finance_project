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
# 这里的 import 依赖于您已将 'model' 文件夹复制到项目根目录
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
    [V3.0-02] Kronos 预测适配器
    职责: 加载预训练模型 -> 预处理 K 线 -> 生成未来趋势预测
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
            # 自动从 HuggingFace 下载权重
            # NeoQuasar/Kronos-small (24M params) 适合个人电脑
            # NeoQuasar/Kronos-base (102M params) 效果更好但更慢
            repo_name = f"NeoQuasar/Kronos-{model_size}"
            tokenizer_repo = "NeoQuasar/Kronos-Tokenizer-base"
            
            print(f"   📥 加载 Tokenizer: {tokenizer_repo}")
            self.tokenizer = KronosTokenizer.from_pretrained(tokenizer_repo)
            
            print(f"   📥 加载 Model: {repo_name}")
            self.model = Kronos.from_pretrained(repo_name)
            self.model.to(self.device)
            
            # 实例化预测器
            # max_context=512 是 small/base 模型的限制
            self.predictor = KronosPredictor(self.model, self.tokenizer, device=self.device, max_context=512)
            print("   ✅ Kronos 加载完成")
            
        except Exception as e:
            print(f"   ❌ Kronos 加载失败: {e}")
            self.is_active = False

    def predict_trend(self, df_kline: pd.DataFrame, pred_len=24):
        """
        预测未来趋势
        :param df_kline: 包含 open, high, low, close, volume 的 DataFrame (标准格式)
        :param pred_len: 预测未来多少个周期 (如日线就是未来24天，分钟线就是24分钟)
        :return: (trend_desc, confidence_score, forecast_df)
        """
        if not self.is_active or df_kline.empty:
            return "模型未就绪", 0.0, None
            
        try:
            # 1. 数据格式适配
            # Kronos 需要: open, high, low, close (volume 可选)
            # 确保列名小写
            df = df_kline.copy()
            df.columns = [c.lower() for c in df.columns]
            
            # 确保有必要的列
            required = ['open', 'high', 'low', 'close']
            if not all(c in df.columns for c in required):
                return "数据列缺失", 0.0, None
                
            # 确保有 timestamps 列 (KronosPredictor 需要)
            if 'date' in df.columns:
                df['timestamps'] = pd.to_datetime(df['date'])
            else:
                # 如果没有时间列，生成伪时间
                df['timestamps'] = pd.date_range(start="2020-01-01", periods=len(df), freq="D")

            # 2. 截取上下文
            # Kronos 最大上下文 512，我们取最近 400 条作为输入
            lookback = min(len(df), 400)
            if lookback < 50:
                return "历史数据不足", 0.0, None
                
            # 切片：取最后 lookback 条作为 Input
            # 实际上 KronosPredictor 的用法需要构造 x_df, x_timestamp, y_timestamp
            
            # 准备 Input Data
            x_df = df.iloc[-lookback:].reset_index(drop=True)
            x_timestamp = x_df['timestamps']
            
            # 准备 Output Timestamp (未来的时间点)
            last_time = x_timestamp.iloc[-1]
            y_timestamp = pd.date_range(start=last_time + pd.Timedelta(days=1), periods=pred_len, freq="D")
            
            # 3. 执行推理 (Inference)
            # sample_count=1 (确定性预测), T=0.8 (降低随机性)
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
            
            # 4. 解析结果
            # pred_df 包含预测的 OHLCV
            # 我们计算简单的趋势：预测期末收盘价 vs 当前收盘价
            current_close = x_df.iloc[-1]['close']
            pred_close_avg = pred_df['close'].mean() # 预测期的平均收盘价
            pred_close_final = pred_df['close'].iloc[-1] # 预测期末的收盘价
            
            chg_pct = ((pred_close_final - current_close) / current_close) * 100
            
            trend = "震荡"
            if chg_pct > 2.0: trend = "看涨 (Bullish)"
            elif chg_pct < -2.0: trend = "看跌 (Bearish)"
            
            # 简单的置信度 (基于波动率)
            volatility = pred_df['close'].std() / pred_close_avg
            confidence = max(0.1, 1.0 - volatility*5) # 波动越大置信度越低
            
            desc = f"{trend}, 预期涨幅 {chg_pct:.2f}%"
            return desc, round(confidence, 2), pred_df
            
        except Exception as e:
            print(f"⚠️ Kronos 推理出错: {e}")
            import traceback
            traceback.print_exc()
            return f"推理错误: {str(e)}", 0.0, None

if __name__ == "__main__":
    # 测试代码
    adapter = KronosAdapter(model_size="small")
    if adapter.is_active:
        # 造一点假数据测试
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
        res, conf, _ = adapter.predict_trend(df)
        print(f"预测结果: {res} (置信度: {conf})")