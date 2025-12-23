import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd

# Set font to be like scientific journals
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']

class InnervationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Innervation Analysis (Prism Style + Stats)")
        self.root.geometry("600x550")

        self.group_data = {"Control": [], "CFA": [], "Carrageenan": []}

        # --- HEADER ---
        header_frame = tk.Frame(root)
        header_frame.pack(pady=15)
        tk.Label(header_frame, text="Innervation Analyzer", font=("Arial", 18, "bold")).pack()
        tk.Label(header_frame, text="Style: Publication Ready (Prism-like)", 
                 font=("Arial", 10, "italic"), fg="gray").pack()

        # --- INPUT ROWS ---
        container = tk.Frame(root)
        container.pack(pady=10, fill="x", padx=20)
        
        self.create_row(container, "Control (Right)", "Control")
        self.create_row(container, "CFA (Left)", "CFA")
        self.create_row(container, "Carrageenan (Left)", "Carrageenan")

        # --- RUN BUTTON ---
        # FIX 1: Black Text on Light Gray background
        tk.Button(root, text="CREATE FIGURE & SHOW STATS", command=self.run_analysis, 
                  bg="#e0e0e0", fg="black", font=("Arial", 12, "bold"), 
                  height=2, width=30, activebackground="#cccccc").pack(pady=30)

    def create_row(self, parent, label_text, group_key):
        frame = tk.Frame(parent, pady=8)
        frame.pack(fill="x")
        
        tk.Label(frame, text=label_text, width=20, anchor="w", font=("Arial", 11, "bold")).pack(side="left")
        status_lbl = tk.Label(frame, text="0 mice", fg="red", width=12, anchor="w")
        
        btn_add = tk.Button(frame, text="+ Add Files", 
                            command=lambda: self.add_files(group_key, status_lbl))
        btn_add.pack(side="left", padx=5)

        btn_clear = tk.Button(frame, text="Clear", bg="#eeeeee",
                              command=lambda: self.clear_files(group_key, status_lbl))
        btn_clear.pack(side="left", padx=2)
        status_lbl.pack(side="left", padx=10)

    def add_files(self, group_key, status_lbl):
        file_paths = filedialog.askopenfilenames(title=f"Add files for {group_key}", 
                                                 filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not file_paths: return
        
        for path in file_paths:
            mean_val = self.process_file(path)
            if mean_val is not None: self.group_data[group_key].append(mean_val)
        
        cnt = len(self.group_data[group_key])
        status_lbl.config(text=f"{cnt} mice", fg="green" if cnt > 0 else "red")

    def clear_files(self, group_key, status_lbl):
        self.group_data[group_key] = []
        status_lbl.config(text="0 mice", fg="red")

    def process_file(self, file_path):
        try:
            values = []
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        try: values.append(float(parts[-1]))
                        except ValueError: continue
            return np.mean(values) if values else None
        except: return None

    def run_analysis(self):
        # Validation
        for name, data in self.group_data.items():
            if not data:
                messagebox.showwarning("Missing Data", f"Please add files for {name}")
                return

        group_names = ["Control", "CFA", "Carrageenan"]
        data_list = [self.group_data[n] for n in group_names]
        all_vals = np.concatenate(data_list)
        all_labels = np.concatenate([[n]*len(self.group_data[n]) for n in group_names])

        # FIX 2: Explicit Stats Calculation
        try:
            # 1. ANOVA
            f_stat, p_anova = stats.f_oneway(*data_list)
            
            # 2. TUKEY
            tukey = pairwise_tukeyhsd(endog=all_vals, groups=all_labels, alpha=0.05)
            tukey_data = pd.DataFrame(data=tukey.summary().data[1:], columns=tukey.summary().data[0])
            
            # Show the stats report window
            self.show_stats_popup(p_anova, tukey_data)
            
        except Exception as e:
            messagebox.showerror("Stats Error", f"Could not calculate stats.\nNeed at least 2 mice per group.\n\nError: {e}")
            return

        # Plot
        self.plot_prism_style(self.group_data, group_names, tukey_data)

    def show_stats_popup(self, p_anova, tukey_df):
        """Creates a new window to display the exact P-values."""
        top = tk.Toplevel(self.root)
        top.title("Statistical Report")
        top.geometry("500x400")
        
        text_box = tk.Text(top, padx=10, pady=10, font=("Consolas", 10))
        text_box.pack(fill="both", expand=True)
        
        report = f"--- STATISTICAL ANALYSIS RESULTS ---\n\n"
        report += f"ONE-WAY ANOVA:\n"
        report += f"P-Value: {p_anova:.5f}\n"
        report += f"Significant? {'YES (p<0.05)' if p_anova < 0.05 else 'NO'}\n\n"
        
        report += f"TUKEY MULTIPLE COMPARISONS:\n"
        report += "-"*45 + "\n"
        report += f"{'Group 1':<12} | {'Group 2':<12} | {'P-Value':<8} | {'Sig?'}\n"
        report += "-"*45 + "\n"
        
        for index, row in tukey_df.iterrows():
            g1, g2 = row['group1'], row['group2']
            pval = row['p-adj']
            sig = "YES *" if pval < 0.05 else "ns"
            report += f"{g1:<12} | {g2:<12} | {pval:.4f}   | {sig}\n"
            
        text_box.insert(tk.END, report)
        text_box.config(state="disabled") # Make read-only

    def plot_prism_style(self, groups, group_names, tukey_data):
        means = [np.mean(groups[n]) for n in group_names]
        sems = [stats.sem(groups[n]) for n in group_names]
        
        fig, ax = plt.subplots(figsize=(7, 6))
        
        # Colors
        bar_colors = ['#E0E0E0', '#FFCDD2', '#BBDEFB'] 
        edge_colors = ['#424242', '#D32F2F', '#1976D2'] 
        
        # Bars
        ax.bar(group_names, means, yerr=sems, capsize=0, 
               color=bar_colors, edgecolor=edge_colors, 
               linewidth=2.5, width=0.6, alpha=0.9)
        
        # Distinct Error Bars
        ax.errorbar(group_names, means, yerr=sems, fmt='none', ecolor='black', elinewidth=2.5, capsize=6, capthick=2.5)

        # Scatter Points
        for i, name in enumerate(group_names):
            y = groups[name]
            x = np.random.normal(i, 0.04, size=len(y))
            ax.scatter(x, y, color='black', alpha=0.8, s=60, zorder=3, edgecolors='white', linewidth=0.5)

        # Style Axes
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(2)
        ax.spines['bottom'].set_linewidth(2)
        ax.tick_params(axis='both', which='major', width=2, length=6, labelsize=12)

        ax.set_ylabel('Innervation Index', fontsize=14, fontweight='bold', labelpad=10)
        ax.set_title('Footpad Innervation', fontsize=16, fontweight='bold', pad=20)

        # Draw Brackets ONLY if significant
        y_max = max([max(groups[n]) for n in group_names])
        curr_y = y_max
        
        def get_pval(g1, g2):
            row = tukey_data[((tukey_data['group1'] == g1) & (tukey_data['group2'] == g2)) | 
                             ((tukey_data['group1'] == g2) & (tukey_data['group2'] == g1))]
            if not row.empty: return row['p-adj'].values[0]
            return 1.0

        comparisons = [(0, 1, "Control", "CFA"), (0, 2, "Control", "Carrageenan"), (1, 2, "CFA", "Carrageenan")]
        
        for idx1, idx2, name1, name2 in comparisons:
            p_val = get_pval(name1, name2)
            if p_val < 0.05:
                curr_y = self.draw_bracket(ax, idx1, idx2, curr_y, p_val)

        ax.set_ylim(0, curr_y * 1.1)
        plt.tight_layout()
        plt.show()

    def draw_bracket(self, ax, x1, x2, y_start, p_val):
        h = y_start * 0.03
        y_top = y_start + h * 3
        
        ax.plot([x1, x1, x2, x2], [y_top-h, y_top, y_top, y_top-h], lw=2, c='black')
        
        stars = "ns"
        if p_val < 0.001: stars = "***"
        elif p_val < 0.01: stars = "**"
        elif p_val < 0.05: stars = "*"
        
        ax.text((x1 + x2) * 0.5, y_top, stars, ha='center', va='bottom', fontsize=16, fontweight='bold')
        return y_top 

if __name__ == "__main__":
    root = tk.Tk()
    app = InnervationApp(root)
    root.mainloop()