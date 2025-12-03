# deepseek_finance_project_V3/operation_logger.py

import csv
import os
import json
from datetime import datetime, timedelta
import pandas as pd

class OperationLogger:
    def __init__(self, log_file='investment_operations.csv'):
        self.log_file = log_file
        self.ensure_log_file()
    
    def ensure_log_file(self):
        if not os.path.exists(self.log_file):
            self._write_header()
            print(f"✅ 已创建操作记录文件: {self.log_file}")
            
    def _write_header(self):
        """写入表头"""
        with open(self.log_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'date', 'symbol', 'action', 'amount', 
                'shares', 'price', 'reason', 
                'ai_confidence', 'notes', 'portfolio_snapshot'
            ])
    
    def clear_logs(self):
        """[新增] 清空操作日志"""
        try:
            self._write_header()
            print("✅ 操作日志已清空")
            return True
        except Exception as e:
            print(f"❌ 日志清空失败: {e}")
            return False
    
    def log_operation(self, operation_data):
        csv_row = [
            operation_data.get('date', datetime.now().strftime('%Y-%m-%d')),
            operation_data['symbol'],
            operation_data['action'],
            operation_data['amount'],
            operation_data.get('shares', ''),
            operation_data.get('price', ''),
            operation_data.get('reason', ''),
            operation_data.get('ai_confidence', ''),
            operation_data.get('notes', ''),
            operation_data.get('portfolio_snapshot', '')
        ]
        
        with open(self.log_file, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(csv_row)
        
        print(f"✅ 操作已记录: {operation_data['symbol']} {operation_data['action']} {operation_data['amount']}元")
        return True
    
    def quick_log_operation(self):
        print("\n📝 快速操作记录")
        print("=" * 40)
        
        from portfolio_manager import PortfolioManager
        portfolio_manager = PortfolioManager()
        portfolio = portfolio_manager.portfolio
        current_cash = portfolio.get('cash', 0)
        
        operation_data = {}
        operation_data['date'] = input(f"操作日期 (默认今天): ") or datetime.now().strftime('%Y-%m-%d')
        operation_data['symbol'] = input("标的代码: ").strip().upper()
        operation_data['action'] = input("操作类型 (BUY/SELL/DCA_BUY): ").strip().upper()
        
        try:
            operation_data['amount'] = float(input("操作金额 (元): "))
        except ValueError:
            print("❌ 请输入有效的金额")
            return
        
        shares = input("操作份额 (可选): ")
        operation_data['shares'] = int(shares) if shares else ""
        price = input("成交价格 (可选): ")
        operation_data['price'] = float(price) if price else ""
        operation_data['reason'] = input("操作原因: ")
        
        ai_suggested = input("是否AI建议? (y/n): ").lower()
        if ai_suggested == 'y':
            confidence = input("AI置信度 (0-1): ")
            operation_data['ai_confidence'] = float(confidence) if confidence else ""
        
        operation_data['notes'] = input("备注: ")
        
        snapshot = {
            "cash": current_cash,
            "positions": {}
        }
        for pos in portfolio.get('positions_config', []):
            snapshot['positions'][pos['symbol']] = pos['current_shares']
        
        operation_data['portfolio_snapshot'] = json.dumps(snapshot, ensure_ascii=False)
        self.log_operation(operation_data)
        
        update_portfolio = input("\n是否自动更新portfolio文件? (y/n): ").lower()
        if update_portfolio == 'y':
            self.update_portfolio_after_operation(operation_data, portfolio_manager)
        
        return operation_data
    
    def update_portfolio_after_operation(self, operation_data, portfolio_manager):
        symbol = operation_data['symbol']
        action = operation_data['action']
        amount = operation_data['amount']
        
        portfolio = portfolio_manager.portfolio
        
        if action in ['BUY', 'DCA_BUY']:
            portfolio['cash'] -= amount
            position_found = False
            for pos in portfolio.get('positions_config', []):
                if pos['symbol'] == symbol:
                    if operation_data.get('shares'):
                        pos['current_shares'] += operation_data['shares']
                    pos['last_buy_date'] = operation_data['date']
                    position_found = True
                    break
            
            if not position_found and operation_data.get('shares'):
                new_position = {
                    'symbol': symbol,
                    'current_shares': operation_data['shares'],
                    'cost_price': operation_data.get('price', 0),
                    'last_buy_date': operation_data['date'],
                    'target_percent': 5,
                    'investment_type': 'manual'
                }
                portfolio['positions_config'].append(new_position)
        
        elif action == 'SELL':
            portfolio['cash'] += amount
            for pos in portfolio.get('positions_config', []):
                if pos['symbol'] == symbol and operation_data.get('shares'):
                    pos['current_shares'] -= operation_data['shares']
                    break
        
        portfolio_manager.save_portfolio()
        print("✅ Portfolio文件已自动更新")
    
    def batch_log_operations(self):
        print("\n📦 批量操作记录")
        operations = []
        while True:
            print(f"\n记录第 {len(operations)+1} 条操作:")
            operation = self.quick_log_operation()
            if operation: operations.append(operation)
            if input("\n继续记录? (y/n): ").lower() != 'y': break
        return operations
    
    def get_recent_operations(self, days=30):
        try:
            df = pd.read_csv(self.log_file)
            if df.empty: return []
            
            # 类型安全转换
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
            df['shares'] = pd.to_numeric(df['shares'], errors='coerce').fillna(0)
            df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0.0)
            df['ai_confidence'] = pd.to_numeric(df['ai_confidence'], errors='coerce')
            
            df['date'] = pd.to_datetime(df['date'])
            cutoff = datetime.now() - timedelta(days=days)
            recent_ops = df[df['date'] >= cutoff]
            
            return recent_ops.where(pd.notnull(recent_ops), None).to_dict('records')
        except Exception as e:
            print(f"❌ 读取操作记录失败: {e}")
            return []
    
    def get_operation_stats(self, days=30):
        recent_ops = self.get_recent_operations(days)
        if not recent_ops: return {"total_operations": 0}
        
        total_invested = sum(op.get('amount', 0) for op in recent_ops if str(op.get('action')).upper() in ['BUY', 'DCA_BUY'])
        total_sold = sum(op.get('amount', 0) for op in recent_ops if str(op.get('action')).upper() == 'SELL')
        
        return {
            "period": f"最近{days}天",
            "total_operations": len(recent_ops),
            "total_invested": total_invested,
            "total_sold": total_sold,
            "net_cash_flow": total_invested - total_sold
        }