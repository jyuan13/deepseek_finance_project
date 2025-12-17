# deepseek_finance_project_V3/data_manager.py

# File: deepseek_finance_project_V3/data_manager.py
# Class: DataManager
# Function: __init__
# Logic: 
#   Initialize db_path.
#   Call _init_db to create tables.
#   Call _migrate_db to update schema if needed.

# Function: _init_db
# Logic:
#   Connect to SQLite DB.
#   Create tables 'fund_nav' (fund_code, date, nav, daily_change).
#   Create tables 'fund_holdings' (fund_code, stock_code, stock_name, weight, quarter).
#   Create tables 'macro_cache' (key, value, update_time).
#   Commit and close.

# Function: _migrate_db
# Logic:
#   Check if 'quarter' column exists in 'fund_holdings'.
#   If not (OperationalError), execute ALTER TABLE to add it.
#   Handle exceptions.

# Function: get_connection_safe
# Logic:
#   [New] Return a context manager for safe connection handling.
#   Used for raw SQL execution where necessary.

# Function: save_fund_nav
# Logic:
#   Convert DataFrame to list of tuples.
#   Insert or replace into 'fund_nav'.
#   Commit.

# Function: get_fund_nav
# Logic:
#   Query 'fund_nav' by fund_code ordered by date.
#   Return DataFrame.

# Function: save_fund_holdings
# Logic:
#   Clean and validate DataFrame rows (ensure quarter exists).
#   Insert or replace into 'fund_holdings'.
#   Commit.

# Function: get_fund_holdings
# Logic:
#   Query 'fund_holdings' by fund_code.
#   Return DataFrame.

# Function: save_macro_data
# Logic:
#   Serialize data to JSON.
#   Insert or replace into 'macro_cache' with current timestamp.
#   Commit.

# Function: get_macro_data
# Logic:
#   Query 'macro_cache' by key.
#   Check validity_seconds against update_time.
#   If valid, return parsed JSON; else None.

# Function: clear_all_data
# Logic:
#   Delete all rows from all tables.
#   Commit.

import sqlite3
import pandas as pd
import os
import contextlib
import json
from datetime import datetime

