# deepseek_finance_project_V3/portfolio_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
import re
from portfolio_manager import PortfolioManager

class PortfolioGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DeepSeek 持仓配置工具 V3.8 (Auto-Fix)")
        self.root.geometry("1000x720")
        
        # 初始化管理器
        self.pm = PortfolioManager()
        
        # 定义支持的指数预设
        self.index_presets = [
            ("🇺🇸 纳斯达克100 (^IXIC)", "^IXIC", "纳斯达克100"),
            ("🇺🇸 标普500 (^GSPC)", "^GSPC", "标普500"),
            ("🇺🇸 道琼斯工业 (^DJI)", "^DJI", "道琼斯"),
            ("🇨🇳 上证指数 (000001.SS)", "000001.SS", "上证指数"),
            ("🇨🇳 沪深300 (000300.SS)", "000300.SS", "沪深300"),
            ("🇨🇳 深证成指 (399001.SZ)", "399001.SZ", "深证成指"),
            ("🇭🇰 恒生指数 (^HSI)", "^HSI", "恒生指数"),
            ("🇭🇰 恒生科技 (^HSTECH)", "^HSTECH", "恒生科技"),
            ("🇯🇵 日经225 (^N225)", "^N225", "日经225"),
            ("🟡 COMEX黄金 (GC=F)", "GC=F", "黄金期货"),
            ("🛢️ WTI原油 (CL=F)", "CL=F", "WTI原油"),
            ("₿ 比特币 (BTC-USD)", "BTC-USD", "比特币")
        ]
        
        self.combo_values = [item[0] for item in self.index_presets]
        self.code_to_display = {item[1]: item[0] for item in self.index_presets}
        self.display_to_name = {item[0]: item[2] for item in self.index_presets}

        style = ttk.Style()
        style.configure("Bold.TLabel", font=("Segoe UI", 10, "bold"))
        
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.frame_funds = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_funds, text="📦 基金配置 (Funds)")
        self._init_funds_ui()
        
        self.frame_indices = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_indices, text="📈 指数配置 (Indices)")
        self._init_indices_ui()
        
        self.status_var = tk.StringVar()
        self.status_var.set("系统就绪")
        status_bar = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, bg="#f0f0f0", padx=5)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _init_funds_ui(self):
        list_frame = ttk.LabelFrame(self.frame_funds, text="当前基金持仓列表")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("symbol", "cost", "shares", "limit", "dca", "target", "comment")
        self.tree_funds = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        self.tree_funds.heading("symbol", text="代码")
        self.tree_funds.heading("cost", text="成本")
        self.tree_funds.heading("shares", text="份额")
        self.tree_funds.heading("limit", text="单日限额")
        self.tree_funds.heading("dca", text="定投额")
        self.tree_funds.heading("target", text="计划总额")
        self.tree_funds.heading("comment", text="备注")
        
        self.tree_funds.column("symbol", width=70, anchor="center")
        self.tree_funds.column("cost", width=60, anchor="e")
        self.tree_funds.column("shares", width=70, anchor="e")
        self.tree_funds.column("limit", width=60, anchor="e")
        self.tree_funds.column("dca", width=60, anchor="e")
        self.tree_funds.column("target", width=70, anchor="e")
        self.tree_funds.column("comment", width=120, anchor="w")
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree_funds.yview)
        self.tree_funds.configure(yscroll=scrollbar.set)
        self.tree_funds.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree_funds.bind("<<TreeviewSelect>>", self.on_fund_select)
        
        edit_frame = ttk.LabelFrame(self.frame_funds, text="新增 / 编辑", width=350)
        edit_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        edit_frame.pack_propagate(False) 
        
        self._create_labeled_entry(edit_frame, "基金代码 (如 013403):", "entry_fund_symbol")
        self._create_labeled_entry(edit_frame, "持仓成本价 (Cost Price):", "entry_fund_cost")
        self._create_labeled_entry(edit_frame, "持有份额 (Shares):", "entry_fund_shares")
        
        self._create_labeled_entry(edit_frame, "单日买入限额 (0或NA为不限):", "entry_fund_limit", default="NA")
        self._create_labeled_entry(edit_frame, "每日定投额度 (0或NA为非定投):", "entry_fund_dca", default="0")
        self._create_labeled_entry(edit_frame, "计划投资总额 (目标仓位):", "entry_fund_target", default="NA")
        
        self._create_labeled_entry(edit_frame, "备注 (策略/名称):", "entry_fund_comment")
        
        btn_frame = ttk.Frame(edit_frame)
        btn_frame.pack(pady=20, fill=tk.X, padx=10)
        
        ttk.Button(btn_frame, text="💾 保存 / 更新", command=self.save_fund).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(btn_frame, text="🗑️ 删除选中", command=self.delete_fund).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=2)
        
        ttk.Button(edit_frame, text="🧹 清空输入", command=self.clear_fund_inputs).pack(fill=tk.X, padx=12, pady=5)

        self.load_funds_list()

    def _create_labeled_entry(self, parent, label_text, var_name, default=""):
        tk.Label(parent, text=label_text, font=("Segoe UI", 9)).pack(anchor=tk.W, padx=10, pady=(8, 2))
        entry = ttk.Entry(parent)
        entry.pack(fill=tk.X, padx=10)
        if default: entry.insert(0, default)
        setattr(self, var_name, entry)

    def load_funds_list(self):
        for item in self.tree_funds.get_children():
            self.tree_funds.delete(item)
        try:
            positions = self.pm.get_fund_positions()
            for p in positions:
                dca_val = p.get('dca_config', {}).get('base_amount', 0)
                dca_str = str(dca_val) if dca_val > 0 else "NA"
                
                limit_val = p.get('max_invest_limit', 0)
                limit_str = str(limit_val) if limit_val > 0 else "NA"
                
                target_val = p.get('target_amount', 0)
                target_str = str(target_val) if target_val > 0 else "NA"

                self.tree_funds.insert("", tk.END, values=(
                    p['symbol'], 
                    p['cost_price'], 
                    p['current_shares'], 
                    limit_str,
                    dca_str,
                    target_str,
                    p.get('comment','')
                ))
        except AttributeError: pass

    def on_fund_select(self, event):
        selected = self.tree_funds.selection()
        if not selected: return
        values = self.tree_funds.item(selected[0])['values']
        
        self._set_entry(self.entry_fund_symbol, values[0])
        self._set_entry(self.entry_fund_cost, values[1])
        self._set_entry(self.entry_fund_shares, values[2])
        self._set_entry(self.entry_fund_limit, values[3])
        self._set_entry(self.entry_fund_dca, values[4])
        self._set_entry(self.entry_fund_target, values[5])
        self._set_entry(self.entry_fund_comment, values[6])

    def _set_entry(self, entry, value):
        entry.delete(0, tk.END)
        entry.insert(0, str(value))

    def save_fund(self):
        symbol = self.entry_fund_symbol.get().strip()
        if not symbol:
            messagebox.showwarning("提示", "请输入基金代码")
            return
            
        # [Fix V3.8] 强制补齐 6 位数字代码
        if symbol.isdigit() and len(symbol) < 6:
            symbol = symbol.zfill(6)
            self._set_entry(self.entry_fund_symbol, symbol) # 回显修正
            print(f"🔧 自动修正基金代码为: {symbol}")
        
        def parse_na(val):
            val = str(val).strip().upper()
            if val in ["NA", "N/A", "", "NAN", "NONE"]: return 0
            try: return float(val)
            except: return 0

        try:
            cost = parse_na(self.entry_fund_cost.get())
            shares = parse_na(self.entry_fund_shares.get())
            limit = parse_na(self.entry_fund_limit.get())
            dca_val = parse_na(self.entry_fund_dca.get())
            target = parse_na(self.entry_fund_target.get())
            
            dca_config = {"enabled": dca_val > 0, "base_amount": dca_val}

            self.pm.save_fund_position(
                symbol, cost, shares,
                self.entry_fund_comment.get(),
                limit, dca_config, target
            )
            self.status_var.set(f"基金 {symbol} 已保存")
            self.load_funds_list()
            self.clear_fund_inputs()
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def delete_fund(self):
        selected = self.tree_funds.selection()
        if not selected: return
        symbol = self.tree_funds.item(selected[0])['values'][0]
        if messagebox.askyesno("确认", f"确定要删除基金 {symbol} 吗？"):
            try:
                self.pm.remove_fund_position(str(symbol))
                self.load_funds_list()
                self.clear_fund_inputs()
                self.status_var.set(f"基金 {symbol} 已删除")
            except Exception as e:
                messagebox.showerror("删除失败", str(e))

    def clear_fund_inputs(self):
        self.entry_fund_symbol.delete(0, tk.END)
        self.entry_fund_cost.delete(0, tk.END)
        self.entry_fund_shares.delete(0, tk.END)
        self._set_entry(self.entry_fund_limit, "NA")
        self._set_entry(self.entry_fund_dca, "0")
        self._set_entry(self.entry_fund_target, "NA")
        self.entry_fund_comment.delete(0, tk.END)

    def _init_indices_ui(self):
        list_frame = ttk.LabelFrame(self.frame_indices, text="当前指数持仓列表")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("symbol", "name", "value", "pnl", "target", "comment")
        self.tree_indices = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        self.tree_indices.heading("symbol", text="代码")
        self.tree_indices.heading("name", text="名称")
        self.tree_indices.heading("value", text="市值(CNY)")
        self.tree_indices.heading("pnl", text="盈亏(%)")
        self.tree_indices.heading("target", text="计划总额")
        self.tree_indices.heading("comment", text="备注")
        
        self.tree_indices.column("symbol", width=80, anchor="center")
        self.tree_indices.column("name", width=100, anchor="w")
        self.tree_indices.column("value", width=80, anchor="e")
        self.tree_indices.column("pnl", width=60, anchor="e")
        self.tree_indices.column("target", width=80, anchor="e")
        self.tree_indices.column("comment", width=100, anchor="w")
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree_indices.yview)
        self.tree_indices.configure(yscroll=scrollbar.set)
        self.tree_indices.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree_indices.bind("<<TreeviewSelect>>", self.on_index_select)
        
        edit_frame = ttk.LabelFrame(self.frame_indices, text="新增 / 编辑", width=350)
        edit_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        edit_frame.pack_propagate(False)
        
        tk.Label(edit_frame, text="常用指数 (选择或直接输入代码):", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, padx=10, pady=(10, 2))
        self.entry_idx_symbol = ttk.Combobox(edit_frame, values=self.combo_values)
        self.entry_idx_symbol.pack(fill=tk.X, padx=10)
        self.entry_idx_symbol.bind("<<ComboboxSelected>>", self._on_combo_select)
        
        self._create_labeled_entry(edit_frame, "指数名称 (自动填充/可选):", "entry_idx_name")
        self._create_labeled_entry(edit_frame, "当前持仓市值 (人民币):", "entry_idx_value")
        self._create_labeled_entry(edit_frame, "当前总盈亏率 (%):", "entry_idx_pnl")
        self._create_labeled_entry(edit_frame, "计划投资总额 (0或NA为不限):", "entry_idx_target", default="NA")
        self._create_labeled_entry(edit_frame, "备注:", "entry_idx_comment")
        
        btn_frame = ttk.Frame(edit_frame)
        btn_frame.pack(pady=20, fill=tk.X, padx=10)
        
        ttk.Button(btn_frame, text="💾 保存指数", command=self.save_index).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(btn_frame, text="🗑️ 删除指数", command=self.delete_index).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=2)
        
        ttk.Button(edit_frame, text="🧹 清空输入", command=self.clear_index_inputs).pack(fill=tk.X, padx=12, pady=5)
        
        self.load_indices_list()

    def _on_combo_select(self, event):
        selection = self.entry_idx_symbol.get()
        if selection in self.display_to_name:
            if not self.entry_idx_name.get().strip():
                self.entry_idx_name.delete(0, tk.END)
                self.entry_idx_name.insert(0, self.display_to_name[selection])

    def load_indices_list(self):
        for item in self.tree_indices.get_children():
            self.tree_indices.delete(item)
        try:
            positions = self.pm.get_index_positions()
            for p in positions:
                target_val = p.get('target_amount', 0)
                target_str = str(target_val) if target_val > 0 else "NA"
                
                self.tree_indices.insert("", tk.END, values=(
                    p['symbol'], 
                    p.get('name', ''), 
                    p['market_value_cny'], 
                    p['pnl_rate'], 
                    target_str,
                    p.get('comment', '')
                ))
        except AttributeError: pass

    def on_index_select(self, event):
        selected = self.tree_indices.selection()
        if not selected: return
        values = self.tree_indices.item(selected[0])['values']
        
        symbol_code = values[0]
        display_str = self.code_to_display.get(symbol_code, symbol_code)
        
        self.entry_idx_symbol.delete(0, tk.END)
        self.entry_idx_symbol.insert(0, display_str)
        self._set_entry(self.entry_idx_name, values[1])
        self._set_entry(self.entry_idx_value, values[2])
        self._set_entry(self.entry_idx_pnl, values[3])
        self._set_entry(self.entry_idx_target, values[4])
        self._set_entry(self.entry_idx_comment, values[5])

    def save_index(self):
        raw_input = self.entry_idx_symbol.get().strip()
        if not raw_input:
            messagebox.showwarning("提示", "请输入或选择指数")
            return
            
        match = re.search(r'\((.*?)\)$', raw_input)
        real_symbol = match.group(1) if match else raw_input
        
        def parse_na(val):
            val = str(val).strip().upper()
            if val in ["NA", "N/A", "", "NAN", "NONE"]: return 0
            try: return float(val)
            except: return 0
            
        try:
            self.pm.save_index_position(
                real_symbol,
                parse_na(self.entry_idx_value.get()),
                parse_na(self.entry_idx_pnl.get()),
                self.entry_idx_name.get(),
                self.entry_idx_comment.get(),
                parse_na(self.entry_idx_target.get())
            )
            self.status_var.set(f"指数 {real_symbol} 已保存")
            self.load_indices_list()
            self.clear_index_inputs()
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def delete_index(self):
        selected = self.tree_indices.selection()
        if not selected: return
        symbol = self.tree_indices.item(selected[0])['values'][0]
        if messagebox.askyesno("确认", f"确定要删除指数 {symbol} 吗？"):
            try:
                self.pm.remove_index_position(str(symbol))
                self.load_indices_list()
                self.clear_index_inputs()
                self.status_var.set(f"指数 {symbol} 已删除")
            except Exception as e:
                messagebox.showerror("删除失败", str(e))

    def clear_index_inputs(self):
        self.entry_idx_symbol.delete(0, tk.END)
        self.entry_idx_name.delete(0, tk.END)
        self.entry_idx_value.delete(0, tk.END)
        self.entry_idx_pnl.delete(0, tk.END)
        self._set_entry(self.entry_idx_target, "NA")
        self.entry_idx_comment.delete(0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = PortfolioGUI(root)
    root.mainloop()