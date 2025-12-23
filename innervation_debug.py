import tkinter as tk
from tkinter import filedialog, messagebox
import sys
import os

# --- 1. SAFE IMPORTS ---
# This block checks if you have the libraries installed.
try:
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    from scipy import stats
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
except ImportError as missing_lib:
    # If missing, show a popup window and exit
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Missing Library", 
                         f"Could not load required libraries.\n\nError: {missing_lib}\n\nPlease run: pip install pandas numpy matplotlib scipy statsmodels")
    sys.exit()

class InnervationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Innervation Analysis (Debug Mode)")
        self.root.geometry("550x500")

        self.group_data = {"Control": [], "CFA": [], "Carrageenan": []}
        self.file_counts = {"Control": 0, "CFA": 0, "Carrageenan": 0}

        # UI Header
        tk.Label(root, text="Innervation Data Analyzer", font=("Arial", 16, "bold")).pack(pady=10)
        tk.Label(root, text="Instructions:\n1. Select ALL text files for a group at once.\n(e.g., select 5 files for 5 mice)", 
                 font=("Arial", 10), bg="#f0f0f0").pack(pady=5, fill="x")

        # Input Rows
        self.create_row("Control (Right Feet)", "Control")
        self.create_row("CFA (Left Feet)", "CFA")
        self.create_row("Carrageenan (Left Feet)", "Carrageenan")

        # Run Button
        tk.Button(root, text="GENERATE GRAPH", command=self.safe_run_analysis, 
                  bg="#2196F3", fg="white", font=("Arial", 12, "bold"), height=2).pack(pady=30)
        
        # Status Log
        self.log_box = tk.Text(root, height=8, width=60, font=("Consolas", 9))
        self.log_box.pack(pady=5)
        self.log("Ready. Please load files.")

    def log(self, message):
        """Prints messages to the window so you can see what's happening."""
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)
        print(message) # Also print to console

    def create_row(self, label_text, group_key):
        frame = tk.Frame(self.root)
        frame.pack(pady=5, fill="x", padx=20)
        tk.Label(frame, text=label_text, width=25, anchor="w", font=("Arial", 10, "bold")).pack(side="left")
        btn = tk.Button(frame, text="Select Files...", command=lambda: self.load_files(group_key, status_lbl))
        btn.pack(side="right")
        status_lbl = tk.Label(frame, text="0 files", fg="gray", width=10)
        status_lbl.pack(side="right", padx=10)

    def load_files(self, group_key, status_label):
        file_paths = filedialog.askopenfilenames(title=f"Select {group_key} Files", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not file_paths: return

        loaded_values = []
        self.log(f"--- Loading {group_key} ---")
        
        for path in file_paths:
            val = self.process_file(path)
            if val is not None:
                loaded_values.append(val)
        
        # Update Data
        self.group_data[group_key] = loaded_values
        self.file_counts[group_key] = len(loaded_values)
        
        # Update UI
        color = "green" if len(loaded_values) > 0 else "red"
        status_label.config(text=f"{len(loaded_values)} mice", fg=color)
        self.log(f"Successfully loaded {len(loaded_values)} mice for {group_key}.")

    def process_file(self, file_path):
        """Reads a file safely, even if it has weird text."""
        try:
            values = []
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    parts = line.strip().split() # Split by space or tab
                    if not parts: continue # Skip empty lines
                    
                    # Try to turn the LAST thing on the line into a number
                    # This works for "Image.tif 5.5" AND just "5.5"
                    try:
                        num = float(parts[-1])
                        values.append(num)
                    except ValueError:
                        continue # If the last thing isn't a number, skip this line

            if len(values) == 0:
                self.log(f"WARNING: No numbers found in {os.path.basename(file_path)}")
                return None
            
            return np.mean(values) # Return the average for this mouse
            
        except Exception as e:
            self.log(f"ERROR reading file: {e}")
            return None

    def safe_run_analysis(self):
        try:
            self.run_analysis_logic()
        except Exception as e:
            messagebox.showerror("Analysis Error", f"Something went wrong during calculation:\n\n{str(e)}")
            self.log(f"CRASH: {e}")

    def run_analysis_logic(self):
        # 1. Check if we have enough data
        total_mice = sum(len(v) for v in self.group_data.values())
        if total_mice < 3:
            messagebox.showwarning("Not Enough Data", "You need at least 3 mice total to create a graph.")
            return

        group_names = ["Control", "CFA", "Carrageenan"]
        
        # Check for empty groups
        for name in group_names:
            if not self.group_data[name]:
                self.log(f"Warning: Group '{name}' is empty. Proceeding with caution.")

        # 2. Prepare for Stats
        data_list = [self.group_data[n] for n in group_names if len(self.group_data[n]) > 0]
        active_names = [n for n in group_names if len(self.group_data[n]) > 0]

        # We need at least 2 groups with >1 data point to run ANOVA
        can_run_stats = False
        if len(data_list) >= 2:
            if all(len(d) > 1 for d in data_list):
                can_run_stats = True
            else:
                self.log("Skipping Stats: Some groups have only 1 mouse. Cannot calculate variance.")

        # 3. Plotting
        plt.figure(figsize=(9, 7))
        colors = {'Control': 'lightgray', 'CFA': 'firebrick', 'Carrageenan': 'orange'}
        
        # Calculate means/sems
        x_positions = range(len(active_names))
        means = [np.mean(self.group_data[n]) for n in active_names]
        sems = [stats.sem(self.group_data[n]) if len(self.group_data[n]) > 1 else 0 for n in active_names]
        bar_colors = [colors[n] for n in active_names]

        # Draw Bars
        plt.bar(x_positions, means, yerr=sems, tick_label=active_names, capsize=10, 
                color=bar_colors, edgecolor='black', alpha=0.9)

        # Draw Dots (Individual Mice)
        for i, name in enumerate(active_names):
            y = self.group_data[name]
            x = np.random.normal(i, 0.04, size=len(y)) # Jitter
            plt.scatter(x, y, color='black', alpha=0.7, s=50, zorder=3, edgecolors='white')

        # 4. Run Stats (Only if valid)
        if can_run_stats:
            all_values = np.concatenate(data_list)
            all_labels = np.concatenate([[name] * len(self.group_data[name]) for name in active_names])
            
            # Run Tukey
            tukey = pairwise_tukeyhsd(endog=all_values, groups=all_labels, alpha=0.05)
            tukey_df = pd.DataFrame(data=tukey.summary().data[1:], columns=tukey.summary().data[0])
            
            self.log("Statistics calculated successfully.")
            
            # Helper to draw brackets
            y_max = max(all_values)
            curr_y = y_max
            
            def get_pval(g1, g2):
                row = tukey_df[((tukey_df['group1'] == g1) & (tukey_df['group2'] == g2)) | 
                               ((tukey_df['group1'] == g2) & (tukey_df['group2'] == g1))]
                if not row.empty: return row['p-adj'].values[0]
                return 1.0

            # Check comparisons
            import itertools
            for idx1, idx2 in itertools.combinations(range(len(active_names)), 2):
                name1, name2 = active_names[idx1], active_names[idx2]
                p_val = get_pval(name1, name2)
                
                # Draw if Significant
                if p_val < 0.05:
                    h = y_max * 0.05
                    curr_y += h * 2.5
                    plt.plot([idx1, idx1, idx2, idx2], [curr_y-h, curr_y, curr_y, curr_y-h], lw=1.5, c='k')
                    
                    stars = "*" if p_val < 0.05 else "ns"
                    if p_val < 0.01: stars = "**"
                    if p_val < 0.001: stars = "***"
                    
                    plt.text((idx1 + idx2) * 0.5, curr_y, stars, ha='center', va='bottom', fontsize=14, fontweight='bold')

        plt.ylabel('Average Innervation Index', fontsize=12)
        plt.title('Innervation Analysis', fontsize=14)
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    root = tk.Tk()
    app = InnervationApp(root)
    root.mainloop()