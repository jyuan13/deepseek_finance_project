# deepseek_finance_project_V3/portfolio_manager.py

# File: deepseek_finance_project_V3/portfolio_manager.py
# Class: PortfolioManager
# Function: __init__
# Logic: Initialize paths, load data, ensure structure.

# Function: _load_data
# Logic: Load JSON, auto-migrate List to Dict.

# Function: _save_data
# Logic: Recalculate assets, save to JSON.

# Function: _recalc_total_assets
# Logic: Sum cash + fund value (market_value or cost*shares).

# Function: get_cash_info / update_cash
# Logic: Manage cash field.

# Function: get_total_assets
# Logic: Sum everything.

# Function: get_investment_strategies / save_strategy_config
# Logic: Manage strategy dict.

# Function: get_fund_positions / save_fund_position / remove_fund_position
# Logic: Manage fund/stock entries with calculated fields.

# Function: get_index_positions / save_index_position / remove_index_position
# Logic: Manage index entries.

import json
import os
from datetime import datetime

class PortfolioManager:
    """
    持仓配置管理器 (JSON I/O)
    [V3.97 Stable] 
    1. 修复 indices_data 可能为 list 导致的 AttributeError
    2. 找回所有丢失的现金、策略管理、总资产计算功能
    3. 完整支持 V3.9 的自动份额反推逻辑
    """
    def __init__(self, funds_file='my_funds.json', indices_file='my_indices.json'):
        self.funds_file = funds_file
        self.indices_file = indices_file
        self.config_data = self._load_data(self.funds_file)
        self.indices_data = self._load_data(self.indices_file)
        
        if isinstance(self.config_data, dict):
            if "cash" not in self.config_data:
                self.config_data["cash"] = 0.0
            if "investment_strategies" not in self.config_data:
                self.config_data["investment_strategies"] = {
                    "dca_enabled": True,
                    "weekly_investment_day": "Thursday"
                }
            if "risk_profile" not in self.config_data:
                 self.config_data["risk_profile"] = "balanced"

    def _load_data(self, filepath):
        default_data = {
            "cash": 0.0, 
            "total_assets": 0.0,
            "risk_profile": "balanced",
            "investment_strategies": {},
            "positions_config": []
        }
        
        if not os.path.exists(filepath):
            return default_data
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if isinstance(data, list):
                print(f"🔧 检测到旧版列表格式 ({filepath})，正在自动迁移为字典结构...")
                return {"positions_config": data}
            
            if data is None:
                return default_data
                
            return data
        except Exception as e:
            print(f"⚠️ 读取 {filepath} 失败: {e}，使用默认空配置")
            return default_data

    def _save_data(self, filepath, data):
        if filepath == self.funds_file and isinstance(data, dict):
            self._recalc_total_assets(data)
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _recalc_total_assets(self, data):
        cash = data.get("cash", 0)
        fund_val = 0
        for p in data.get("positions_config", []):
            if "market_value" in p:
                fund_val += p["market_value"]
            else:
                fund_val += p.get("cost_price", 0) * p.get("current_shares", 0)
        
        data["total_assets"] = cash + fund_val

    def get_cash_info(self):
        if not isinstance(self.config_data, dict): return 0.0
        return self.config_data.get("cash", 0.0)

    def update_cash(self, amount):
        if not isinstance(self.config_data, dict): self.config_data = {}
        self.config_data["cash"] = float(amount)
        self._save_data(self.funds_file, self.config_data)

    def get_total_assets(self):
        cash = self.get_cash_info()
        fund_val = 0
        for p in self.get_fund_positions():
             val = p.get("market_value", p.get("cost_price", 0) * p.get("current_shares", 0))
             fund_val += val
        idx_val = 0
        for p in self.get_index_positions():
            idx_val += p.get("market_value_cny", 0)
        return cash + fund_val + idx_val

    def get_risk_profile(self):
        if not isinstance(self.config_data, dict): return "balanced"
        return self.config_data.get("risk_profile", "balanced")

    def get_investment_strategies(self):
        if not isinstance(self.config_data, dict): return {}
        return self.config_data.get("investment_strategies", {})

    def save_strategy_config(self, strategy_data):
        if not isinstance(self.config_data, dict): self.config_data = {}
        if "risk_profile" in strategy_data:
            self.config_data["risk_profile"] = strategy_data.pop("risk_profile")
        self.config_data["investment_strategies"] = strategy_data
        self._save_data(self.funds_file, self.config_data)

    def get_current_positions(self):
        return self.get_fund_positions()

    def get_fund_positions(self):
        if not isinstance(self.config_data, dict):
            if isinstance(self.config_data, list): return self.config_data
            return []
        return self.config_data.get("positions_config", [])

    def save_fund_position(self, symbol, market_value, pnl_rate, calculated_shares, calculated_cost, comment, limit_amount, dca_config, target_amount):
        positions = self.get_fund_positions()
        found = False
        new_entry = {
            "symbol": symbol,
            "market_value": float(market_value),
            "pnl_rate": float(pnl_rate),
            "current_shares": float(calculated_shares),
            "cost_price": float(calculated_cost),
            "comment": comment,
            "max_invest_limit": float(limit_amount),
            "dca_config": dca_config,
            "target_amount": float(target_amount),
            "last_update": datetime.now().strftime("%Y-%m-%d")
        }

        for i, pos in enumerate(positions):
            if pos['symbol'] == symbol:
                positions[i] = new_entry
                found = True
                break
        
        if not found:
            positions.append(new_entry)
            
        if not isinstance(self.config_data, dict):
            self.config_data = {"positions_config": positions}
        else:
            self.config_data["positions_config"] = positions
            
        self._save_data(self.funds_file, self.config_data)

    def remove_fund_position(self, symbol):
        positions = self.get_fund_positions()
        new_positions = [p for p in positions if p['symbol'] != symbol]
        if isinstance(self.config_data, dict):
            self.config_data["positions_config"] = new_positions
        else:
            self.config_data = {"positions_config": new_positions}
        self._save_data(self.funds_file, self.config_data)

    def get_index_positions(self):
        if not isinstance(self.indices_data, dict):
            if isinstance(self.indices_data, list): return self.indices_data
            return []
        return self.indices_data.get("positions_config", [])

    def save_index_position(self, symbol, market_value, pnl_rate, name, comment, target_amount):
        if not isinstance(self.indices_data, dict):
            if isinstance(self.indices_data, list):
                 self.indices_data = {"positions_config": self.indices_data}
            else:
                 self.indices_data = {"positions_config": []}
                 
        positions = self.indices_data.get("positions_config", [])
        found = False
        new_entry = {
            "symbol": symbol,
            "name": name,
            "market_value_cny": float(market_value),
            "pnl_rate": float(pnl_rate),
            "target_amount": float(target_amount),
            "comment": comment,
            "last_update": datetime.now().strftime("%Y-%m-%d")
        }

        for i, pos in enumerate(positions):
            if pos['symbol'] == symbol:
                positions[i] = new_entry
                found = True
                break
        
        if not found:
            positions.append(new_entry)
        
        self.indices_data["positions_config"] = positions
        self._save_data(self.indices_file, self.indices_data)
    def save_fund_simple(self, symbol, market_value, pnl_rate, limit, dca, target, comment):
        """[V4.0] 极简保存：只存市值和盈亏，不负责计算份额"""
        positions = self.get_fund_positions()
        new_entry = {
            "symbol": symbol,
            "market_value": float(market_value),
            "pnl_rate": float(pnl_rate),
            "max_invest_limit": float(limit),
            "dca_config": {"enabled": dca > 0, "base_amount": dca},
            "target_amount": float(target),
            "comment": comment,
            "current_shares": 0, # 占位，设为0，标志着需要在运行时反推
            "cost_price": 0,     # 占位，运行时计算
            "last_update": datetime.now().strftime("%Y-%m-%d")
        }
        
        found = False
        for i, pos in enumerate(positions):
            if pos['symbol'] == symbol:
                positions[i] = new_entry
                found = True
                break
        if not found: positions.append(new_entry)
        
        if not isinstance(self.config_data, dict): self.config_data = {"positions_config": positions}
        else: self.config_data["positions_config"] = positions
        self._save_data(self.funds_file, self.config_data)

    def remove_index_position(self, symbol):
        if not isinstance(self.indices_data, dict):
             if isinstance(self.indices_data, list):
                 self.indices_data = {"positions_config": self.indices_data}
             else:
                 return

        positions = self.indices_data.get("positions_config", [])
        self.indices_data["positions_config"] = [p for p in positions if p['symbol'] != symbol]
        self._save_data(self.indices_file, self.indices_data)