# deepseek_finance_project_V3/portfolio_gui.py

"""
==========================================================================================
【文件定义】
文件名: portfolio_gui.py
类名  : PortfolioGUI
==========================================================================================
【函数清单与逻辑流 (Function Logic Flow)】

1. __init__(root)
   [定义 Index Presets 数据 (Tuple结构)] -> [生成 combo_values/mappings]
          ↓
   [初始化 PortfolioManager (纯本地IO)]
          ↓
   [配置 UI 样式] -> [构建 Notebook & Tabs (Funds, Indices, General)] -> [构建 Status Bar]

2. _init_funds_ui
   [创建 Funds 列表框架] -> [配置 Treeview (代码, 市值, 盈亏, 限额, 定投, 目标, 备注)]
          ↓
   [绑定滚动条 & 选择事件] -> [创建右侧编辑区 (Label + Entry)] -> [加载数据 load_funds()]

3. load_funds
   [清空 Treeview] -> [从 PM 获取 positions]
          ↓
   [遍历] -> (直接读取 market_value/pnl_rate) -> [插入 Treeview]

4. save_fund
   [获取输入框数据] -> [数据校验 (代码补全, 数值转换)]
          ↓
   [调用 PM.save_fund_simple (只存配置, 不计算)] -> [刷新列表 & 清空输入] -> [更新状态栏]

5. on_fund_select(event)
   [获取选中的 Treeview Item] -> [清空输入框] -> [将 Item Values 回填至 Entry]

6. delete_fund
   [获取选中项] -> [弹窗确认] -> [调用 PM.remove_fund_position] -> [刷新列表 & 清空]

7. clear_fund
   [遍历所有 Funds Entry 组件] -> [调用 delete(0, END)]

8. _init_indices_ui
   [创建 Indices 列表框架] -> [配置 Treeview] -> [创建编辑区]
          ↓
   [配置 Combobox (常用指数预设)] -> [绑定事件] -> [加载数据 load_idx()]

9. _on_combo(event)
   [获取 Combobox 选中值] -> [查找 code_to_display 映射] -> [自动填入代码和名称]

10. load_idx
    [清空 Treeview] -> [从 PM 获取 index_positions] -> [插入 Treeview]

11. save_idx
    [获取输入] -> [调用 PM.save_index_position] -> [刷新列表 & 清空]

12. on_idx_select(event)
    [获取选中 Item] -> [回填至 Indices Entry]

13. delete_idx
    [获取选中项] -> [确认] -> [PM.remove_index_position] -> [刷新]

14. clear_idx
    [清空 Indices 输入框]

15. _init_general_ui
    [创建 General 框架] -> [创建 Cash/Risk 输入框] (已移除定投日) -> [加载数据 load_gen()]

16. load_gen
    [PM.get_cash_info] -> [PM.get_risk_profile] -> [回填 UI]

17. save_gen
    [获取输入] -> [PM.update_cash] -> [PM.save_strategy_config] -> [更新状态栏]

18. _create_entry(parent, label, var, default)
    [Helper] -> [创建 Label+Entry]
==========================================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox
from portfolio_manager import PortfolioManager

class PortfolioGUI:
    """
    持仓配置工具 V4.03 (Lite / Simplified)
    特性：
    1. 移除“定投日”配置，简化全局设置。
    2. 极简架构：无重型依赖，只负责 JSON 配置。
    3. 交互优化：无弹窗，状态栏反馈。
    """
    def __init__(self, root):
        self.root = root
        self.root.title("DeepSeek 持仓配置工具 V4.03 (Lite)")
        self.root.geometry("1000x720")
        
        # [Fix] 1. 数据定义绝对前置 (Tuple: Display, Code, Name)
        self.index_presets = [
            ("🇺🇸 纳斯达克100 (^IXIC)", "^IXIC", "纳斯达克100"),
            ("🇺🇸 标普500 (^GSPC)", "^GSPC", "标普500"),
            ("🇨🇳 上证指数 (000001.SS)", "000001.SS", "上证指数"),
            ("🇨🇳 沪深300 (000300.SS)", "000300.SS", "沪深300"),
            ("🇭🇰 恒生指数 (^HSI)", "^HSI", "恒生指数"),
            ("🇭🇰 恒生科技 (^HSTECH)", "^HSTECH", "恒生科技"),
            ("🇯🇵 日经225 (^N225)", "^N225", "日经225"),
            ("🟡 COMEX黄金 (GC=F)", "GC=F", "黄金期货"),
            ("₿ 比特币 (BTC-USD)", "BTC-USD", "比特币")
        ]
        # 提取列表供 Combobox 使用
        self.combo_values = [item[0] for item in self.index_presets]
        # 建立映射方便查找
        self.display_map = {item[0]: (item[1], item[2]) for item in self.index_presets}
        
        # 2. 初始化管理器
        self.pm = PortfolioManager()
        
        # 3. 样式配置
        style = ttk.Style()
        style.configure("Bold.TLabel", font=("Segoe UI", 10, "bold"))
        
        # 4. 主选项卡
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.frame_funds = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_funds, text="📦 股票/基金配置")
        self._init_funds_ui()
        
        self.frame_indices = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_indices, text="📈 指数配置")
        self._init_indices_ui()
        
        self.frame_general = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_general, text="⚙️ 全局配置")
        self._init_general_ui()
        
        # 5. 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪 - 请输入【市值】和【盈亏】，系统将自动反推份额")
        status_bar = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, bg="#f0f0f0", padx=5)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # ==================== 1. 股票/基金 UI ====================
    def _init_funds_ui(self):
        # 左侧列表
        list_frame = ttk.LabelFrame(self.frame_funds, text="已配置列表")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("symbol", "value", "pnl", "limit", "dca", "target", "comment")
        self.tree_funds = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        headers = ["代码", "市值(元)", "盈亏(%)", "限额", "定投", "目标", "备注"]
        widths = [80, 80, 60, 60, 60, 60, 100]
        
        for col, h, w in zip(columns, headers, widths):
            self.tree_funds.heading(col, text=h)
            self.tree_funds.column(col, width=w, anchor="center" if col=="symbol" else "e")
            
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree_funds.yview)
        self.tree_funds.configure(yscroll=scrollbar.set)
        self.tree_funds.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree_funds.bind("<<TreeviewSelect>>", self.on_fund_select)
        
        # 右侧编辑
        edit_frame = ttk.LabelFrame(self.frame_funds, text="编辑配置 (资产视角)", width=320)
        edit_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        edit_frame.pack_propagate(False)
        
        self._create_entry(edit_frame, "代码 (如 513120, 00700):", "e_f_sym")
        self._create_entry(edit_frame, "当前持仓市值 (CNY):", "e_f_val")
        self._create_entry(edit_frame, "当前盈亏率 (%, 如 -10.5):", "e_f_pnl")
        self._create_entry(edit_frame, "单日买入限额 (0为不限):", "e_f_lim", "0")
        self._create_entry(edit_frame, "每日定投额度 (0为非定投):", "e_f_dca", "0")
        self._create_entry(edit_frame, "目标总额 (0为不限):", "e_f_tar", "0")
        self._create_entry(edit_frame, "备注:", "e_f_com")
        
        btn_box = ttk.Frame(edit_frame)
        btn_box.pack(fill=tk.X, pady=20, padx=10)
        ttk.Button(btn_box, text="💾 保存配置", command=self.save_fund).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(btn_box, text="🗑️ 删除", command=self.delete_fund).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=2)
        ttk.Button(edit_frame, text="🧹 清空", command=self.clear_fund).pack(fill=tk.X, padx=12)
        
        self.load_funds()

    def load_funds(self):
        for i in self.tree_funds.get_children(): self.tree_funds.delete(i)
        for p in self.pm.get_fund_positions():
            # 优先显示 market_value
            val = p.get('market_value', p.get('cost_price', 0) * p.get('current_shares', 0))
            pnl = p.get('pnl_rate', 0.0)
            
            self.tree_funds.insert("", tk.END, values=(
                p['symbol'], 
                f"{val:.2f}", 
                f"{pnl:+.2f}%", 
                p.get('max_invest_limit', 0), 
                p.get('dca_config', {}).get('base_amount', 0), 
                p.get('target_amount', 0), 
                p.get('comment', '')
            ))

    def save_fund(self):
        try:
            sym = self.e_f_sym.get().strip()
            if not sym: return
            if sym.isdigit() and len(sym)<6: sym = sym.zfill(6)
            
            self.pm.save_fund_simple(
                sym, 
                float(self.e_f_val.get()), 
                float(self.e_f_pnl.get()),
                float(self.e_f_lim.get()),
                float(self.e_f_dca.get()),
                float(self.e_f_tar.get()),
                self.e_f_com.get()
            )
            self.load_funds()
            self.clear_fund()
            # 无弹窗，更新状态栏
            self.status_var.set(f"✅ 股票/基金 [{sym}] 配置已保存")
        except Exception as e: 
            messagebox.showerror("错误", f"输入格式错误: {str(e)}")

    def on_fund_select(self, e):
        sel = self.tree_funds.selection()
        if not sel: return
        v = self.tree_funds.item(sel[0])['values']
        self.clear_fund()
        self.e_f_sym.insert(0, v[0])
        self.e_f_val.insert(0, v[1])
        self.e_f_pnl.insert(0, v[2].replace('%','').replace('+',''))
        self.e_f_lim.insert(0, v[3])
        self.e_f_dca.insert(0, v[4])
        self.e_f_tar.insert(0, v[5])
        self.e_f_com.insert(0, v[6])

    def delete_fund(self):
        sel = self.tree_funds.selection()
        if sel:
            sym = self.tree_funds.item(sel[0])['values'][0]
            if messagebox.askyesno("确认", f"删除 {sym}?"):
                self.pm.remove_fund_position(str(sym))
                self.load_funds()
                self.clear_fund()
                self.status_var.set(f"🗑️ 已删除 {sym}")

    def clear_fund(self):
        for e in [self.e_f_sym, self.e_f_val, self.e_f_pnl, self.e_f_lim, self.e_f_dca, self.e_f_tar, self.e_f_com]:
            e.delete(0, tk.END)

    # ==================== 2. 指数 UI ====================
    def _init_indices_ui(self):
        list_frame = ttk.LabelFrame(self.frame_indices, text="已配置指数")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("symbol", "value", "pnl", "target", "comment")
        self.tree_idx = ttk.Treeview(list_frame, columns=columns, show="headings")
        for col, h in zip(columns, ["代码", "市值", "盈亏", "目标", "备注"]):
            self.tree_idx.heading(col, text=h)
            self.tree_idx.column(col, width=80, anchor="e")
            
        self.tree_idx.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree_idx.bind("<<TreeviewSelect>>", self.on_idx_select)
        
        edit_frame = ttk.LabelFrame(self.frame_indices, text="编辑指数", width=320)
        edit_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        edit_frame.pack_propagate(False)
        
        tk.Label(edit_frame, text="常用代码:", font=("Segoe UI", 8)).pack(anchor=tk.W, padx=10, pady=(5,0))
        # 这里的 self.combo_values 已经在 __init__ 头部定义
        self.combo_idx = ttk.Combobox(edit_frame, values=self.combo_values)
        self.combo_idx.pack(fill=tk.X, padx=10, pady=2)
        self.combo_idx.bind("<<ComboboxSelected>>", self._on_combo)
        
        self._create_entry(edit_frame, "指数代码:", "e_i_sym")
        self._create_entry(edit_frame, "指数名称:", "e_i_name")
        self._create_entry(edit_frame, "市值 (CNY):", "e_i_val")
        self._create_entry(edit_frame, "盈亏 (%):", "e_i_pnl")
        self._create_entry(edit_frame, "目标总额:", "e_i_tar", "0")
        self._create_entry(edit_frame, "备注:", "e_i_com")
        
        btn_box = ttk.Frame(edit_frame)
        btn_box.pack(fill=tk.X, pady=20, padx=10)
        ttk.Button(btn_box, text="💾 保存", command=self.save_idx).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(btn_box, text="🗑️ 删除", command=self.delete_idx).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=2)
        ttk.Button(edit_frame, text="🧹 清空", command=self.clear_idx).pack(fill=tk.X, padx=12)
        
        self.load_idx()

    def _on_combo(self, e):
        val = self.combo_idx.get()
        if val in self.display_map:
            code, name = self.display_map[val]
            self.e_i_sym.delete(0, tk.END)
            self.e_i_sym.insert(0, code)
            self.e_i_name.delete(0, tk.END)
            self.e_i_name.insert(0, name)

    def load_idx(self):
        for i in self.tree_idx.get_children(): self.tree_idx.delete(i)
        for p in self.pm.get_index_positions():
            self.tree_idx.insert("", tk.END, values=(
                p['symbol'], p['market_value_cny'], p['pnl_rate'], 
                p.get('target_amount',0), p.get('comment','')
            ))

    def save_idx(self):
        try:
            self.pm.save_index_position(
                self.e_i_sym.get(), float(self.e_i_val.get()), float(self.e_i_pnl.get()),
                self.e_i_name.get(), self.e_i_com.get(), float(self.e_i_tar.get())
            )
            self.load_idx()
            self.clear_idx()
            self.status_var.set(f"✅ 指数 [{self.e_i_sym.get()}] 配置已保存")
        except Exception as e: messagebox.showerror("错误", str(e))

    def on_idx_select(self, e):
        sel = self.tree_idx.selection()
        if not sel: return
        v = self.tree_idx.item(sel[0])['values']
        self.clear_idx()
        self.e_i_sym.insert(0, v[0])
        self.e_i_val.insert(0, v[1])
        self.e_i_pnl.insert(0, v[2])
        self.e_i_tar.insert(0, v[3])
        self.e_i_com.insert(0, v[4])

    def delete_idx(self):
        sel = self.tree_idx.selection()
        if sel:
            self.pm.remove_index_position(self.tree_idx.item(sel[0])['values'][0])
            self.load_idx()
            self.clear_idx()
            self.status_var.set("🗑️ 已删除选中指数")

    def clear_idx(self):
        for e in [self.e_i_sym, self.e_i_name, self.e_i_val, self.e_i_pnl, self.e_i_tar, self.e_i_com]:
            e.delete(0, tk.END)

    # ==================== 3. 全局配置 UI ====================
    def _init_general_ui(self):
        frame = ttk.LabelFrame(self.frame_general, text="基础设置")
        frame.pack(fill=tk.X, padx=20, pady=20)
        self._create_entry(frame, "现金余额 (CNY):", "e_g_cash")
        # [V4.03] 已移除定投日配置
        self._create_entry(frame, "风险偏好:", "e_g_risk", "balanced")
        ttk.Button(frame, text="💾 保存设置", command=self.save_gen).pack(pady=10)
        self.load_gen()

    def _create_entry(self, parent, label, var, default=""):
        tk.Label(parent, text=label).pack(anchor=tk.W, padx=10, pady=(5,0))
        e = ttk.Entry(parent)
        e.pack(fill=tk.X, padx=10)
        if default: e.insert(0, default)
        setattr(self, var, e)

    def load_gen(self):
        try:
            self.e_g_cash.insert(0, self.pm.get_cash_info())
            # investment_strategies 中已不再强制需要 weekly_investment_day
            self.e_g_risk.insert(0, self.pm.get_risk_profile())
        except: pass

    def save_gen(self):
        try:
            self.pm.update_cash(float(self.e_g_cash.get()))
            # 只保存必要策略，忽略定投日
            self.pm.save_strategy_config({
                "dca_enabled": True,
                "risk_profile": self.e_g_risk.get()
            })
            self.status_var.set("✅ 全局基础设置已保存")
        except Exception as e: messagebox.showerror("错误", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = PortfolioGUI(root)
    root.mainloop()