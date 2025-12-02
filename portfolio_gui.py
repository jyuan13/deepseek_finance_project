import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

# [修复] 智能判断配置文件路径
# 确保 EXE 无论在哪运行，都只读取它旁边的 json
if getattr(sys, 'frozen', False):
    # 如果是打包后的 EXE
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 如果是 Python 脚本
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "my_portfolio.json")

class PortfolioEditor:
    def __init__(self, root):
        self.root = root
        self.root.title(f"DeepSeek 基金持仓配置管理器 (V3.2) - {CONFIG_FILE}")
        self.root.geometry("1200x650")
        
        self.data = {}
        self.filename = CONFIG_FILE
        self.load_data()
        
        # --- 1. 顶部：账户设置 ---
        frame_top = ttk.LabelFrame(root, text="📊 账户基础信息", padding="10")
        frame_top.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(frame_top, text="可用现金:").grid(row=0, column=0, padx=5)
        self.var_cash = tk.DoubleVar()
        ttk.Entry(frame_top, textvariable=self.var_cash, width=12).grid(row=0, column=1)
        
        ttk.Label(frame_top, text="总资产:").grid(row=0, column=2, padx=5)
        self.var_total = tk.DoubleVar()
        ttk.Entry(frame_top, textvariable=self.var_total, width=12).grid(row=0, column=3)
        
        ttk.Label(frame_top, text="风险偏好:").grid(row=0, column=4, padx=5)
        self.var_risk = tk.StringVar()
        ttk.Combobox(frame_top, textvariable=self.var_risk, values=["conservative", "balanced", "aggressive"], width=10).grid(row=0, column=5)
        
        ttk.Button(frame_top, text="💾 保存基础设置", command=self.save_global_settings).grid(row=0, column=6, padx=15)

        # --- 2. 中部：持仓列表 ---
        frame_mid = ttk.LabelFrame(root, text="💼 持仓明细", padding="10")
        frame_mid.pack(fill="both", expand=True, padx=10, pady=5)
        
        columns = ("comment", "symbol", "shares", "cost", "target", "limit", "dca", "type")
        self.tree = ttk.Treeview(frame_mid, columns=columns, show="headings")
        
        self.tree.heading("comment", text="备注 (说明)")
        self.tree.heading("symbol", text="代码")
        self.tree.heading("shares", text="份额")
        self.tree.heading("cost", text="成本")
        self.tree.heading("target", text="目标(%)")
        self.tree.heading("limit", text="限额")
        self.tree.heading("dca", text="定投额")
        self.tree.heading("type", text="类型")
        
        self.tree.column("comment", width=180, anchor="w")
        self.tree.column("symbol", width=80, anchor="center")
        self.tree.column("shares", width=80, anchor="center")
        self.tree.column("cost", width=60, anchor="center")
        self.tree.column("target", width=60, anchor="center")
        self.tree.column("limit", width=80, anchor="center")
        self.tree.column("dca", width=80, anchor="center")
        self.tree.column("type", width=80, anchor="center")
        
        self.tree.pack(fill="both", expand=True, side="left")
        
        scroll = ttk.Scrollbar(frame_mid, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)

        # --- 3. 底部：按钮 ---
        frame_bot = ttk.Frame(root, padding="10")
        frame_bot.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(frame_bot, text="➕ 新增", command=self.add_position).pack(side="left", padx=5)
        ttk.Button(frame_bot, text="✏️ 编辑", command=self.edit_position).pack(side="left", padx=5)
        ttk.Button(frame_bot, text="❌ 删除", command=self.delete_position).pack(side="left", padx=5)
        ttk.Button(frame_bot, text="🔄 刷新", command=self.refresh_tree).pack(side="right", padx=5)

        self.refresh_gui_data()

    def load_data(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except: self.data = {"positions_config": []}
        else:
            self.data = {"cash": 100000, "total_assets": 100000, "risk_profile": "balanced", "positions_config": []}
            self.save_file()

    def save_file(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("错误", str(e))
            return False

    def refresh_gui_data(self):
        self.var_cash.set(self.data.get("cash", 0))
        self.var_total.set(self.data.get("total_assets", 0))
        self.var_risk.set(self.data.get("risk_profile", "balanced"))
        self.refresh_tree()

    def refresh_tree(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for idx, pos in enumerate(self.data.get("positions_config", [])):
            comment = pos.get("//comment", pos.get("comment", ""))
            
            dca_val = "-"
            if pos.get("investment_type") == "dca" and "dca_config" in pos:
                dca_val = pos["dca_config"].get("base_amount", 0)

            self.tree.insert("", "end", iid=idx, values=(
                comment,
                pos.get("symbol"),
                pos.get("current_shares"),
                pos.get("cost_price"),
                pos.get("target_percent"),
                pos.get("max_invest_limit", 0),
                dca_val,
                pos.get("investment_type")
            ))

    def save_global_settings(self):
        self.data["cash"] = self.var_cash.get()
        self.data["total_assets"] = self.var_total.get()
        self.data["risk_profile"] = self.var_risk.get()
        if self.save_file(): messagebox.showinfo("成功", "账户信息已保存")

    def add_position(self): self.open_editor(True)
    
    def edit_position(self):
        sel = self.tree.selection()
        if sel: self.open_editor(False, int(sel[0]))

    def delete_position(self):
        sel = self.tree.selection()
        if sel and messagebox.askyesno("确认", "删除此持仓？"):
            del self.data["positions_config"][int(sel[0])]
            self.save_file()
            self.refresh_tree()

    def open_editor(self, is_new, index=None):
        win = tk.Toplevel(self.root)
        win.title("持仓编辑")
        win.geometry("450x650")
        
        item = self.data["positions_config"][index] if not is_new else {}
        
        current_comment = item.get("//comment", item.get("comment", ""))
        
        dca_base = 0.0
        if "dca_config" in item:
            dca_base = item["dca_config"].get("base_amount", 0.0)

        vars = {}
        fields = [
            ("备注/说明 (Comment)", "comment", str, current_comment),
            ("代码 (Symbol)", "symbol", str, item.get("symbol", "")),
            ("份额 (Shares)", "current_shares", float, item.get("current_shares", 0.0)), # [修复] 改为 float
            ("成本 (Cost)", "cost_price", float, item.get("cost_price", 0.0)),
            ("目标% (Target)", "target_percent", float, item.get("target_percent", 10)),
            ("允许偏差% (Dev)", "deviation_limit", float, item.get("deviation_limit", 3)),
            ("单日限额 (Limit)", "max_invest_limit", float, item.get("max_invest_limit", 0)),
            ("定投金额 (DCA Base)", "base_amount", float, dca_base),
        ]
        
        for lbl, key, dtype, val in fields:
            ttk.Label(win, text=lbl).pack(anchor="w", padx=20, pady=2)
            v = tk.StringVar(value=str(val))
            ttk.Entry(win, textvariable=v).pack(fill="x", padx=20, pady=5)
            vars[key] = v
            
        ttk.Label(win, text="类型 (Type)").pack(anchor="w", padx=20, pady=2)
        v_type = tk.StringVar(value=item.get("investment_type", "manual"))
        ttk.Combobox(win, textvariable=v_type, values=["manual", "dca"]).pack(fill="x", padx=20, pady=5)
        
        def save():
            try:
                new_item = item.copy()
                
                comment_val = vars["comment"].get().strip()
                if comment_val:
                    new_item["//comment"] = comment_val
                    if "comment" in new_item: del new_item["comment"]
                else:
                    if "//comment" in new_item: del new_item["//comment"]

                new_item["symbol"] = vars["symbol"].get().strip().upper()
                new_item["current_shares"] = float(vars["current_shares"].get()) # [修复] 保持 float
                new_item["cost_price"] = float(vars["cost_price"].get())
                new_item["target_percent"] = float(vars["target_percent"].get())
                new_item["deviation_limit"] = float(vars["deviation_limit"].get())
                new_item["max_invest_limit"] = float(vars["max_invest_limit"].get())
                new_item["investment_type"] = v_type.get()
                
                base_amount = float(vars["base_amount"].get())
                if new_item["investment_type"] == "dca":
                    if "dca_config" not in new_item:
                        new_item["dca_config"] = {}
                    new_item["dca_config"]["base_amount"] = base_amount
                    if "frequency" not in new_item["dca_config"]:
                        new_item["dca_config"]["frequency"] = "daily"
                        new_item["dca_config"]["execution_day"] = 1
                
                if not new_item["symbol"]: raise ValueError("代码不能为空")
                
                if is_new: self.data["positions_config"].append(new_item)
                else: self.data["positions_config"][index] = new_item
                
                self.save_file()
                self.refresh_tree()
                win.destroy()
            except Exception as e: messagebox.showerror("错误", str(e))

        ttk.Button(win, text="💾 保存配置", command=save).pack(pady=20)

if __name__ == "__main__":
    root = tk.Tk()
    app = PortfolioEditor(root)
    root.mainloop()