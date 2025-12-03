# deepseek_finance_project_V3/fund_data_manager.py

import pandas as pd
import akshare as ak
import json
from datetime import datetime, timedelta
from data_provider import DataProvider
from data_manager import DataManager

class FundDataManager:
    """
    [V3.3 基金数据管家]
    修复: KeyError crash, 增加港股识别
    """
    
    def __init__(self):
        self.provider = DataProvider()
        self.db = DataManager() 

    def get_fund_nav_history(self, fund_code, lookback_days=90):
        df = self.db.get_fund_nav(fund_code, limit=lookback_days)
        is_stale = True
        if not df.empty:
            last_date = pd.to_datetime(df.iloc[-1]['date'])
            if (datetime.now() - last_date).days < 3:
                is_stale = False
        
        if df.empty or is_stale:
            print(f"🔄 [更新] 同步基金 {fund_code} 净值...")
            new_df = self.provider.fetch_fund_nav_history(fund_code)
            if not new_df.empty:
                self.db.save_fund_nav(new_df)
                # 重新读取以确保排序和限制正确
                df = self.db.get_fund_nav(fund_code, limit=lookback_days)
            else:
                print(f"⚠️ 警告: 无法获取 {fund_code} 的最新净值 (尝试了所有接口)，将使用历史缓存(如有)。")
        
        return df

    def get_top_holdings(self, fund_code):
        df = self.db.get_latest_holdings(fund_code)
        
        if df.empty:
            print(f"🔄 [更新] 同步基金 {fund_code} 持仓...")
            new_df = self.provider.fetch_fund_portfolio(fund_code)
            if not new_df.empty:
                self.db.save_fund_holdings(new_df)
                df = new_df
            else:
                print(f"⚠️ 警告: 无法获取 {fund_code} 的持仓明细 (可能是QDII/ETF联接基金且未配置穿透映射，或数据未更新)。")
        
        return df.to_dict(orient='records') if not df.empty else []

    def update_market_quotes(self, symbol_list):
        print(f"⚡ 正在检查 {len(symbol_list)} 只标的行情缓存...")
        for symbol in symbol_list:
            market = "US" if symbol.isalpha() or symbol.startswith('^') else "A"
            df = self.db.get_market_data(symbol)
            is_stale = True
            if not df.empty:
                last_date = pd.to_datetime(df.iloc[-1]['date'])
                if (datetime.now() - last_date).days < 1:
                    is_stale = False
            
            if df.empty or is_stale:
                new_data = self.provider.market.fetch_history_kline(symbol, market=market)
                if not new_data.empty:
                    # [V3.3 修复] 补充缺失的 symbol 和 source 列，防止 KeyError
                    new_data['symbol'] = symbol
                    new_data['source'] = 'history_sync'
                    self.db.save_market_data(new_data, source="history_sync")

    def get_realtime_price(self, symbol):
        snapshot, valid = self.get_realtime_snapshot(symbol)
        if valid:
            return snapshot['price']
        return None

    def get_realtime_snapshot(self, symbol):
        # [V3.3 优化] 智能识别市场类型
        market = "A"
        if symbol.isalpha() or symbol.startswith('^'):
            market = "US"
        elif len(symbol) == 5 and symbol.isdigit():
            market = "HK"  # 识别 5 位数字代码为港股
            
        return self.provider.market.get_quote_snapshot(symbol, market)

    def get_aggregated_news(self, symbol):
        return self.provider.news.fetch_sentiment_news(symbol)

    def _map_fund_type(self, raw_type):
        if not raw_type: return "stock"
        raw_type = str(raw_type)
        if "债" in raw_type or "固定收益" in raw_type: return "bond"
        elif "混合" in raw_type or "配置" in raw_type: return "mix"
        elif "货币" in raw_type or "理财" in raw_type: return "bond"
        elif "指数" in raw_type or "股票" in raw_type or "ETF" in raw_type:
            return "stock"
        return "stock"

    def _fetch_fund_type_from_akshare(self, fund_code):
        name = f"基金_{fund_code}"
        ctype = "stock"
        try:
            if hasattr(ak, 'fund_individual_basic_info_em'):
                df = ak.fund_individual_basic_info_em(symbol=fund_code)
                if not df.empty:
                    if 'item' in df.columns and 'value' in df.columns:
                        info_dict = df.set_index('item')['value'].to_dict()
                        raw_type = info_dict.get('基金类型', '股票型')
                        name = info_dict.get('基金简称', name)
                        return self._map_fund_type(raw_type), name
        except Exception:
            pass 

        try:
            df_all = ak.fund_name_em()
            row = df_all[df_all['基金代码'] == fund_code]
            if not row.empty:
                name = row.iloc[0]['基金简称']
                raw_type = row.iloc[0]['基金类型']
                return self._map_fund_type(raw_type), name
        except Exception:
            pass
            
        return ctype, name

    def get_fund_basic_info(self, fund_code):
        cache_key = f"fund_meta_{fund_code}"
        conn = self.db._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT value FROM meta_cache WHERE key=?", (cache_key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
        except Exception:
            pass 
        finally:
            conn.close()
        
        ctype, name = self._fetch_fund_type_from_akshare(fund_code)
        res = {"code": fund_code, "type": ctype, "name": name}
        
        try:
            conn = self.db._get_conn()
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO meta_cache (key, value, update_time) VALUES (?, ?, ?)",
                          (cache_key, json.dumps(res, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            conn.close()
        except Exception:
            pass
            
        return res

if __name__ == "__main__":
    mgr = FundDataManager()
    print("Testing Fund Type Logic...")
    print(f"000001: {mgr.get_fund_basic_info('000001')}")