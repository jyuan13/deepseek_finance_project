#!/usr/bin/env python3
"""
DeepSeek Finance Project V3.0-06 (Investment Committee) - 主程序入口
"""

import os
import sys
import shutil
import subprocess
from dotenv import load_dotenv

load_dotenv()

from deepseek_client import DeepSeekClient
from fund_data_manager import FundDataManager
from portfolio_manager import PortfolioManager
from operation_logger import OperationLogger
from finance_analyzer import FinancialAnalyzer
from email_sender import EmailSender
from data_manager import DataManager

# --- 版本控制 ---
SYSTEM_VERSION = "V3.0-06"
BUILD_DATE = "2025-05-23"

def print_banner():
    print("=" * 60)
    print(f"    DeepSeek Finance Project {SYSTEM_VERSION} (Internal Build)")
    print(f"    Architecture: Multi-Agent Committee (Macro/News/CIO)")
    print(f"    Build Date: {BUILD_DATE}")
    print("=" * 60)

def auto_update_libs():
    """
    [V3.13] 启动时自动更新关键数据源库 (AkShare/Baostock)
    防止因数据源接口变更导致获取失败
    """
    target_libs = ["akshare", "baostock"]
    print("\n🔄 正在检查并更新核心数据源库 (AkShare/Baostock)...")
    print("   (使用 pypi.org 简易源，如果网络不通请手动更新)")
    
    for lib in target_libs:
        try:
            # 构造 pip 更新指令
            # pip install --upgrade package -i https://pypi.org/simple
            cmd = [
                sys.executable, "-m", "pip", "install", 
                "--upgrade", lib, 
                "-i", "https://pypi.org/simple"
            ]
            
            # 使用 subprocess 调用，静默输出，仅在报错时提示
            # stdout=subprocess.DEVNULL 可以隐藏正常输出，让启动界面更清爽
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # print(f"   ✅ {lib} 检查完毕")
        except Exception as e:
            print(f"   ⚠️ {lib} 自动更新失败: {e} (可忽略，继续运行)")
    
    print("   ✅ 依赖库检查完毕")

def build_gui_tool():
    print("\n🔨 正在构建持仓配置工具 (EXE)...")
    script_name = "portfolio_gui.py"
    if not os.path.exists(script_name):
        print(f"❌ 错误: 未找到 {script_name} 文件。")
        print("   请确保 portfolio_gui.py 存在于项目根目录下。")
        return

    # 打包指令
    cmd = f'pyinstaller --onefile --windowed --name="持仓配置小工具" --clean {script_name}'
    
    print(f"⚡ 执行指令: {cmd}")
    print("⏳ 正在打包，这可能需要几分钟，请耐心等待...")
    
    try:
        # shell=True 确保在 Windows/Linux 下都能找到命令
        ret = subprocess.call(cmd, shell=True)
        
        if ret == 0:
            print("\n✅ 构建成功！正在部署...")
            root_dir = os.getcwd()
            dist_dir = os.path.join(root_dir, "dist")
            exe_name = "持仓配置小工具.exe"
            src_exe = os.path.join(dist_dir, exe_name)
            dst_exe = os.path.join(root_dir, exe_name)
            
            if os.path.exists(src_exe):
                if os.path.exists(dst_exe):
                    os.remove(dst_exe) # 删除旧版
                shutil.move(src_exe, dst_exe)
                print(f"📂 EXE 已移动到项目根目录: {dst_exe}")
                
                # 清理垃圾文件 (可选)
                print("🧹 清理构建临时文件...")
                try:
                    if os.path.exists("build"): shutil.rmtree("build")
                    if os.path.exists("dist"): shutil.rmtree("dist")
                    if os.path.exists("持仓配置小工具.spec"): os.remove("持仓配置小工具.spec")
                except:
                    pass
                    
                print("✨ 一切就绪！您可以直接在文件夹中双击运行 '持仓配置小工具.exe'")
            else:
                print(f"⚠️ 未在 dist 目录找到 {exe_name}，请手动检查。")
        else:
            print("❌ 构建失败，请检查上方报错信息。")
            print("💡 提示: 请确认已安装 pyinstaller (pip install pyinstaller)")
            
    except Exception as e:
        print(f"❌ 发生异常: {e}")

