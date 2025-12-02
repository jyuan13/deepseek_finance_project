# deepseek_finance_project_V3/fund_data_manager.py

import pandas as pd
import akshare as ak
import json
from datetime import datetime, timedelta
from data_provider import DataProvider
from data_manager import DataManager

class FundDataManager:
    """
    [V3.1 基金数据管家]
    升级: 智能识别基金类型 (Equity/Bond/Mix)，支持缓存
    修复: AkShare 接口兼容性问题
    """
    
    def __init__(self):
        self.provider = DataProvider()
        self.db = DataManager() 

    def get_fund_nav_history(self, fund_code, lookback_days=90):
        df = self.db.get_fund_nav(fund_code, limit=lookback_days)
        is_stale = True
        if not df.empty:
            last_date = df.iloc[-1]['date']
            if (datetime.now() - last_date).days < 3:
                is_stale = False
        
        if df.empty or is_stale:
            print(f"🔄 [更新] 同步基金 {fund_code} 净值...")
            new_df = self.provider.fetch_fund_nav_history(fund_code)
            if not new_df.empty:
                self.db.save_fund_nav(new_df)
                df = self.db.get_fund_nav(fund_code, limit=lookback_days)
        return df

    def get_top_holdings(self, fund_code):
        df = self.db.get_latest_holdings(fund_code)
        if df.empty:
            print(f"🔄 [更新] 同步基金 {fund_code} 持仓...")
            new_df = self.provider.fetch_fund_portfolio(fund_code)
            if not new_df.empty:
                self.db.save_fund_holdings(new_df)
                df = new_df
        return df.to_dict(orient='records') if not df.empty else []

    def update_market_quotes(self, symbol_list):
        print(f"⚡ 正在检查 {len(symbol_list)} 只标的行情缓存...")
        for symbol in symbol_list:
            market = "US" if symbol.isalpha() or symbol.startswith('^') else "A"
            df = self.db.get_market_data(symbol)
            is_stale = True
            if not df.empty:
                last_date = df.iloc[-1]['date']
                if (datetime.now() - last_date).days < 1:
                    is_stale = False
            
            if df.empty or is_stale:
                new_data = self.provider.market.fetch_history_kline(symbol, market=market)
                if not new_data.empty:
                    self.db.save_market_data(new_data, source="history_sync")

    def get_realtime_price(self, symbol):
        snapshot, valid = self.get_realtime_snapshot(symbol)
        if valid:
            return snapshot['price']
        return None

    def get_realtime_snapshot(self, symbol):
        market = "US" if symbol.isalpha() or symbol.startswith('^') else "A"
        return self.provider.market.get_quote_snapshot(symbol, market)

    def get_aggregated_news(self, symbol):
        return self.provider.news.fetch_sentiment_news(symbol)

    def _map_fund_type(self, raw_type):
        """辅助方法：将中文类型映射为系统类型"""
        if "债" in raw_type or "固定收益" in raw_type:
            return "bond"
        elif "混合" in raw_type or "配置" in raw_type:
            return "mix"
        elif "货币" in raw_type:
            return "bond"
        return "stock"

    def _fetch_fund_type_from_akshare(self, fund_code):
        """[V3.2 修复版] 兼容性更强的类型获取"""
        name = f"基金_{fund_code}"
        ctype = "stock"
        
        # 方案 A: 尝试新接口 (fund_individual_basic_info_em)
        # 这个接口信息最全，但旧版 akshare 没有
        try:
            if hasattr(ak, 'fund_individual_basic_info_em'):
                df = ak.fund_individual_basic_info_em(symbol=fund_code)
                if not df.empty:
                    info_dict = df.set_index('item')['value'].to_dict()
                    raw_type = info_dict.get('基金类型', '股票型')
                    name = info_dict.get('基金简称', name)
                    return self._map_fund_type(raw_type), name
        except Exception:
            pass # 失败则静默进入方案 B

        # 方案 B: 尝试老接口 (fund_name_em)
        # 这个接口极其稳定，但返回的是全量列表，速度稍慢
        try:
            # print(f"   ⚠️ 正在降级查找基金 {fund_code} 信息...") 
            df_all = ak.fund_name_em()
            # 筛选代码
            row = df_all[df_all['基金代码'] == fund_code]
            if not row.empty:
                name = row.iloc[0]['基金简称']
                raw_type = row.iloc[0]['基金类型']
                return self._map_fund_type(raw_type), name
        except Exception:
            pass
            
        return ctype, name

    def get_fund_basic_info(self, fund_code):
        """
        智能类型推断 + 缓存
        """
        cache_key = f"fund_meta_{fund_code}"
        
        # 1. 查缓存
        conn = self.db._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT value FROM meta_cache WHERE key=?", (cache_key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
        except Exception:
            pass # 表可能还没建好或者查询错误，直接跳过
        finally:
            conn.close()
        
        # 2. 联网获取 (使用兼容版方法)
        ctype, name = self._fetch_fund_type_from_akshare(fund_code)
        res = {"code": fund_code, "type": ctype, "name": name}
        
        # 3. 写入缓存
        try:
            conn = self.db._get_conn()
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO meta_cache (key, value, update_time) VALUES (?, ?, ?)",
                          (cache_key, json.dumps(res, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️ 写入缓存失败: {e}")
            
        return res

if __name__ == "__main__":
    mgr = FundDataManager()
    print("Testing Fund Type Logic...")
    # 测试一个股票型和一个债券型
    print(f"000001: {mgr.get_fund_basic_info('000001')}") 
    print(f"000217: {mgr.get_fund_basic_info('000217')}")