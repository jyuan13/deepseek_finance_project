"""
==========================================================================================
【文件定义】
文件名: main.py
类名  : Main (Script)
==========================================================================================
【函数清单与逻辑流 (Function Logic Flow)】

1. check_dependencies
   [打印提示] -> [Try Import akshare, baostock]
          ↓
   (Success: Return True) / (Fail: Print Error & Return False)

2. print_banner
   [OS Clear Screen] -> [Print ASCII Art Banner] -> [Print Version & Build Date]

3. run_batch_update(fdm, pm)
   [打印维护模式警告] -> [Input 确认 'y'] -> {不匹配则返回}
          ↓
   [PM.get_fund_positions] -> [Loop: 遍历所有基金]
          ↓
   [FDM.update_fund_holdings(force=True)] -> [Print 成功/失败]
          ↓
   [Print 统计结果]

4. run_gui_build
   [打印构建提示]
          ↓
   [构建 pyinstaller 指令]
     --onefile (单文件)
     --windowed (无黑框)
     --distpath . (生成在根目录)
     --clean (清理缓存)
     portfolio_gui.py (入口文件)
          ↓
   [OS System Execute] -> [Check Return Code]
          ↓
   (Success: Print Path & Clean temp files) / (Fail: Print Error)

5. main
   [Check Dependencies] -> [Print Banner]
          ↓
   [Init Logger, DeepSeekClient, FDM, PM]
          ↓
   [Init FinancialAnalyzer (注入依赖)]
          ↓
   [While True Loop]
     [Print Menu Options 1-7, 99, 0] -> [Input Choice]
     [Case 1: analyzer.run_analysis_menu()] -> [运行时自动计算]
     [Case 2: os.system("python portfolio_gui.py")] -> [启动 Lite 配置工具]
     [Case 3: analyzer.manage_rag_system()] -> [原功能4上移]
     [Case 4: analyzer._run_step_debug_mode()] -> [原功能5上移]
     [Case 5: run_gui_build()] -> [原功能6上移]
     [Case 6: run_batch_update(fdm, pm)] -> [原功能7上移]
     [Case 7: APITester.run_menu()] -> [原功能8上移]
     [Case 99: analyzer.perform_system_reset()]
     [Case 0: Exit]
     [Exception Handling]
==========================================================================================
"""

import os
import sys
import time
import shutil
from datetime import datetime
from deepseek_client import DeepSeekClient
from fund_data_manager import FundDataManager
from portfolio_manager import PortfolioManager
from operation_logger import OperationLogger
from finance_analyzer import FinancialAnalyzer
from api_tester import APITester

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def check_dependencies():
    print(f"{Colors.CYAN}🔄 正在自检核心数据源库 (AkShare/Baostock)...{Colors.ENDC}")
    try:
        import akshare
        import baostock
        print(f"   {Colors.GREEN}✅ 依赖库自检完毕{Colors.ENDC}")
        return True
    except ImportError as e:
        print(f"   {Colors.FAIL}❌ 缺失依赖库: {e}{Colors.ENDC}")
        return False

def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{Colors.BLUE}")
    print(r"""
  ____                  ____            _    
 |  _ \  ___  ___ _ __ / ___|  ___  ___| | __
 | | | |/ _ \/ _ \ '_ \\___ \ / _ \/ _ \ |/ /
 | |_| |  __/  __/ |_) |___) |  __/  __/   < 
 |____/ \___|\___| .__/|____/ \___|\___|_|\_\
                 |_|                         
    """)
    print(f"{Colors.HEADER}    DeepSeek Finance Project V4.00 (Streamlined){Colors.ENDC}")
    print(f"    Architecture: Lite Config Tool / Runtime Analysis Engine")
    print(f"    Build Date: {datetime.now().strftime('%Y-%m-%d')}")
    print("============================================================")

