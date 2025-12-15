# deepseek_finance_project_V3/api_tester.py

import os
import time
import requests
import pandas as pd
import akshare as ak
import baostock as bs
import yfinance as yf
from duckduckgo_search import DDGS
import urllib3
import logging
from datetime import datetime

# 禁用 SSL 警告，保持与 data_provider 一致的测试环境
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

class APITester:
    """
    [V3.27] 接口连通性测试工具 (交互优化版)
    增加实时进度显示，解决"卡住"时不知道在干什么的问题
    """
    def __init__(self):
        self.keys = {
            "FMP": os.environ.get("FMP_API_Key"),
            "AV": os.environ.get("Alpha_Vantage_API_Key"),
            "TwelveData": os.environ.get("TwelveData_API_Key"),
            "Finnhub": os.environ.get("Finnhub_API_Key")
        }

    def _print_result(self, name, status, msg="", time_cost=0):
        """格式化打印测试结果 (覆盖当前行)"""
        # 清除当前行的 "⏳ 正在测试..."
        print(f"\r{' ' * 80}\r", end="", flush=True)
        
        if status == "OK":
            status_str = f"\033[92m[OK]\033[0m"
        elif status == "NOK":
            status_str = f"\033[91m[NOK]\033[0m"
        else:
            status_str = f"\033[93m[{status}]\033[0m"
            
        time_str = f"({time_cost:.2f}s)" if time_cost > 0 else ""
        # 截断过长的错误信息
        if len(msg) > 100: msg = msg[:97] + "..."
        print(f"   {status_str} {name:<40} {time_str} {msg}")

    def run_menu(self):
        while True:
            print("\n🔌 接口连通性测试工具 (API Tester)")
            print("="*60)
            print("1. 🇨🇳 AkShare (A股/港股/基金/宏观)")
            print("2. 🇺🇸 YFinance (美股/期货)")
            print("3. 📊 Baostock (A股历史)")
            print("4. 🔍 DuckDuckGo (舆情搜索)")
            print("5. 🔑 商业 API (FMP/AV/TwelveData/Finnhub)")
            print("-" * 60)
            print("9. 🚀 测试全部")
            print("0. 🔙 返回主菜单")
            print("="*60)
            
            choice = input("请选择测试对象 (0-9): ").strip()
            
            if choice == "1": self.test_akshare()
            elif choice == "2": self.test_yfinance()
            elif choice == "3": self.test_baostock()
            elif choice == "4": self.test_ddg()
            elif choice == "5": self.test_commercial_apis()
            elif choice == "9":
                self.test_akshare()
                self.test_yfinance()
                self.test_baostock()
                self.test_ddg()
                self.test_commercial_apis()
            elif choice == "0": break
            else: print("❌ 无效输入")

    def _run_test(self, name, func, *args):
        # [新增] 打印实时进度，使用 \r 回车符实现原地刷新
        print(f"   ⏳ 正在测试: {name:<35} ...", end="\r", flush=True)
        
        time.sleep(0.2) # 给一点时间让 print 刷新
        start_t = time.time()
        try:
            res = func(*args)
            cost = time.time() - start_t
            
            # 简单的有效性检查
            is_valid = False
            if isinstance(res, pd.DataFrame):
                is_valid = not res.empty
            elif isinstance(res, (list, dict)):
                is_valid = len(res) > 0
            elif res is not None:
                is_valid = True
                
            if is_valid:
                self._print_result(name, "OK", "", cost)
            else:
                self._print_result(name, "NOK", "返回数据为空", cost)
        except Exception as e:
            cost = time.time() - start_t
            err_msg = str(e).replace('\n', ' ')
            self._print_result(name, "NOK", f"Error: {err_msg}", cost)

    def test_akshare(self):
        print("\nTesting AkShare Interfaces (东方财富/新浪源)...")
        print("注意: AkShare 依赖网络爬虫，容易受 IP 限制或 SSL 问题影响。")
        
        # 1. A股实时
        self._run_test("A股实时快照 (stock_zh_a_spot_em)", getattr(ak, 'stock_zh_a_spot_em', None))
        
        # 2. 港股实时
        func = getattr(ak, 'stock_hk_spot_em', getattr(ak, 'stock_hk_spot', None))
        if func:
            self._run_test("港股实时快照 (stock_hk_spot_em)", func)
        else:
            self._print_result("港股实时快照", "SKIP", "接口未找到")
        
        # 3. 基金持仓
        if hasattr(ak, 'fund_portfolio_hold_em'):
            self._run_test("基金持仓 (fund_portfolio_hold_em)", ak.fund_portfolio_hold_em, "000001", "2024")
        else:
            self._print_result("基金持仓", "SKIP", "接口未找到")
        
        # 4. 基金净值
        if hasattr(ak, 'fund_open_fund_info_em'):
            self._run_test("基金净值 (fund_open_fund_info_em)", ak.fund_open_fund_info_em, "000001", "单位净值走势")
        
        # 5. 基金基本信息
        if hasattr(ak, 'fund_individual_basic_info_em'):
            self._run_test("基金档案 (fund_individual_basic_info_em)", ak.fund_individual_basic_info_em, "000001")
        else:
            if hasattr(ak, 'fund_em_open_fund_info'):
                self._run_test("基金档案 (旧版接口)", ak.fund_em_open_fund_info, "000001")
            else:
                self._print_result("基金档案", "SKIP", "当前AkShare版本不支持此接口")
        
        # 6. 宏观债市
        self._run_test("宏观债市 (bond_zh_us_rate)", getattr(ak, 'bond_zh_us_rate', None))
        
        # 7. 美股指数历史
        self._run_test("美股指数历史 (index_us_stock_sina)", getattr(ak, 'index_us_stock_sina', None), ".IXIC")
        
        # 8. 港股历史
        if hasattr(ak, 'stock_hk_hist'):
            self._run_test("港股历史日线 (stock_hk_hist)", ak.stock_hk_hist, "00700", "daily", "20240101", "qfq")

        # 9. 舆情相关
        if hasattr(ak, 'stock_news_em'):
            self._run_test("个股新闻 (stock_news_em)", ak.stock_news_em, "600519")
        
        if hasattr(ak, 'news_cctv_xwlb_em'):
            self._run_test("新闻联播 (news_cctv_xwlb_em)", ak.news_cctv_xwlb_em, datetime.now().strftime("%Y%m%d"))

    def test_yfinance(self):
        print("\nTesting YFinance Interfaces (Yahoo)...")
        print("注意: 国内网络可能会连接超时。")

        def test_yf_ticker():
            t = yf.Ticker("AAPL")
            return t.fast_info.last_price
            
        self._run_test("美股快照 (Ticker.fast_info)", test_yf_ticker)
        
        def test_yf_hist():
            return yf.download("^IXIC", period="5d", progress=False)
            
        self._run_test("美股历史 (download)", test_yf_hist)
        
        def test_yf_hk():
            t = yf.Ticker("00700.HK")
            return t.fast_info.last_price
            
        self._run_test("港股快照 (00700.HK)", test_yf_hk)

    def test_baostock(self):
        print("\nTesting Baostock Interfaces...")
        print("注意: 登录可能需要几秒钟，请耐心等待。")
        
        def test_bs_kline():
            # [V3.27 优化] 增加 try-finally 确保退出登录
            try:
                lg = bs.login()
                if lg.error_code != '0':
                    raise Exception(f"Login failed: {lg.error_msg}")
                    
                rs = bs.query_history_k_data_plus("sh.600000",
                    "date,code,open,high,low,close",
                    start_date='2024-01-01', end_date='2024-01-10',
                    frequency="d", adjustflag="3")
                
                if rs.error_code != '0':
                    raise Exception(f"Query failed: {rs.error_msg}")
                    
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())
                return data_list
            finally:
                bs.logout()

        self._run_test("A股历史K线 (query_history_k_data_plus)", test_bs_kline)

    def test_ddg(self):
        print("\nTesting DuckDuckGo Search...")
        
        def test_ddgs():
            with DDGS() as ddgs:
                return list(ddgs.text("OpenAI", max_results=3))
                
        self._run_test("关键词搜索 (text)", test_ddgs)

    def test_commercial_apis(self):
        print("\nTesting Commercial APIs (Need Keys)...")
        
        # FMP
        if self.keys["FMP"]:
            def test_fmp():
                url = f"https://financialmodelingprep.com/api/v3/quote/AAPL?apikey={self.keys['FMP']}"
                return requests.get(url, timeout=5, verify=False).json()
            self._run_test("FMP Quote (AAPL)", test_fmp)
        else:
            self._print_result("FMP Quote", "SKIP", "No Key Found")

        # Alpha Vantage
        if self.keys["AV"]:
            def test_av():
                url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IBM&apikey={self.keys['AV']}"
                return requests.get(url, timeout=5, verify=False).json()
            self._run_test("AlphaVantage Quote (IBM)", test_av)
        else:
            self._print_result("AlphaVantage Quote", "SKIP", "No Key Found")

        # Twelve Data
        if self.keys["TwelveData"]:
            def test_td():
                url = f"https://api.twelvedata.com/quote?symbol=AAPL&apikey={self.keys['TwelveData']}"
                return requests.get(url, timeout=5).json()
            self._run_test("TwelveData Quote (AAPL)", test_td)
        else:
            self._print_result("TwelveData Quote", "SKIP", "No Key Found")

        # Finnhub
        if self.keys["Finnhub"]:
            def test_fh():
                url = f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={self.keys['Finnhub']}"
                return requests.get(url, timeout=5).json()
            self._run_test("Finnhub Quote (AAPL)", test_fh)
        else:
            self._print_result("Finnhub Quote", "SKIP", "No Key Found")