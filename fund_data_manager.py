# deepseek_finance_project_V3/fund_data_manager.py

import pandas as pd
import akshare as ak
import contextlib
from datetime import datetime
from data_provider import DataProvider
from data_manager import DataManager

class FundDataManager:
    """
    基金数据管家
    协调 DataProvider (API层) 和 DataManager (持久层)，
    负责数据的获取、缓存策略和业务对象封装。
    """
    def __init__(self):
        self.provider = DataProvider()
        self.db = DataManager()
        
        # 特殊资产映射表 (指数/商品等非标准基金)
        # 如果代码匹配这里的 key，则走特殊获取逻辑
        self.special_assets = {
            '000300': {'symbol': '000300.SS', 'type': 'index', 'name': '沪深300'},
            '000001': {'symbol': '000001.SS', 'type': 'index', 'name': '上证指数'},
            '399001': {'symbol': '399001.SZ', 'type': 'index', 'name': '深证成指'},
            'NASDAQ': {'symbol': '^IXIC', 'type': 'index', 'name': '纳斯达克'},
            'SP500': {'symbol': '^GSPC', 'type': 'index', 'name': '标普500'},
            'GOLD': {'symbol': 'GC=F', 'type': 'commodity', 'name': '黄金'},
        }

    def update_fund_nav(self, fund_code):
        """
        [Active Update] 强制联网更新基金净值并保存到数据库
        """
        # 1. 检查是否是特殊资产 (指数)
        if fund_code in self.special_assets:
            # 指数通常实时获取或走K线逻辑，不需要存历史NAV表
            return False
            
        # 2. 普通基金逻辑
        df = self.provider.fetch_fund_nav_history(fund_code)
        if not df.empty:
            self.db.save_fund_nav(df)
            return True
        return False

    def get_fund_nav_history(self, fund_code, lookback_days=90):
        """
        获取基金净值历史 (优先读库，过期或无数据则联网)
        """
        # A. 特殊资产 (直接走 K 线获取)
        if fund_code in self.special_assets:
            asset = self.special_assets[fund_code]
            symbol = asset['symbol']
            market = "US" if symbol.startswith("^") or symbol == "GC=F" else "A"
            df = self.provider.fetch_history_kline(symbol, market=market, days=lookback_days)
            if not df.empty:
                # 统一格式化为 nav 表结构
                df = df.rename(columns={'close': 'nav'})
                df['daily_change'] = df['nav'].pct_change() * 100
                return df[['date', 'nav', 'daily_change']]
            return pd.DataFrame()

        # B. 普通基金 (查库)
        df = self.db.get_fund_nav(fund_code)
        
        # 缓存策略：如果库里没数据，或者数据太旧(超过3天)，尝试更新
        need_update = False
        if df.empty:
            need_update = True
        else:
            try:
                last_date = pd.to_datetime(df['date'].iloc[-1])
                if (datetime.now() - last_date).days > 3: 
                    need_update = True
            except:
                need_update = True
        
        if need_update:
            success = self.update_fund_nav(fund_code)
            if success:
                df = self.db.get_fund_nav(fund_code) # 更新后再次读取
            
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            # 截取最近 N 天的数据返回
            df = df[df['date'] >= (datetime.now() - pd.Timedelta(days=lookback_days))]
            
        return df

    def update_fund_holdings(self, fund_code, force_update=False):
        """
        更新基金持仓 (通常每季度更新一次)
        :param force_update: 是否强制联网下载
        """
        # 1. 检查本地是否有近期持仓 (除非强制更新)
        if not force_update:
            df_local = self.db.get_fund_holdings(fund_code)
            if not df_local.empty:
                return df_local

        # 2. 联网获取
        df = self.provider.fetch_fund_portfolio(fund_code, force_update=force_update)
        if not df.empty:
            self.db.save_fund_holdings(df)
            
        return df

    def get_top_holdings(self, fund_code):
        """
        获取前十大持仓列表 (List of Dict)
        """
        # 优先读库
        df = self.db.get_fund_holdings(fund_code)
        
        # 如果库为空，尝试联网更新
        if df.empty:
            df = self.update_fund_holdings(fund_code)
            
        if df.empty: return []
        
        # 转换为业务层使用的 list 格式
        holdings = []
        for _, row in df.iterrows():
            holdings.append({
                "stock_code": row['stock_code'],
                "stock_name": row['stock_name'],
                "weight": row['weight']
            })
        return holdings

    def get_aggregated_news(self, fund_code):
        """
        获取聚合舆情 (基金本身 + 重仓股)
        """
        # 1. 获取基金本身新闻
        news = self.provider.news.fetch_sentiment_news(fund_code)
        
        # 2. 获取前3大重仓股新闻 (增加上下文)
        holdings = self.get_top_holdings(fund_code)
        for h in holdings[:3]:
            stock_code = h['stock_code']
            stock_news = self.provider.news.fetch_sentiment_news(stock_code)
            news.extend(stock_news)
            
        return list(set(news)) # 去重

    def get_fund_basic_info(self, fund_code):
        """
        获取基金基础信息 (代码, 类型, 名称)
        """
        # 1. 特殊资产直接返回
        if fund_code in self.special_assets:
            return self.special_assets[fund_code]
            
        # 2. 默认信息
        info = {'code': fund_code, 'type': 'stock', 'name': fund_code}
        
        # 3. 尝试从数据库持仓表中反推名称 (减少API调用)
        # [Fix V3.6] 使用 get_connection 获取连接并正确关闭
        try:
            with contextlib.closing(self.db.get_connection()) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT stock_name FROM fund_holdings WHERE fund_code=? LIMIT 1", (fund_code,))
                row = cursor.fetchone()
                # 这里逻辑是：目前我们没有专门的 fund_info 表，
                # 但如果以后有，可以在这里查。
                # 暂时我们主要依赖用户配置的别名，或者前端显示代码。
                pass
        except Exception: 
            pass
        
        # 4. (可选) 尝试调用 AkShare 接口获取详情
        # 考虑到速度，这里通常不实时调用 ak.fund_em_open_fund_info
        # 除非确实需要精确的官方名称
        
        return info

    def get_realtime_snapshot(self, symbol):
        """
        获取实时行情快照 (透传给 DataProvider)
        自动判断市场类型 (A股/港股/美股)
        """
        market = "A"
        
        # 简单的市场判断逻辑
        if symbol.startswith("^") or symbol == "GC=F" or symbol == "CL=F" or "USD" in symbol:
            market = "US"
        elif symbol.endswith(".HK") or (symbol.isdigit() and len(symbol) == 5):
            market = "HK"
        elif symbol.endswith(".SS") or symbol.endswith(".SZ"):
            market = "A"
            
        return self.provider.market.get_quote_snapshot(symbol, market=market)