def run_batch_update(fdm, pm):
    print(f"\n{Colors.WARNING}🔄 [维护模式] 开始更新本地持仓数据库...{Colors.ENDC}")
    if input(f"{Colors.BOLD}确认开始更新吗? (y/n): {Colors.ENDC}").lower() != 'y': return
    funds = pm.get_fund_positions()
    total = len(funds)
    print(f"\n📋 共有 {total} 只标的待更新...")
    for i, fund in enumerate(funds):
        code = fund['symbol']
        print(f"   [{i+1}/{total}] 正在更新 {code} ...", end="", flush=True)
        try:
            fdm.update_fund_holdings(code, force_update=True)
            print(f"\r   [{i+1}/{total}] {Colors.GREEN}✅ 更新成功: {code}{Colors.ENDC}          ")
        except Exception as e:
            print(f"\r   [{i+1}/{total}] {Colors.FAIL}❌ 更新失败 {code}: {str(e)[:50]}{Colors.ENDC}")
    input("\n按回车键继续...")

def run_gui_build():
    print(f"\n{Colors.CYAN}🔨 正在构建轻量级配置工具 (EXE -> 根目录)...{Colors.ENDC}")
    
    # [V4.0] 极简构建指令：不打包 pandas/akshare，体积 < 15MB
    cmd = 'pyinstaller --onefile --windowed --name="持仓配置小工具" --clean --distpath . portfolio_gui.py'
    
    print(f"⚡ 执行指令: {cmd}")
    print(f"{Colors.WARNING}⏳ 正在打包 (预计 10-20秒)...{Colors.ENDC}")
    
    ret = os.system(cmd)
    
    if ret == 0:
        print(f"\n{Colors.GREEN}✅ 构建成功！{Colors.ENDC}")
        print(f"📂 文件位置: {os.path.abspath('持仓配置小工具.exe')}")
        # 清理垃圾
        print("🧹 正在清理临时文件...")
        try:
            if os.path.exists("build"): shutil.rmtree("build")
            if os.path.exists("持仓配置小工具.spec"): os.remove("持仓配置小工具.spec")
            print("✨ 清理完成")
        except: pass
    else:
        print(f"\n{Colors.FAIL}❌ 构建失败 (Code: {ret}){Colors.ENDC}")
        print("请确保已安装: pip install pyinstaller")
    
    input("\n按回车键返回...")

def main():
    if not check_dependencies(): return
    print_banner()
    logger = OperationLogger()
    try: client = DeepSeekClient()
    except Exception as e:
        print(f"{Colors.FAIL}❌ DeepSeek 客户端初始化失败: {e}{Colors.ENDC}")
        return

    print("⏳ 正在初始化数据引擎...")
    fdm = FundDataManager()
    pm = PortfolioManager()
    analyzer = FinancialAnalyzer(client, fdm, pm, logger)
    time.sleep(0.5)

    while True:
        print_banner()
        print(f"{Colors.BOLD}功能菜单:{Colors.ENDC}")
        print("1. 🚀 智能金融分析 (运行时自动计算份额/净值)")
        print("2. 💼 投资组合管理 (Lite GUI)")
        print("3. 🧠 RAG 知识库管理")
        print("4. 🐞 分步调试模式")
        print("5. 🛠️ 构建配置工具 (Lite EXE)")
        print("-" * 60)
        print("6. 🔄 更新持仓数据")
        print("7. 🔌 接口连通性测试")
        print("-" * 60)
        print("99. 🧹 系统重置")
        print("0.  退出")
        print("============================================================")
        
        choice = input(f"{Colors.CYAN}指令 > {Colors.ENDC}").strip()
        
        try:
            if choice == "1": 
                analyzer.run_analysis_menu()
                input("\n按回车键返回...")
            elif choice == "2": 
                print(f"{Colors.GREEN}🚀 正在启动 GUI 配置工具...{Colors.ENDC}")
                os.system("python portfolio_gui.py")
            elif choice == "3": 
                analyzer.manage_rag_system()
            elif choice == "4": 
                analyzer._run_step_debug_mode()
                input("\n按回车键返回...")
            elif choice == "5": 
                run_gui_build()
            elif choice == "6": 
                run_batch_update(fdm, pm)
            elif choice == "7": 
                tester = APITester()
                tester.run_menu()
            elif choice == "99": 
                analyzer.perform_system_reset()
            elif choice == "0": 
                sys.exit()
            else: 
                print(f"{Colors.FAIL}❌ 无效指令{Colors.ENDC}")
        except KeyboardInterrupt: 
            break
        except Exception as e: 
            print(f"\n{Colors.FAIL}❌ 异常: {e}{Colors.ENDC}")
            import traceback
            traceback.print_exc()
            input()

if __name__ == "__main__":
    main()