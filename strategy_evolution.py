import sqlite3
import json
import datetime
import yfinance as yf
from typing import Dict, Any, List, Optional
from deepseek_client import DeepSeekClient  # 假设您有这个客户端

class StrategyEvolutionEngine:
    """
    策略进化引擎 - 实现预测跟踪、验证和自我进化
    """
    
    def __init__(self, db_path='financial_memory.db', deepseek_client=None):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.deepseek_client = deepseek_client
        self._init_db()

    def _init_db(self):
        """初始化记忆库"""
        # 1. 预测记录表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                etf_name TEXT,
                input_snapshot TEXT,
                ai_outlook TEXT,
                confidence REAL,
                timeframe INTEGER DEFAULT 5,
                status TEXT DEFAULT 'pending',
                actual_change REAL,
                is_correct INTEGER
            )
        ''')
        
        # 2. 经验教训表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                topic TEXT,
                lesson_content TEXT,
                weight INTEGER DEFAULT 1,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0
            )
        ''')
        
        # 3. 性能统计表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                total_predictions INTEGER DEFAULT 0,
                correct_predictions INTEGER DEFAULT 0,
                accuracy REAL DEFAULT 0.0,
                last_updated TEXT
            )
        ''')
        
        self.conn.commit()

    def log_prediction(self, symbol: str, etf_name: str, input_data: Dict, ai_response: Dict):
        """
        记录AI预测
        """
        self.cursor.execute('''
            INSERT INTO predictions (timestamp, symbol, etf_name, input_snapshot, ai_outlook, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.datetime.now().isoformat(),
            symbol,
            etf_name,
            json.dumps(input_data, ensure_ascii=False),
            ai_response.get('outlook', 'Neutral'),
            ai_response.get('confidence', 0.5)
        ))
        self.conn.commit()
        print(f"✅ 预测已归档: {etf_name}({symbol}) -> {ai_response.get('outlook')}")

    def verify_predictions(self, days_ago: int = 5):
        """
        验证指定天数前的预测
        """
        target_date = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).strftime('%Y-%m-%d')
        
        self.cursor.execute('''
            SELECT id, symbol, etf_name, ai_outlook, input_snapshot 
            FROM predictions 
            WHERE date(timestamp) <= ? AND status = 'pending'
        ''', (target_date,))
        
        records = self.cursor.fetchall()
        results = []
        
        for record_id, symbol, etf_name, outlook, snapshot_json in records:
            # 获取实际涨跌幅
            actual_change = self._get_actual_return(symbol, days_ago)
            
            # 判断预测是否正确
            is_correct = self._evaluate_prediction(outlook, actual_change)
            
            # 更新预测记录
            self.cursor.execute('''
                UPDATE predictions 
                SET status = 'verified', actual_change = ?, is_correct = ?
                WHERE id = ?
            ''', (actual_change, 1 if is_correct else 0, record_id))
            
            # 更新性能统计
            self._update_performance_stats(symbol, is_correct)
            
            # 如果预测错误，触发反思
            if not is_correct:
                lesson = self._trigger_self_reflection(symbol, etf_name, outlook, actual_change, snapshot_json)
                if lesson:
                    results.append({
                        'symbol': symbol,
                        'predicted': outlook,
                        'actual': actual_change,
                        'lesson': lesson
                    })
            
            print(f"📊 复盘 {etf_name}: 预测{outlook}, 实际{actual_change:.2f}% -> {'✅' if is_correct else '❌'}")
        
        self.conn.commit()
        return results

    def _get_actual_return(self, symbol: str, days: int) -> float:
        """获取实际收益率"""
        try:
            # 处理A股代码适配
            if '.SH' in symbol:
                yf_symbol = symbol.replace('.SH', '.SS')
            elif '.SZ' in symbol:
                yf_symbol = symbol.replace('.SZ', '.SZ')
            else:
                yf_symbol = symbol
            
            # 获取足够的历史数据
            period_days = days + 10  # 多取几天以防数据缺失
            hist = yf.Ticker(yf_symbol).history(period=f"{period_days}d")
            
            if len(hist) < days + 1:
                return 0.0
            
            # 计算days天前的价格到最新价格的涨跌幅
            start_price = hist['Close'].iloc[-(days+1)]
            end_price = hist['Close'].iloc[-1]
            change_pct = (end_price / start_price - 1) * 100
            
            return change_pct
            
        except Exception as e:
            print(f"❌ 获取 {symbol} 实际收益失败: {e}")
            return 0.0

    def _evaluate_prediction(self, outlook: str, actual_change: float) -> bool:
        """评估预测准确性"""
        if outlook == 'Bullish':
            return actual_change > 0
        elif outlook == 'Bearish':
            return actual_change < 0
        else:  # Neutral
            return abs(actual_change) < 2.0  # 涨跌幅在2%以内算正确

    def _trigger_self_reflection(self, symbol: str, etf_name: str, predicted: str, 
                               actual_change: float, snapshot_json: str) -> Optional[str]:
        """
        触发AI自我反思 - 进化核心
        """
        if not self.deepseek_client:
            print("⚠️  DeepSeek客户端未配置，跳过反思")
            return None
            
        try:
            snapshot = json.loads(snapshot_json)
            
            reflection_prompt = f"""
## 🔍 系统复盘模式：从错误中学习

你之前对 **{etf_name} ({symbol})** 做出了错误的预测：

**预测方向**: {predicted}
**实际结果**: {actual_change:.2f}% (方向{( "相同" if (predicted == "Bullish" and actual_change > 0) or (predicted == "Bearish" and actual_change < 0) else "相反")})

### 📊 当时的数据上下文

**宏观环境**:
{json.dumps(snapshot.get('market_context', {}), ensure_ascii=False, indent=2)}

**ETF分析**:
{json.dumps(snapshot.get('etf_analysis', {}).get(symbol, {}), ensure_ascii=False, indent=2)}

**市场情绪**:
{json.dumps(snapshot.get('sentiment_data', {}), ensure_ascii=False, indent=2)}

### 🧠 反思要求

请深入分析这次预测错误的原因：

1. **关键误导因素**: 是哪个数据指标最具误导性？
2. **被忽视的信号**: 当时哪些重要信号被忽略了？
3. **突发变量**: 是否出现了未预料的外部事件？
4. **模式识别**: 这种错误模式在历史上是否重复出现？

**请总结一条具体的投资法则**，格式：
{{"insight": "根本原因分析", "rule": "具体的操作法则", "confidence_impact": "对置信度的影响"}}

请确保法则具体、可操作，避免泛泛而谈。
"""
            
            # 调用DeepSeek进行反思
            result = self.deepseek_client.chat(
                message=reflection_prompt,
                model_type="chat",
                system_prompt="你是一个严谨的量化分析师，擅长从错误中总结投资法则",
                use_history=False
            )
            
            if "content" in result:
                # 解析反思结果
                lesson_content = result["content"]
                
                # 存入经验库
                self.cursor.execute('''
                    INSERT INTO lessons (timestamp, topic, lesson_content)
                    VALUES (?, ?, ?)
                ''', (
                    datetime.datetime.now().isoformat(),
                    f"Error_{symbol}_{predicted}",
                    lesson_content
                ))
                
                self.conn.commit()
                print(f"🧬 系统进化: 新增经验法则")
                return lesson_content
                
        except Exception as e:
            print(f"❌ 反思过程出错: {e}")
            
        return None

    def _update_performance_stats(self, symbol: str, is_correct: bool):
        """更新性能统计"""
        # 获取现有统计
        self.cursor.execute('''
            SELECT total_predictions, correct_predictions 
            FROM performance_stats 
            WHERE symbol = ?
        ''', (symbol,))
        
        result = self.cursor.fetchone()
        
        if result:
            total, correct = result
            total += 1
            correct += 1 if is_correct else 0
            accuracy = correct / total if total > 0 else 0.0
            
            self.cursor.execute('''
                UPDATE performance_stats 
                SET total_predictions = ?, correct_predictions = ?, accuracy = ?, last_updated = ?
                WHERE symbol = ?
            ''', (total, correct, accuracy, datetime.datetime.now().isoformat(), symbol))
        else:
            self.cursor.execute('''
                INSERT INTO performance_stats (symbol, total_predictions, correct_predictions, accuracy, last_updated)
                VALUES (?, 1, ?, ?, ?)
            ''', (symbol, 1 if is_correct else 0, 1.0 if is_correct else 0.0, datetime.datetime.now().isoformat()))
        
        self.conn.commit()

    def get_accumulated_wisdom(self, limit: int = 10) -> List[str]:
        """获取积累的智慧法则"""
        self.cursor.execute('''
            SELECT lesson_content 
            FROM lessons 
            ORDER BY (success_count - failure_count) DESC, id DESC 
            LIMIT ?
        ''', (limit,))
        
        return [row[0] for row in self.cursor.fetchall()]

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        self.cursor.execute('''
            SELECT symbol, total_predictions, correct_predictions, accuracy
            FROM performance_stats
            ORDER BY accuracy DESC
        ''')
        
        stats = self.cursor.fetchall()
        
        total_predictions = sum(row[1] for row in stats)
        total_correct = sum(row[2] for row in stats)
        overall_accuracy = total_correct / total_predictions if total_predictions > 0 else 0.0
        
        return {
            'overall_accuracy': overall_accuracy,
            'total_predictions': total_predictions,
            'symbol_stats': [
                {
                    'symbol': row[0],
                    'total': row[1],
                    'correct': row[2],
                    'accuracy': row[3]
                } for row in stats
            ]
        }

    def close(self):
        """关闭数据库连接"""
        self.conn.close()