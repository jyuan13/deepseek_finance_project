# deepseek_finance_project_V3/data_manager.py

import sqlite3
import pandas as pd
import json
import os
from datetime import datetime
from contextlib import closing

class DataManager:
    """
    [V3.36] 数据库管理 - 资源安全版
    修复: 增加 contextlib.closing 确保连接及时关闭，消除 ResourceWarning
    """
    def __init__(self, db_path='financial_data_v3.db'):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._get_conn()
        try:
            with closing(conn.cursor()) as cursor:
                # 基金净值表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS fund_nav (
                        fund_code TEXT,
                        date TEXT,
                        nav REAL,
                        daily_change REAL,
                        UNIQUE(fund_code, date)
                    )
                ''')
                # 基金持仓表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS fund_holdings (
                        fund_code TEXT,
                        stock_code TEXT,
                        stock_name TEXT,
                        weight REAL,
                        quarter TEXT,
                        UNIQUE(fund_code, stock_code, quarter)
                    )
                ''')
                # 元数据缓存表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS meta_cache (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        update_time TEXT
                    )
                ''')
                # 市场行情表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS market_quotes (
                        symbol TEXT,
                        date TEXT,
                        open REAL,
                        high REAL,
                        low REAL,
                        close REAL,
                        volume REAL,
                        UNIQUE(symbol, date)
                    )
                ''')
            conn.commit()
        finally:
            conn.close()

    def save_fund_nav(self, df):
        if df.empty: return
        conn = self._get_conn()
        try:
            # 确保日期格式统一
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            data_to_insert = df[['fund_code', 'date', 'nav', 'daily_change']].values.tolist()
            with closing(conn.cursor()) as cursor:
                cursor.executemany('''
                    INSERT OR IGNORE INTO fund_nav (fund_code, date, nav, daily_change)
                    VALUES (?, ?, ?, ?)
                ''', data_to_insert)
            conn.commit()
        except Exception as e:
            print(f"Save NAV Error: {e}")
        finally:
            conn.close()

    def get_fund_nav(self, fund_code, limit=30):
        conn = self._get_conn()
        try:
            query = f'''
                SELECT date, nav, daily_change FROM fund_nav 
                WHERE fund_code='{fund_code}' 
                ORDER BY date ASC 
            '''
            df = pd.read_sql_query(query, conn)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                return df.tail(limit)
            return pd.DataFrame()
        finally:
            conn.close()

    def save_fund_holdings(self, df):
        if df.empty: return
        conn = self._get_conn()
        try:
            data_to_insert = df[['fund_code', 'stock_code', 'stock_name', 'weight', 'quarter']].values.tolist()
            with closing(conn.cursor()) as cursor:
                # 先清空旧持仓，避免重复堆积
                cursor.execute("DELETE FROM fund_holdings WHERE fund_code=?", (str(df.iloc[0]['fund_code']),))
                cursor.executemany('''
                    INSERT OR REPLACE INTO fund_holdings (fund_code, stock_code, stock_name, weight, quarter)
                    VALUES (?, ?, ?, ?, ?)
                ''', data_to_insert)
            conn.commit()
        finally:
            conn.close()

    def get_latest_holdings(self, fund_code):
        conn = self._get_conn()
        try:
            query = f'''
                SELECT stock_code, stock_name, weight, quarter 
                FROM fund_holdings 
                WHERE fund_code='{fund_code}'
                ORDER BY weight DESC
            '''
            return pd.read_sql_query(query, conn)
        finally:
            conn.close()

    def save_market_data(self, df, symbol):
        if df.empty: return
        conn = self._get_conn()
        try:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            df['symbol'] = symbol
            data = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
            with closing(conn.cursor()) as cursor:
                cursor.executemany('''
                    INSERT OR IGNORE INTO market_quotes (symbol, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', data)
            conn.commit()
        finally:
            conn.close()

    def get_market_data(self, symbol, limit=365):
        conn = self._get_conn()
        try:
            query = f'''
                SELECT date, open, high, low, close, volume 
                FROM market_quotes 
                WHERE symbol='{symbol}' 
                ORDER BY date ASC
            '''
            df = pd.read_sql_query(query, conn)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                return df.tail(limit)
            return pd.DataFrame()
        finally:
            conn.close()

    def clear_all_data(self):
        conn = self._get_conn()
        try:
            with closing(conn.cursor()) as cursor:
                cursor.execute("DELETE FROM fund_nav")
                cursor.execute("DELETE FROM fund_holdings")
                cursor.execute("DELETE FROM meta_cache")
                cursor.execute("DELETE FROM market_quotes")
            conn.commit()
            print("🧹 数据库已清空")
        finally:
            conn.close()