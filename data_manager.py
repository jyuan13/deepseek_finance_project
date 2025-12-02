# deepseek_finance_project_V3/data_manager.py

import sqlite3
import pandas as pd
import os
import json
from datetime import datetime

class DataManager:
    """
    [V3.9 数据仓库]
    修复: 增加 meta_cache 表定义，防止 no such table 报错。
    """
    
    def __init__(self, db_path="financial_data_v3.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """初始化数据库表结构 (自动修复缺失表)"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 1. 基金净值表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fund_nav (
                fund_code TEXT,
                date TEXT,
                nav REAL,
                daily_change REAL,
                source TEXT DEFAULT 'akshare',
                PRIMARY KEY (fund_code, date)
            )
        ''')
        
        # 2. 基金持仓表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fund_holdings (
                fund_code TEXT,
                report_date TEXT,
                stock_code TEXT,
                stock_name TEXT,
                weight REAL,
                source TEXT DEFAULT 'akshare',
                PRIMARY KEY (fund_code, report_date, stock_code)
            )
        ''')
        
        # 3. 市场行情表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_quotes (
                symbol TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                source TEXT,
                PRIMARY KEY (symbol, date, source)
            )
        ''')
        
        # 4. [关键修复] 基础信息缓存表 (用于存储基金类型等元数据)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meta_cache (
                key TEXT PRIMARY KEY,
                value TEXT,
                update_time TEXT
            )
        ''')
        
        # 5. 舆情缓存表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sentiment_cache (
                symbol TEXT,
                date TEXT,
                news_summary TEXT,
                sentiment_score REAL,
                source TEXT,
                created_at TEXT,
                PRIMARY KEY (symbol, date, source)
            )
        ''')
        
        conn.commit()
        conn.close()

    def save_market_data(self, df: pd.DataFrame, source="unknown"):
        if df.empty: return
        df = df.copy()
        df['source'] = source
        if 'date' in df.columns: df['date'] = df['date'].astype(str)
        conn = self._get_conn()
        try:
            data = df.to_dict(orient='records')
            sql = "INSERT OR REPLACE INTO market_quotes (symbol, date, open, high, low, close, volume, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            params = [(d['symbol'], d['date'], d.get('open',0), d.get('high',0), d.get('low',0), d.get('close',0), d.get('volume',0), d['source']) for d in data]
            conn.cursor().executemany(sql, params)
            conn.commit()
        finally: conn.close()

    def get_market_data(self, symbol, preferred_source="history_sync"):
        conn = self._get_conn()
        # 简单的查询逻辑，不强制 source，优先返回有数据的
        query = f"SELECT * FROM market_quotes WHERE symbol='{symbol}' ORDER BY date ASC"
        df = pd.read_sql(query, conn)
        conn.close()
        if not df.empty: 
            df['date'] = pd.to_datetime(df['date'])
        return df

    def save_fund_nav(self, df):
        if df.empty: return
        df = df.copy()
        df['date'] = df['date'].astype(str)
        conn = self._get_conn()
        try:
            data = df.to_dict(orient='records')
            sql = "INSERT OR REPLACE INTO fund_nav (fund_code, date, nav, daily_change, source) VALUES (?, ?, ?, ?, 'akshare')"
            params = [(d['fund_code'], d['date'], d['nav'], d['daily_change']) for d in data]
            conn.cursor().executemany(sql, params)
            conn.commit()
        finally: conn.close()

    def get_fund_nav(self, fund_code, limit=30):
        conn = self._get_conn()
        df = pd.read_sql(f"SELECT * FROM fund_nav WHERE fund_code='{fund_code}' ORDER BY date DESC LIMIT {limit}", conn)
        conn.close()
        if not df.empty: 
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
        return df

    def save_fund_holdings(self, df):
        if df.empty: return
        conn = self._get_conn()
        try:
            data = df.to_dict(orient='records')
            sql = "INSERT OR REPLACE INTO fund_holdings (fund_code, report_date, stock_code, stock_name, weight, source) VALUES (?, ?, ?, ?, ?, 'akshare')"
            params = [(d['fund_code'], d.get('report_date',''), d['stock_code'], d['stock_name'], d['weight']) for d in data]
            conn.cursor().executemany(sql, params)
            conn.commit()
        finally: conn.close()

    def get_latest_holdings(self, fund_code):
        conn = self._get_conn()
        res = conn.execute(f"SELECT MAX(report_date) FROM fund_holdings WHERE fund_code='{fund_code}'").fetchone()
        if not res or not res[0]: 
            conn.close()
            return pd.DataFrame()
        df = pd.read_sql(f"SELECT * FROM fund_holdings WHERE fund_code='{fund_code}' AND report_date='{res[0]}'", conn)
        conn.close()
        return df
        
    def clear_all_data(self):
        """清空数据库 (危险操作)"""
        conn = self._get_conn()
        cursor = conn.cursor()
        for table in ['fund_nav', 'fund_holdings', 'market_quotes', 'meta_cache', 'sentiment_cache']:
            try:
                cursor.execute(f"DELETE FROM {table}")
            except:
                pass
        conn.commit()
        conn.close()
        print("⚠ 数据库已清空")