# deepseek_finance_project_V3/data_manager.py

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
    """
    def __init__(self, db_path='financial_data_v3.db'):
        self.db_path = db_path
        self._init_db()
        # [Fix] 启动时检查数据库结构并自动迁移 (解决 quarter 列缺失问题)
        self._migrate_db()

    def _init_db(self):
        """初始化数据库表结构 (仅在文件不存在或表不存在时有效)"""
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
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
            
            # 2. 基金持仓表 (注意：旧版可能没有 quarter)
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
            
            conn.commit()

    def _migrate_db(self):
        """[V3.3 Fix] 自动检测并修复旧版数据库结构缺失的列"""
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            try:
                # 尝试查询 quarter 字段，如果不存在会抛出 OperationalError
                cursor.execute("SELECT quarter FROM fund_holdings LIMIT 0")
            except sqlite3.OperationalError:
                print("🔧 检测到旧版数据库模式，正在执行热迁移 (添加 quarter 字段)...")
                try:
                    # SQLite 支持动态添加列
                    cursor.execute("ALTER TABLE fund_holdings ADD COLUMN quarter TEXT DEFAULT 'Unknown'")
                    conn.commit()
                    print("✅ 数据库迁移成功！")
                except Exception as e:
                    print(f"❌ 数据库迁移失败: {e}")
                    print("💡 建议: 如果问题依旧，请手动删除目录下的 financial_data_v3.db 文件后重试")

    def get_connection(self):
        """
        [New V3.6] 为外部模块提供数据库连接 
        注意：调用方必须负责关闭连接，建议使用 with contextlib.closing(...) 管理
        """
        return sqlite3.connect(self.db_path)

    def save_fund_nav(self, df):
        """保存基金净值历史"""
        if df.empty: return
        # 转换 DataFrame 为 tuple 列表，确保格式正确
        data_to_insert = []
        for _, row in df.iterrows():
            data_to_insert.append((
                str(row['fund_code']),
                str(row['date']),
                float(row['nav']),
                float(row['daily_change']) if pd.notna(row['daily_change']) else 0.0
            ))
        
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT OR REPLACE INTO fund_nav (fund_code, date, nav, daily_change)
                VALUES (?, ?, ?, ?)
            ''', data_to_insert)
            conn.commit()

    def get_fund_nav(self, fund_code):
        """读取基金净值历史"""
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            df = pd.read_sql(f"SELECT * FROM fund_nav WHERE fund_code='{fund_code}' ORDER BY date", conn)
            return df

    def save_fund_holdings(self, df):
        """保存基金持仓明细"""
        if df.empty: return
        
        # [V3.3] 适配包含 quarter 的数据结构
        data_to_insert = []
        for _, row in df.iterrows():
            # 兼容处理：确保 quarter 字段存在
            q = row.get('quarter', 'Unknown')
            if pd.isna(q): q = 'Unknown'
            
            # 数据清洗：确保类型正确
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
            
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.cursor()
            # 使用 5 个占位符，匹配表结构
            cursor.executemany('''
                INSERT OR REPLACE INTO fund_holdings (fund_code, stock_code, stock_name, weight, quarter)
                VALUES (?, ?, ?, ?, ?)
            ''', data_to_insert)
            conn.commit()

    def get_fund_holdings(self, fund_code):
        """读取基金持仓明细"""
        with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
            # 获取该基金的所有持仓记录
            df = pd.read_sql(f"SELECT * FROM fund_holdings WHERE fund_code='{fund_code}'", conn)
            return df

    def save_macro_data(self, key, data):
        """保存宏观数据缓存 (JSON格式)"""
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO macro_cache (key, value, update_time)
                    VALUES (?, ?, ?)
                ''', (key, json_str, now_str))
                conn.commit()
        except Exception as e:
            print(f"❌ 宏观数据缓存失败: {e}")

    def get_macro_data(self, key, validity_seconds=3600):
        """读取宏观数据缓存 (带有效期检查)"""
        try:
            with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
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
        except Exception as e:
            pass
        return None

    def clear_all_data(self):
        """[Safe Reset] 清空所有表数据但保留表结构"""
        try:
            with contextlib.closing(sqlite3.connect(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM fund_nav")
                cursor.execute("DELETE FROM fund_holdings")
                cursor.execute("DELETE FROM macro_cache")
                conn.commit()
                print("🧹 数据库已清空")
        except Exception as e:
            print(f"❌ 清空数据库失败: {e}")