class DataManager:
    """
    数据持久化层 (SQLite)
    负责所有数据库的直接读写操作，提供连接管理与模式迁移功能。
    [V3.62 Fix] 修复 ResourceWarning: unclosed database
    """
    def __init__(self, db_path='financial_data_v3.db'):
        self.db_path = db_path
        self._init_db()
        # 启动时检查数据库结构并自动迁移 (解决 quarter 列缺失问题)
        self._migrate_db()

    def _init_db(self):
        """初始化数据库表结构"""
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            with conn: # 自动 commit/rollback
                cursor = conn.cursor()
                
                # 1. 基金净值表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS fund_nav (
                        fund_code TEXT,
                        date TEXT,
                        nav REAL,
                        daily_change REAL,
                        PRIMARY KEY (fund_code, date)
                    )
                ''')
                
                # 2. 基金持仓表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS fund_holdings (
                        fund_code TEXT,
                        stock_code TEXT,
                        stock_name TEXT,
                        weight REAL,
                        quarter TEXT,
                        PRIMARY KEY (fund_code, stock_code)
                    )
                ''')
                
                # 3. 宏观数据缓存表 (KV存储)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS macro_cache (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        update_time TIMESTAMP
                    )
                ''')

    def _migrate_db(self):
        """自动检测并修复旧版数据库结构缺失的列"""
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            try:
                # 尝试查询 quarter 字段
                cursor.execute("SELECT quarter FROM fund_holdings LIMIT 0")
            except sqlite3.OperationalError:
                print("🔧 检测到旧版数据库模式，正在执行热迁移 (添加 quarter 字段)...")
                try:
                    cursor.execute("ALTER TABLE fund_holdings ADD COLUMN quarter TEXT DEFAULT 'Unknown'")
                    conn.commit()
                    print("✅ 数据库迁移成功！")
                except Exception as e:
                    print(f"❌ 数据库迁移失败: {e}")

    def get_connection_safe(self):
        """
        [New] 提供上下文管理器形式的连接，防止忘记关闭
        用法: with self.get_connection_safe() as conn: ...
        """
        return contextlib.closing(sqlite3.connect(self.db_path))

    def save_fund_nav(self, df):
        """保存基金净值历史"""
        if df.empty: return
        data_to_insert = []
        for _, row in df.iterrows():
            data_to_insert.append((
                str(row['fund_code']),
                str(row['date']),
                float(row['nav']),
                float(row['daily_change']) if pd.notna(row['daily_change']) else 0.0
            ))
        
        with self.get_connection_safe() as conn:
            with conn:
                cursor = conn.cursor()
                cursor.executemany('''
                    INSERT OR REPLACE INTO fund_nav (fund_code, date, nav, daily_change)
                    VALUES (?, ?, ?, ?)
                ''', data_to_insert)

    def get_fund_nav(self, fund_code):
        """读取基金净值历史"""
        with self.get_connection_safe() as conn:
            df = pd.read_sql(f"SELECT * FROM fund_nav WHERE fund_code='{fund_code}' ORDER BY date", conn)
            return df

    def save_fund_holdings(self, df):
        """保存基金持仓明细"""
        if df.empty: return
        
        data_to_insert = []
        for _, row in df.iterrows():
            q = row.get('quarter', 'Unknown')
            if pd.isna(q): q = 'Unknown'
            
            fund_code = str(row['fund_code'])
            stock_code = str(row['stock_code'])
            stock_name = str(row['stock_name'])
            try:
                weight = float(row['weight'])
            except:
                weight = 0.0
                
            data_to_insert.append((
                fund_code,
                stock_code,
                stock_name,
                weight,
                str(q)
            ))
            
        with self.get_connection_safe() as conn:
            with conn:
                cursor = conn.cursor()
                cursor.executemany('''
                    INSERT OR REPLACE INTO fund_holdings (fund_code, stock_code, stock_name, weight, quarter)
                    VALUES (?, ?, ?, ?, ?)
                ''', data_to_insert)

    def get_fund_holdings(self, fund_code):
        """读取基金持仓明细"""
        with self.get_connection_safe() as conn:
            df = pd.read_sql(f"SELECT * FROM fund_holdings WHERE fund_code='{fund_code}'", conn)
            return df

    def save_macro_data(self, key, data):
        """保存宏观数据缓存 (JSON格式)"""
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with self.get_connection_safe() as conn:
                with conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO macro_cache (key, value, update_time)
                        VALUES (?, ?, ?)
                    ''', (key, json_str, now_str))
        except Exception as e:
            print(f"❌ 宏观数据缓存失败: {e}")

    def get_macro_data(self, key, validity_seconds=3600):
        """读取宏观数据缓存 (带有效期检查)"""
        try:
            with self.get_connection_safe() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value, update_time FROM macro_cache WHERE key=?", (key,))
                row = cursor.fetchone()
                
                if row:
                    value_json, update_time_str = row
                    update_time = datetime.strptime(update_time_str, "%Y-%m-%d %H:%M:%S")
                    
                    # 检查是否过期
                    if (datetime.now() - update_time).total_seconds() < validity_seconds:
                        return json.loads(value_json)
                    else:
                        return None
        except Exception:
            pass
        return None

    def clear_all_data(self):
        """[Safe Reset] 清空所有表数据但保留表结构"""
        try:
            with self.get_connection_safe() as conn:
                with conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM fund_nav")
                    cursor.execute("DELETE FROM fund_holdings")
                    cursor.execute("DELETE FROM macro_cache")
                print("🧹 数据库已清空")
        except Exception as e:
            print(f"❌ 清空数据库失败: {e}")