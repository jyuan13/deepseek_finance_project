# deepseek_finance_project_V3/risk_guard.py

class RiskGuard:
    """
    [V3.9 风控卫士]
    升级: 支持多资产类型动态阈值 (Equity/Bond/Crypto/Mix)
    """
    
    def __init__(self):
        # 默认规则 (股票型)
        self.default_rules = {
            "max_drawdown_limit": -15.0,
            "single_day_drop_limit": -4.0,
            "stop_loss_threshold": -2.5
        }
        
        # 债券型规则 (严格)
        self.bond_rules = {
            "max_drawdown_limit": -3.0,
            "single_day_drop_limit": -0.5,
            "stop_loss_threshold": -0.3
        }
        
        # 混合型规则 (中庸)
        self.mix_rules = {
            "max_drawdown_limit": -10.0,
            "single_day_drop_limit": -2.5,
            "stop_loss_threshold": -1.5
        }

    def _get_rules(self, asset_type):
        if asset_type == "bond": return self.bond_rules
        if asset_type == "mix": return self.mix_rules
        return self.default_rules

    def check_risk(self, signal, context):
        """
        审核交易信号 & 持仓风险
        :param context: { ..., 'asset_type': 'stock' }
        """
        asset_type = context.get('asset_type', 'stock')
        rules = self._get_rules(asset_type)
        
        shadow_chg = context.get('shadow_change', 0)
        holding_pnl = context.get('holding_pnl', 0)
        has_holding = context.get('has_holding', False)
        
        # 1. 买入熔断
        if signal == "BUY":
            if shadow_chg < rules['stop_loss_threshold']:
                return False, f"⛔ [熔断] 今日跌幅 {shadow_chg}% 超过 {asset_type} 类阈值 {rules['stop_loss_threshold']}%，禁止接飞刀。"
            
            if has_holding and holding_pnl < rules['max_drawdown_limit']:
                return False, f"⛔ [止损] 累计亏损 {holding_pnl}% 超过 {asset_type} 类阈值，禁止补仓。"

        # 2. 持仓风险检查
        if has_holding:
            if holding_pnl < rules['max_drawdown_limit']:
                return False, f"⚠️ [严重警告] 累计亏损触及 {asset_type} 类止损线，建议清仓。"
            
            if shadow_chg < rules['single_day_drop_limit']:
                return False, f"⚠️ [预警] 今日跌幅 {shadow_chg}% 异常，建议关注。"

        return True, "✅ 风控通过"