def main():
    # [V3.13] 启动前先检查更新
    auto_update_libs()
    
    print_banner()
    
    # --- 用户配置区 ---
    # 在这里修改默认首选 AI ( "qwen" 或 "deepseek" )
    PREFERRED_PROVIDER = "qwen" 
    # ------------------

    qwen_key = os.environ.get("Qwen_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    
    api_key = None
    provider = PREFERRED_PROVIDER
    
    # 智能 Key 选择逻辑
    if PREFERRED_PROVIDER == "qwen" and qwen_key:
        print("✅ 检测到 Qwen API Key，激活 Qwen-Plus 思考模式...")
        api_key = qwen_key
        provider = "qwen"
    elif PREFERRED_PROVIDER == "deepseek" and deepseek_key:
        print("✅ 检测到 DeepSeek API Key...")
        api_key = deepseek_key
        provider = "deepseek"
    # 如果首选不可用，尝试备选
    elif qwen_key:
        print("⚠️ 首选 API 未找到，自动切换至 Qwen...")
        api_key = qwen_key
        provider = "qwen"
    elif deepseek_key:
        print("⚠️ 首选 API 未找到，自动切换至 DeepSeek...")
        api_key = deepseek_key
        provider = "deepseek"
    else:
        print("⚠️  未检测到任何 API Key")
        provider_input = input("请手动选择提供商 [1] Qwen / [2] DeepSeek: ").strip()
        if provider_input == "2":
            provider = "deepseek"
            api_key = input("API Key: ").strip()
        else:
            provider = "qwen"
            api_key = input("API Key: ").strip()

    try:
        client = DeepSeekClient(api_key=api_key, provider=provider)
        print(f"🚀 服务已连接: {provider.upper()} ({client.models['chat']})")
    except Exception as e:
        print(f"❌ AI 初始化失败: {e}")
        return

    try:
        dm = DataManager()
        fdm = FundDataManager()
    except Exception as e:
        print(f"❌ 数据层初始化失败: {e}")
        return

    try:
        pm = PortfolioManager()
        logger = OperationLogger()
        email_sender = EmailSender()
    except Exception as e:
        print(f"❌ 业务层初始化失败: {e}")
        return
    
    try:
        analyzer = FinancialAnalyzer(client, fdm, pm, logger)
        if not analyzer.kronos.is_active:
            print("⚠️  Kronos 模型未就绪 (请确保 'model' 文件夹存在)")
        else:
            print("✅ Kronos 预测引擎已就绪")
    except Exception as e:
        print(f"❌ 分析器初始化失败: {e}")
        return

    while True:
        print("\n" + "="*30 + f" 主菜单 ({SYSTEM_VERSION}) " + "="*30)
        print("1. 🚀 智能金融分析 (委员会模式)")
        print("2. 💼 投资组合管理")
        print("3. 📝 记录交易操作")
        print("4. 🧠 RAG 知识库管理")
        print("5. 📧 邮件通知配置")
        print("6. 🛠️ 构建持仓配置工具 (EXE)")
        print("-" * 66)
        print("99. 🧹 系统重置")
        print("0.  退出")
        print("=" * 66)
        
        choice = input("指令 > ").strip()
        
        if choice == "1": analyzer.run_analysis_menu()
        elif choice == "2": pm.manage_portfolio()
        elif choice == "3": logger.quick_log_operation()
        elif choice == "4": analyzer.manage_rag_system()
        elif choice == "5": email_sender.setup_email_config()
        elif choice == "6": build_gui_tool()
        elif choice == "99": analyzer.perform_system_reset()
        elif choice == "0":
            print("👋 再见！")
            break
        else:
            print("❌ 无效输入")

if __name__ == "__main__":
    main()