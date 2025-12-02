# deepseek_finance_project_V3/portfolio_manager.py

import json
import os
import re
from datetime import datetime
import pandas as pd

class PortfolioManager:
    def __init__(self, portfolio_file='my_portfolio.json'):
        self.portfolio_file = portfolio_file
        self.portfolio = self.load_portfolio()
    
    def load_portfolio(self):
        """加载投资组合配置"""
        if not os.path.exists(self.portfolio_file):
            return self._create_default_portfolio()
        
        try:
            with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载投资组合文件失败: {e}")
            return {}

    def _create_default_portfolio(self):
        """创建默认配置"""
        default_portfolio = {
            "cash": 100000,
            "total_assets": 100000,
            "risk_profile": "balanced",
            "cash_reserve_ratio": 0.1,
            "investment_strategies": {
                "dca_enabled": True,
                "weekly_investment_day": "Monday"
            },
            "positions_config": []
        }
        self.save_portfolio(default_portfolio)
        return default_portfolio
    
    def save_portfolio(self, portfolio=None):
        """保存投资组合配置"""
        if portfolio is None:
            portfolio = self.portfolio
        try:
            with open(self.portfolio_file, 'w', encoding='utf-8') as f:
                json.dump(portfolio, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 保存投资组合文件失败: {e}")
            return False
            
    def reset_portfolio(self):
        """重置投资组合为初始状态"""
        self.portfolio = self._create_default_portfolio()
        self.save_portfolio()
        print("✅ 投资组合已重置为默认状态 (现金: 100,000)")
        return True
    
    def get_current_positions(self):
        return self.portfolio.get('positions_config', [])
    
    def get_cash_balance(self):
        return self.portfolio.get('cash', 0)
    
    def update_position(self, symbol, shares, cost_price=None, update_date=None, max_invest_limit=None):
        """[V3.9] 更新持仓信息，包括限额"""
        if update_date is None:
            update_date = datetime.now().strftime('%Y-%m-%d')
        
        position_found = False
        for position in self.portfolio['positions_config']:
            if position['symbol'] == symbol:
                position['current_shares'] = float(shares) # [修复] 确保是 float
                position['last_buy_date'] = update_date
                if cost_price is not None:
                    position['cost_price'] = float(cost_price)
                if max_invest_limit is not None:
                    position['max_invest_limit'] = float(max_invest_limit)
                position_found = True
                break
        
        if not position_found and shares > 0:
            new_position = {
                'symbol': symbol,
                'current_shares': float(shares),
                'cost_price': float(cost_price) if cost_price else 0.0,
                'last_buy_date': update_date,
                'target_percent': 5,
                'deviation_limit': 3,
                'min_threshold': 1,
                'investment_type': 'manual',
                'max_invest_limit': float(max_invest_limit) if max_invest_limit else 0.0
            }
            self.portfolio['positions_config'].append(new_position)
        
        self.save_portfolio()
        print(f"✅ 已更新持仓: {symbol} -> {shares}份 (限额: {max_invest_limit if max_invest_limit else '无'})")
    
    def update_cash(self, new_cash_balance):
        self.portfolio['cash'] = float(new_cash_balance)
        self.save_portfolio()
        print(f"✅ 现金余额已更新: {new_cash_balance}元")
    
    def add_new_position_config(self, symbol, target_percent=5, deviation_limit=3, 
                               investment_type='manual', dca_config=None, max_invest_limit=0):
        """[V3.9] 添加新配置，支持限额"""
        for position in self.portfolio['positions_config']:
            if position['symbol'] == symbol:
                print(f"⚠️  {symbol} 的配置已存在")
                return False
        
        new_position = {
            'symbol': symbol,
            'current_shares': 0.0,
            'cost_price': 0.0,
            'last_buy_date': '',
            'target_percent': float(target_percent),
            'deviation_limit': float(deviation_limit),
            'min_threshold': 1,
            'investment_type': investment_type,
            'max_invest_limit': float(max_invest_limit)
        }
        
        if dca_config and investment_type in ['dca_fixed', 'dca_intelligent']:
            new_position['dca_config'] = dca_config
        
        self.portfolio['positions_config'].append(new_position)
        self.save_portfolio()
        print(f"✅ 已添加持仓配置: {symbol} (单日限额: {max_invest_limit})")
        return True
    
    def _validate_symbol_format(self, symbol):
        """校验代码格式"""
        symbol = symbol.upper().strip()
        if symbol.endswith(('.SS', '.SH', '.SZ', '.HK', '.TW')):
            return True, "格式正确"
        if symbol.isdigit():
            if len(symbol) == 6:
                return True, "A股代码 (建议添加 .SS/.SZ 后缀以防歧义)"
            elif 4 <= len(symbol) <= 5:
                return True, "港股代码 (建议添加 .HK 后缀)"
            else:
                return False, f"⚠️  纯数字代码长度({len(symbol)}位)不符合常规"
        if symbol.isalpha():
            return True, "美股代码"
        if symbol.startswith('^'):
            return True, "指数代码"
        return False, "⚠️  代码格式异常"

    def get_position_pnl(self, symbol, current_price):
        for pos in self.portfolio['positions_config']:
            if pos['symbol'] == symbol:
                shares = pos.get('current_shares', 0)
                cost = pos.get('cost_price', 0)
                if shares > 0 and cost > 0 and current_price > 0:
                    market_value = shares * current_price
                    cost_value = shares * cost
                    pnl_amount = market_value - cost_value
                    pnl_pct = (pnl_amount / cost_value) * 100
                    return pnl_amount, pnl_pct
        return 0.0, 0.0

    def get_position_valuation(self, symbol, current_price):
        for pos in self.portfolio['positions_config']:
            if pos['symbol'] == symbol:
                shares = pos.get('current_shares', 0)
                if shares > 0:
                    return shares * current_price
        return 0.0
        
    def get_portfolio_summary(self):
        return {
            'cash_balance': self.get_cash_balance(),
            'positions': self.get_current_positions(),
            'risk_profile': self.portfolio.get('risk_profile', 'balanced')
        }

    def manage_portfolio(self):
        """交互管理界面"""
        print("\n💼 投资组合管理")
        print("=" * 40)
        while True:
            print(f"\n现金余额: {self.get_cash_balance():.2f}元")
            print("当前持仓:")
            positions = self.get_current_positions()
            if positions:
                for pos in positions:
                    limit_str = f"限额:{pos.get('max_invest_limit', 0)}" if pos.get('max_invest_limit') else "无限制"
                    if pos['current_shares'] > 0:
                        print(f"  - {pos['symbol']}: {pos['current_shares']}份 (目标:{pos.get('target_percent',0)}% | {limit_str})")
            else:
                print("  - 暂无持仓")
            
            print("\n1. 更新现金余额")
            print("2. 更新持仓份额/限额")
            print("3. 添加新标的配置")
            print("4. 查看详细配置")
            print("0. 返回主菜单")
            
            choice = input("请选择操作: ").strip()
            
            if choice == "1":
                try:
                    new_cash = float(input("新的现金余额: "))
                    self.update_cash(new_cash)
                except ValueError: print("❌ 无效数字")
            
            elif choice == "2":
                symbol = input("标的代码 (如 513120.SS): ").strip().upper()
                is_valid, msg = self._validate_symbol_format(symbol)
                if not is_valid:
                    print(msg)
                    if input("确认继续? (y/n): ").lower() != 'y': continue

                try:
                    shares = float(input("持有份额: ")) # [修复] 支持小数
                    cost_price = input("成本价 (回车跳过): ")
                    cost = float(cost_price) if cost_price else None
                    
                    limit_input = input("单日最大买入限额 (0表示无限制, 回车跳过): ")
                    limit = float(limit_input) if limit_input else None
                    
                    self.update_position(symbol, shares, cost, max_invest_limit=limit)
                except ValueError: print("❌ 无效数字")
            
            elif choice == "3":
                symbol = input("标的代码: ").strip().upper()
                try:
                    target = float(input("目标配置 (%): "))
                    dev = float(input("允许偏离 (%): "))
                    limit = float(input("单日限额 (0为无): ") or 0)
                    inv_type = input("投资类型 (manual/dca): ")
                    dca = None
                    if inv_type == 'dca':
                        dca = {
                            'base_amount': float(input("定投金额: ")),
                            'frequency': 'weekly',
                            'execution_day': int(input("周几扣款 (1-7): "))
                        }
                    self.add_new_position_config(symbol, target, dev, inv_type, dca, max_invest_limit=limit)
                except ValueError: print("❌ 无效输入")
            
            elif choice == "4":
                print(json.dumps(self.portfolio, ensure_ascii=False, indent=2))
            
            elif choice == "0":
                break