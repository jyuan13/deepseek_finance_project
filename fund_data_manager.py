# deepseek_finance_project_V3/fund_data_manager.py

import pandas as pd
import akshare as ak
import json
from datetime import datetime, timedelta
from data_provider import DataProvider
from data_manager import DataManager

class FundDataManager:
    """
    [V3.5 基金数据管家 - 混合资产版]
    升级: 支持 NASDAQ, SP500, GOLD 等指数/商品的"伪基金"模式
    """
    
    def __init__(self):
        self.provider = DataProvider()
        self.db = DataManager()
        
        # [V3.5 新增] 特殊资产注册表
        self.special_assets = {
            "NASDAQ": {
                "symbol": "^IXIC",      # 实际行情代码
                "name": "纳斯达克100指数",
                "type": "index_us",     # 资产类型
                "currency": "USD"
            },
            "SP500": {
                "symbol": "^GSPC",
                "name": "标普500指数",
                "type": "index_us",
                "currency": "USD"
            },
            "GOLD": {
                "symbol": "GC=F",
                "name": "COMEX黄金期货",
                "type": "commodity",
                "currency": "USD"
            }
        }

    def update_fund_holdings(self, fund_code, force_update=True):
        """
        [维护模式专用] 强制联网下载并更新本地持仓文件
        """
        if fund_code in self.special_assets:
            print(f"   ⏩ [跳过] {fund_code} 是特殊指数/商品，无需下载持仓。")
            return

        print(f"   📥 [联网] 正在下载最新持仓: {fund_code} ...")
        df = self.provider.fetch_fund_portfolio(fund_code, years_to_try=2, force_update=force_update)
        
        if not df.empty:
            self.db.save_fund_holdings(df)
            print(f"     ✅ 更新成功: {len(df)} 条持仓记录")
        else:
            print(f"     ⚠️ 更新失败: 未获取到数据")

    def get_fund_nav_history(self, fund_code, lookback_days=90):
        if fund_code in self.special_assets:
            asset = self.special_assets[fund_code]
            symbol = asset['symbol']
            
            market = "US" 
            df = self.provider.fetch_history_kline(symbol, market=market, days=lookback_days)
            
            if not df.empty:
                df = df.rename(columns={'close': 'nav'})
                df['daily_change'] = df['nav'].pct_change() * 100
                df = df[['date', 'nav', 'daily_change']].dropna()
                return df.sort_values('date')
            return pd.DataFrame()

        df = self.db.get_fund_nav(fund_code, limit=lookback_days)
        is_stale = True
        if not df.empty:
            last_date = pd.to_datetime(df.iloc[-1]['date'])
            if (datetime.now() - last_date).days < 5: 
                is_stale = False
        
        if df.empty or is_stale:
            new_df = self.provider.fetch_fund_nav_history(fund_code)
            if not new_df.empty:
                self.db.save_fund_nav(new_df)
                df = self.db.get_fund_nav(fund_code, limit=lookback_days)
        
        return df

    def get_top_holdings(self, fund_code):
        if fund_code in self.special_assets:
            asset = self.special_assets[fund_code]
            return [{
                "stock_code": asset['symbol'],
                "stock_name": asset['name'],
                "weight": 100.00
            }]

        df = self.provider.fetch_fund_portfolio(fund_code, force_update=False)
        
        if df.empty:
            df = self.db.get_latest_holdings(fund_code)
            
        if df.empty:
            print(f"   ⚠️ [本地缺失] 未找到 {fund_code} 的持仓文件。")
            print(f"      请在主菜单选择 '7. 更新持仓数据' 来下载数据。")
            return []
            
        return df.to_dict(orient='records')

    def update_market_quotes(self, symbol_list):
        print(f"⚡ 检查行情缓存 ({len(symbol_list)}只)...")
        for symbol in symbol_list:
            market = "US" if symbol.isalpha() or symbol.startswith('^') or "=" in symbol else "A"
            self.provider.fetch_history_kline(symbol, market=market)

    def get_realtime_price(self, symbol):
        snapshot, valid = self.get_realtime_snapshot(symbol)
        if valid:
            return snapshot['price']
        return None

    def get_realtime_snapshot(self, symbol):
        market = "A"
        if symbol.isalpha() or symbol.startswith('^') or "=" in symbol:
            market = "US"
        elif len(symbol) == 5 and symbol.isdigit():
            market = "HK" 
            
        return self.provider.market.get_quote_snapshot(symbol, market)

    def get_aggregated_news(self, symbol):
        if symbol in self.special_assets:
            search_term = self.special_assets[symbol]['name']
            return self.provider.news.fetch_sentiment_news(search_term)
            
        return self.provider.news.fetch_sentiment_news(symbol)

    def get_fund_basic_info(self, fund_code):
        if fund_code in self.special_assets:
            return {
                "code": fund_code,
                "name": self.special_assets[fund_code]['name'],
                "type": self.special_assets[fund_code]['type']
            }

        cache_key = f"fund_meta_{fund_code}"
        conn = self.db._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT value FROM meta_cache WHERE key=?", (cache_key,))
            row = cursor.fetchone()
            if row: return json.loads(row[0])
        except Exception: pass 
        finally: conn.close()
        
        return self._fetch_and_cache_info(fund_code)

    def _fetch_and_cache_info(self, fund_code):
        name = f"基金_{fund_code}"
        ctype = "stock"
        
        try:
            df = ak.fund_individual_basic_info_em(symbol=fund_code)
            if not df.empty and 'value' in df.columns:
                info = df.set_index('item')['value'].to_dict()
                name = info.get('基金简称', name)
                if "债" in info.get('基金类型', ''): ctype = "bond"
        except: pass
        
        res = {"code": fund_code, "type": ctype, "name": name}
        
        try:
            conn = self.db._get_conn()
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO meta_cache (key, value, update_time) VALUES (?, ?, ?)",
                          (f"fund_meta_{fund_code}", json.dumps(res, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            conn.close()
        except: pass
            
        return res

if __name__ == "__main__":
    mgr = FundDataManager()
    print("Testing Fund Type Logic...")
    print(f"000001: {mgr.get_fund_basic_info('000001')}")
    print(f"NASDAQ: {mgr.get_fund_basic_info('NASDAQ')}")