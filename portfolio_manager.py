# deepseek_finance_project_V3/portfolio_manager.py

import json
import os
import shutil
from datetime import datetime

class PortfolioManager:
    """
    持仓管理器 V3.6 (Full Featured)
    负责管理本地持仓文件，支持基金与指数的双轨制存储，以及现金余额管理。
    """
    def __init__(self):
        # 配置文件路径
        self.funds_file = "my_funds.json"
        self.indices_file = "my_indices.json"
        self.old_file = "my_portfolio.json"
        
        # [Migration] 启动时检查并迁移旧版数据
        self._check_and_migrate()
        
        # 初始化文件结构（如果不存在）
        self._init_files()

    def _check_and_migrate(self):
        """兼容性迁移：如果存在旧版文件且无新版文件，则重命名迁移"""
        if os.path.exists(self.old_file) and not os.path.exists(self.funds_file):
            print(f"🔄 检测到旧版持仓文件，正在迁移至 {self.funds_file}...")
            try:
                shutil.move(self.old_file, self.funds_file)
                print("✅ 迁移成功")
            except Exception as e:
                print(f"❌ 迁移失败: {e}")

    def _init_files(self):
        """初始化必要的数据文件"""
        # 1. 基金与现金文件
        if not os.path.exists(self.funds_file):
            default_funds = {
                "cash": 100000.0,  # 默认现金
                "positions_config": []
            }
            self._save_json(self.funds_file, default_funds)
            
        # 2. 指数文件
        if not os.path.exists(self.indices_file):
            self._save_json(self.indices_file, [])

    # ==================== 基金与现金 (Funds & Cash) ====================

    def get_fund_data(self):
        """读取完整的基金配置数据（包含现金）"""
        data = self._load_json(self.funds_file)
        if not isinstance(data, dict):
            # 数据损坏或格式错误时的兜底
            return {"cash": 0.0, "positions_config": []}
        return data

    def get_fund_positions(self):
        """仅获取基金持仓列表"""
        data = self.get_fund_data()
        return data.get("positions_config", [])

    def get_cash_balance(self):
        """获取当前现金余额"""
        data = self.get_fund_data()
        return data.get("cash", 0.0)

    def update_cash(self, new_balance):
        """更新现金余额"""
        data = self.get_fund_data()
        data["cash"] = float(new_balance)
        self._save_json(self.funds_file, data)
        print(f"✅ 现金余额已更新: {new_balance}")

    def save_fund_position(self, symbol, cost_price, shares, comment="", max_invest_limit=0, dca_config=None, target_amount=0):
        """
        保存或更新单个基金持仓
        :param symbol: 基金代码
        :param cost_price: 持仓成本
        :param shares: 持有份额
        :param comment: 备注
        :param max_invest_limit: 单日买入限额 (0为不限)
        :param dca_config: 定投配置 dict {"enabled": bool, "base_amount": float}
        :param target_amount: 计划投资总额 (子弹)
        """
        data = self.get_fund_data()
        positions = data.get("positions_config", [])
        
        # 构造新记录对象
        new_entry = {
            "symbol": symbol,
            "cost_price": float(cost_price) if cost_price else 0.0,
            "current_shares": float(shares) if shares else 0.0,
            "comment": comment,
            "max_invest_limit": float(max_invest_limit) if max_invest_limit else 0.0,
            "dca_config": dca_config or {"enabled": False, "base_amount": 0},
            "target_amount": float(target_amount) if target_amount else 0.0,
            "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 查找是否存在，存在则更新，不存在则追加
        found = False
        for i, p in enumerate(positions):
            if p['symbol'] == symbol:
                # 这是一个更新操作，保留原有的一些不需要覆盖的字段（如果有）
                # 这里我们选择全量覆盖以确保配置最新
                positions[i] = new_entry
                found = True
                break
        
        if not found:
            positions.append(new_entry)
            
        data["positions_config"] = positions
        self._save_json(self.funds_file, data)
        print(f"✅ 基金持仓已保存: {symbol}")

    def remove_fund_position(self, symbol):
        """删除指定的基金持仓"""
        data = self.get_fund_data()
        positions = data.get("positions_config", [])
        
        # 过滤掉要删除的 symbol
        new_positions = [p for p in positions if p['symbol'] != symbol]
        
        if len(new_positions) == len(positions):
            print(f"⚠️ 未找到基金: {symbol}")
            return

        data["positions_config"] = new_positions
        self._save_json(self.funds_file, data)
        print(f"🗑️ 基金持仓已删除: {symbol}")

    # 为了兼容旧代码的调用习惯
    def get_current_positions(self):
        return self.get_fund_positions()

    # ==================== 指数相关 (Indices) ====================

    def get_index_positions(self):
        """获取指数持仓列表"""
        data = self._load_json(self.indices_file)
        if isinstance(data, list):
            return data
        # 如果格式不对，返回空列表
        return []

    def save_index_position(self, symbol, market_value_cny, pnl_rate, name="", comment="", target_amount=0):
        """
        保存或更新指数持仓
        :param symbol: 指数代码 (如 ^IXIC)
        :param market_value_cny: 当前持仓市值 (人民币)
        :param pnl_rate: 当前总盈亏率 (%)
        :param name: 指数名称
        :param comment: 备注
        :param target_amount: 计划投资总额
        """
        positions = self.get_index_positions()
        
        new_entry = {
            "symbol": symbol,
            "name": name,
            "market_value_cny": float(market_value_cny) if market_value_cny else 0.0,
            "pnl_rate": float(pnl_rate) if pnl_rate else 0.0,
            "target_amount": float(target_amount) if target_amount else 0.0,
            "comment": comment,
            "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        found = False
        for i, p in enumerate(positions):
            if p['symbol'] == symbol:
                positions[i] = new_entry
                found = True
                break
        
        if not found:
            positions.append(new_entry)
            
        self._save_json(self.indices_file, positions)
        print(f"✅ 指数持仓已保存: {symbol}")

    def remove_index_position(self, symbol):
        """删除指定的指数持仓"""
        positions = self.get_index_positions()
        new_positions = [p for p in positions if p['symbol'] != symbol]
        
        if len(new_positions) == len(positions):
            print(f"⚠️ 未找到指数: {symbol}")
            return
            
        self._save_json(self.indices_file, new_positions)
        print(f"🗑️ 指数持仓已删除: {symbol}")

    # ==================== 通用工具方法 ====================

    def _load_json(self, filepath):
        """安全读取 JSON 文件"""
        if not os.path.exists(filepath):
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ 读取 {filepath} 失败: {e}")
            return {}

    def _save_json(self, filepath, data):
        """安全写入 JSON 文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存 {filepath} 失败: {e}")

    def manage_portfolio(self):
        """CLI 管理入口 (main.py 调用的菜单)"""
        while True:
            print("\n💼 投资组合管理 (双轨版)")
            print("-" * 30)
            print("1. 查看基金持仓 (Funds)")
            print("2. 查看指数持仓 (Indices)")
            print("3. 修改现金余额 (Cash)")
            print("0. 返回主菜单")
            print("-" * 30)
            
            choice = input("选择: ").strip()
            
            if choice == "1":
                funds = self.get_fund_positions()
                print(f"\n📊 当前基金持仓 ({len(funds)}):")
                if not funds:
                    print("   (暂无持仓)")
                for p in funds:
                    dca = p.get('dca_config', {}).get('base_amount', 0)
                    target = p.get('target_amount', 0)
                    print(f"   - {p['symbol']}: 成本 {p['cost_price']}, 份额 {p['current_shares']}, 定投 {dca}, 计划 {target}")
                    
            elif choice == "2":
                indices = self.get_index_positions()
                print(f"\n📈 当前指数持仓 ({len(indices)}):")
                if not indices:
                    print("   (暂无持仓)")
                for p in indices:
                    target = p.get('target_amount', 0)
                    print(f"   - {p['symbol']} ({p.get('name','')}): 市值 ¥{p['market_value_cny']}, 盈亏 {p['pnl_rate']}%, 计划 {target}")
            
            elif choice == "3":
                curr = self.get_cash_balance()
                print(f"\n💰 当前现金余额: {curr}")
                try:
                    new_val = input("请输入新余额: ").strip()
                    if new_val:
                        self.update_cash(new_val)
                except ValueError:
                    print("❌ 输入无效")
                    
            elif choice == "0":
                break
            else:
                print("❌ 无效输入")