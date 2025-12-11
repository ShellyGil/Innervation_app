import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Toplevel
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageEnhance, ImageFilter, ImageOps
import os

# --- Helper Math Functions ---
def calculate_otsu_threshold(image_array):
    pixels = image_array.flatten()
    if pixels.size == 0: return 0
    hist, bin_edges = np.histogram(pixels, bins=256, range=(0, 256))
    hist_norm = hist.astype(float) / pixels.size
    weight_bg = np.cumsum(hist_norm)
    mean_bg = np.cumsum(hist_norm * np.arange(256))
    global_mean = mean_bg[-1]
    valid_mask = (weight_bg > 0) & (weight_bg < 1)
    between_var = np.zeros(256)
    if np.any(valid_mask):
        mean_fg = (global_mean - mean_bg) / (1 - weight_bg)
        mean_bg_safe = mean_bg / weight_bg
        between_var[valid_mask] = weight_bg[valid_mask] * (1 - weight_bg[valid_mask]) * \
                                  (mean_bg_safe[valid_mask] - mean_fg[valid_mask]) ** 2
    return np.argmax(between_var)

def apply_filters_to_image(pil_image, contrast, brightness, noise):
    img = pil_image.copy()
    if noise > 0: 
        img = img.filter(ImageFilter.GaussianBlur(radius=noise))
    if contrast != 1.0: 
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if brightness != 1.0: 
        img = ImageEnhance.Brightness(img).enhance(brightness)
    return img

# --- Adjustment Dialog ---
class AdjustmentDialog:
    def __init__(self, parent, callback):
        self.top = Toplevel(parent)
        self.top.title("Image Adjustments")
        self.top.geometry("300x350")
        self.callback = callback
        self.top.transient(parent)
        
        ttk.Label(self.top, text="Contrast").pack(anchor="w", padx=10, pady=(10,0))
        self.scale_contrast = tk.Scale(self.top, from_=0.5, to=3.0, resolution=0.1, orient="horizontal", command=self.on_change)
        self.scale_contrast.set(parent.adj_contrast)
        self.scale_contrast.pack(fill="x", padx=10)
        
        ttk.Label(self.top, text="Brightness").pack(anchor="w", padx=10, pady=(10,0))
        self.scale_brightness = tk.Scale(self.top, from_=0.5, to=3.0, resolution=0.1, orient="horizontal", command=self.on_change)
        self.scale_brightness.set(parent.adj_brightness)
        self.scale_brightness.pack(fill="x", padx=10)
        
        ttk.Label(self.top, text="Noise Reduction (Blur)").pack(anchor="w", padx=10, pady=(10,0))
        self.scale_noise = tk.Scale(self.top, from_=0.0, to=5.0, resolution=0.2, orient="horizontal", command=self.on_change)
        self.scale_noise.set(parent.adj_noise)
        self.scale_noise.pack(fill="x", padx=10)
        
        ttk.Button(self.top, text="Done", command=self.top.destroy).pack(pady=20)

    def on_change(self, val):
        self.callback(contrast=self.scale_contrast.get(), brightness=self.scale_brightness.get(), noise=float(self.scale_noise.get()))

# --- Main Application ---
class InnervationApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Innervation Index V6.2")
        self.geometry("1200x850")
        
        # --- State ---
        self.files = []
        self.folder_path = ""
        self.current_index = 0
        self.original_raw_image = None
        
        # Image Params
        self.adj_contrast = 1.0
        self.adj_brightness = 1.0
        self.adj_noise = 0.0 
        self.show_red_overlay = tk.BooleanVar(value=False)
        
        # View/Zoom
        self.view_crop_raw = None    
        self.view_offset = (0, 0)
        self.display_scale = 1.0
        self.zoom_start = None
        
        # Modes: "VIEW", "DRAW", "ZOOM_SELECT"
        self.mode = "VIEW" 
        self.drawing_points = []
        self.current_calculated_value = None 
        
        self._setup_ui()
        self.bind("<Control-t>", self.open_adjustments)
        
    def _setup_ui(self):
        control_frame = ttk.Frame(self, padding=15, width=300)
        control_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(control_frame, text="INN V6.2", font=("Helvetica", 16, "bold")).pack(pady=(0, 10))
        ttk.Label(control_frame, text="Workflow:\n1. Load Folder\n2. Adjust\n3. Start Drawing -> Calculate\n4. Save or Discard").pack(anchor="w", pady=5)
        ttk.Separator(control_frame).pack(fill="x", pady=10)
        
        # Options
        ttk.Label(control_frame, text="Crop Mode:").pack(anchor="w")
        self.crop_mode = tk.StringVar(value="Polygon")
        ttk.Combobox(control_frame, textvariable=self.crop_mode, values=["Polygon", "Freehand"], state="readonly").pack(fill="x", pady=5)
        
        ttk.Label(control_frame, text="Threshold Algo:").pack(anchor="w", pady=(10,0))
        self.algo_mode = tk.StringVar(value="1-0 Cut off")
        algo_dd = ttk.Combobox(control_frame, textvariable=self.algo_mode, values=["1-0 Cut off", "Otsu"], state="readonly")
        algo_dd.pack(fill="x", pady=5)
        algo_dd.bind("<<ComboboxSelected>>", self._toggle_cutoff)
        
        self.ent_cutoff = ttk.Entry(control_frame)
        self.ent_cutoff.insert(0, "2500")
        self.ent_cutoff.pack(fill="x", pady=5)
        
        ttk.Checkbutton(control_frame, text="Show Threshold (Red)", variable=self.show_red_overlay, command=self.render_view).pack(anchor="w", pady=10)
        
        ttk.Separator(control_frame).pack(fill="x", pady=10)
        
        # Buttons
        ttk.Button(control_frame, text="📂 Load Folder", command=self.load_folder).pack(fill="x", pady=5)
        
        self.btn_adj = ttk.Button(control_frame, text="🎨 Adjust Image", command=self.open_adjustments, state="disabled")
        self.btn_adj.pack(fill="x", pady=5)
        
        # Zoom Controls Frame
        zoom_frame = ttk.Frame(control_frame)
        zoom_frame.pack(fill="x", pady=5)
        
        self.btn_zoom = ttk.Button(zoom_frame, text="🔍 Zoom In", command=self.activate_zoom_mode, state="disabled")
        self.btn_zoom.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 2))
        
        # CHANGED: New Zoom Out Button
        self.btn_zoom_out = ttk.Button(zoom_frame, text="🔍 Zoom Out", command=self.zoom_out_step, state="disabled")
        self.btn_zoom_out.pack(side=tk.RIGHT, fill="x", expand=True, padx=(2, 0))
        
        self.btn_reset = ttk.Button(control_frame, text="Reset View", command=self.reset_current_view, state="disabled")
        self.btn_reset.pack(fill="x", pady=5)
        
        ttk.Separator(control_frame).pack(fill="x", pady=15)

        self.btn_draw = ttk.Button(control_frame, text="✏️ Start Drawing ROI", command=self.activate_draw_mode, state="disabled")
        self.btn_draw.pack(fill="x", pady=5)

        self.btn_calc = ttk.Button(control_frame, text="Calculate Index", command=self.calculate_only, state="disabled")
        self.btn_calc.pack(fill="x", pady=5)

        self.lbl_result = ttk.Label(control_frame, text="Current: --", font=("Helvetica", 14, "bold"), foreground="blue")
        self.lbl_result.pack(anchor="center", pady=10)

        # Save/Discard Buttons
        btn_row = ttk.Frame(control_frame)
        btn_row.pack(fill="x", pady=10)
        
        self.btn_save = ttk.Button(btn_row, text="💾 Save & Next", command=self.save_and_next, state="disabled")
        self.btn_save.pack(side=tk.LEFT, fill="x", expand=True, padx=(0,2))
        
        self.btn_discard = ttk.Button(btn_row, text="❌ Discard & Next", command=self.discard_and_next, state="disabled")
        self.btn_discard.pack(side=tk.RIGHT, fill="x", expand=True, padx=(2,0))

        # Canvas Area
        self.canvas_frame = ttk.Frame(self)
        self.canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#222222", cursor="arrow")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.finish_polygon)
        self.canvas.bind("<Control-Button-1>", self.finish_polygon)
        
        self.canvas.bind("<Motion>", self.update_crosshair)
        self.canvas.bind("<Leave>", self.hide_crosshair)
        self.canvas.bind("<Enter>", self.show_crosshair)

    def _toggle_cutoff(self, event):
        if self.algo_mode.get() == "Otsu": self.ent_cutoff.config(state="disabled")
        else: self.ent_cutoff.config(state="normal")
        if self.show_red_overlay.get(): self.render_view()

    # --- Custom Cursor Logic ---
    def update_crosshair(self, event):
        if self.mode not in ["DRAW", "ZOOM_SELECT"]:
            self.canvas.config(cursor="arrow")
            self.canvas.delete("cursor")
            return
            
        self.canvas.config(cursor="none")
        self.canvas.delete("cursor")
        x, y = event.x, event.y
        size = 15
        self.canvas.create_line(x-size, y, x+size, y, fill="black", width=3, tags="cursor")
        self.canvas.create_line(x-size, y, x+size, y, fill="cyan", width=1, tags="cursor")
        self.canvas.create_line(x, y-size, x, y+size, fill="black", width=3, tags="cursor")
        self.canvas.create_line(x, y-size, x, y+size, fill="cyan", width=1, tags="cursor")

    def hide_crosshair(self, event):
        self.canvas.delete("cursor")
        self.canvas.config(cursor="arrow")

    def show_crosshair(self, event):
        if self.mode in ["DRAW", "ZOOM_SELECT"]:
            self.canvas.config(cursor="none")

    # --- Standard App Logic ---
    def load_folder(self):
        path = filedialog.askdirectory()
        if not path: return
        self.folder_path = path
        self.files = [f for f in os.listdir(path) if f.lower().endswith(('.tif', '.tiff', '.png', '.jpg'))]
        self.files.sort()
        if not self.files: return
        
        res_path = os.path.join(self.folder_path, "innervation_results.txt")
        if not os.path.exists(res_path):
            with open(res_path, "w") as f:
                f.write(f"{'Filename':<30}\tIndex\n{'-'*40}\n")
                
        self.current_index = 0
        self.load_image_from_disk()

    def load_image_from_disk(self):
        if self.current_index >= len(self.files):
            messagebox.showinfo("Done", "Processing Complete!")
            return
            
        filename = self.files[self.current_index]
        self.title(f"Innervation Index ({self.current_index+1}/{len(self.files)}) - {filename}")
        filepath = os.path.join(self.folder_path, filename)
        
        self.current_calculated_value = None
        self.lbl_result.config(text="Current: --")
        self.mode = "VIEW"
        
        raw = Image.open(filepath).convert("I")
        arr = np.array(raw)
        p2, p98 = np.percentile(arr, (2, 98))
        range_val = p98 - p2 if (p98 - p2) != 0 else 1
        arr_norm = np.clip((arr - p2) / range_val * 255, 0, 255).astype(np.uint8)
        self.original_raw_image = Image.fromarray(arr_norm)
        
        self.reset_current_view()
        
        # Enable buttons
        self.btn_calc.config(state="disabled") 
        self.btn_save.config(state="disabled") 
        self.btn_reset.config(state="normal")
        self.btn_zoom.config(state="normal")
        self.btn_zoom_out.config(state="normal")
        self.btn_adj.config(state="normal")
        self.btn_draw.config(state="normal")
        self.btn_discard.config(state="normal")

    def open_adjustments(self, event=None):
        if self.original_raw_image: AdjustmentDialog(self, self.update_adjustments)

    def update_adjustments(self, contrast, brightness, noise):
        self.adj_contrast = contrast
        self.adj_brightness = brightness
        self.adj_noise = noise
        self.render_view()

    def reset_current_view(self):
        self.view_offset = (0, 0)
        self.view_crop_raw = self.original_raw_image.copy()
        self.render_view()

    def render_view(self):
        if not self.view_crop_raw: return
        self.drawing_points = []
        self.canvas.delete("all") 
        
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10: cw, ch = 800, 600
        
        iw, ih = self.view_crop_raw.size
        scale = min(cw/iw, ch/ih)
        self.display_scale = scale
        new_size = (int(iw * scale), int(ih * scale))
        
        small_raw = self.view_crop_raw.resize(new_size, Image.BILINEAR)
        small_processed = apply_filters_to_image(small_raw, self.adj_contrast, self.adj_brightness, self.adj_noise)
        
        if self.show_red_overlay.get():
            arr = np.array(small_processed)
            if self.algo_mode.get() == "Otsu": thresh = calculate_otsu_threshold(arr)
            else:
                try: thresh = float(self.ent_cutoff.get())
                except: thresh = 255
            
            rgb_img = small_processed.convert("RGB")
            data = np.array(rgb_img)
            mask = arr > thresh
            data[mask] = [255, 0, 0] 
            self.final_display_image = Image.fromarray(data)
        else:
            self.final_display_image = small_processed

        self.tk_image = ImageTk.PhotoImage(self.final_display_image)
        self.canvas_offset_x = (cw - new_size[0]) // 2
        self.canvas_offset_y = (ch - new_size[1]) // 2
        self.canvas.create_image(cw//2, ch//2, image=self.tk_image, anchor="center", tags="img")

    def activate_zoom_mode(self):
        self.mode = "ZOOM_SELECT"
        self.canvas.config(cursor="none")

    # --- NEW FUNCTION: Zoom Out Step ---
    def zoom_out_step(self):
        if not self.view_crop_raw or not self.original_raw_image:
            return
            
        current_w, current_h = self.view_crop_raw.size
        orig_w, orig_h = self.original_raw_image.size
        
        # Don't zoom out if already full size
        if current_w >= orig_w and current_h >= orig_h:
            return

        # Expansion factor (1.5x)
        factor = 1.5
        new_w = int(current_w * factor)
        new_h = int(current_h * factor)
        
        # Calculate new top-left based on center preservation
        center_x = self.view_offset[0] + current_w // 2
        center_y = self.view_offset[1] + current_h // 2
        
        new_x = center_x - new_w // 2
        new_y = center_y - new_h // 2
        
        # Clamp to image boundaries
        x1 = max(0, int(new_x))
        y1 = max(0, int(new_y))
        x2 = min(orig_w, int(new_x + new_w))
        y2 = min(orig_h, int(new_y + new_h))
        
        # Update view offset and crop
        self.view_offset = (x1, y1)
        self.view_crop_raw = self.original_raw_image.crop((x1, y1, x2, y2))
        
        self.mode = "VIEW"
        self.render_view()

    def activate_draw_mode(self):
        self.mode = "DRAW"
        self.drawing_points = []
        self.render_view() 
        self.canvas.config(cursor="none")

    def apply_zoom(self, start, end):
        x1 = (start[0] - self.canvas_offset_x) / self.display_scale
        y1 = (start[1] - self.canvas_offset_y) / self.display_scale
        x2 = (end[0] - self.canvas_offset_x) / self.display_scale
        y2 = (end[1] - self.canvas_offset_y) / self.display_scale
        w, h = self.view_crop_raw.size
        x1, x2 = sorted([max(0, min(w, x)) for x in [x1, x2]])
        y1, y2 = sorted([max(0, min(h, y)) for y in [y1, y2]])
        
        if (x2 - x1) < 10 or (y2 - y1) < 10:
            self.mode = "VIEW"
            return
            
        self.view_offset = (self.view_offset[0] + x1, self.view_offset[1] + y1)
        self.view_crop_raw = self.view_crop_raw.crop((x1, y1, x2, y2))
        self.render_view()
        self.mode = "VIEW" 

    # --- Mouse Events ---
    def on_click(self, event):
        x, y = event.x, event.y
        if self.mode == "ZOOM_SELECT":
            self.zoom_start = (x, y)
        elif self.mode == "DRAW":
            self.drawing_points.append((x, y))
            r = 3
            self.canvas.create_oval(x-r, y-r, x+r, y+r, fill="red", outline="red", tags="overlay")
            if self.crop_mode.get() == "Polygon" and len(self.drawing_points) > 1:
                x0, y0 = self.drawing_points[-2]
                self.canvas.create_line(x0, y0, x, y, fill="yellow", width=2, tags="overlay")
            self.btn_calc.config(state="normal")
    
    def on_drag(self, event):
        self.update_crosshair(event)
        x, y = event.x, event.y
        if self.mode == "ZOOM_SELECT" and self.zoom_start:
            self.canvas.delete("zoom_box")
            x0, y0 = self.zoom_start
            self.canvas.create_rectangle(x0, y0, x, y, outline="cyan", width=2, dash=(4, 4), tags="zoom_box")
        elif self.mode == "DRAW" and self.crop_mode.get() == "Freehand":
            self.drawing_points.append((x, y))
            if len(self.drawing_points) > 1:
                x0, y0 = self.drawing_points[-2]
                self.canvas.create_line(x0, y0, x, y, fill="yellow", width=2, tags="overlay")

    def on_release(self, event):
        if self.mode == "ZOOM_SELECT" and self.zoom_start:
            self.apply_zoom(self.zoom_start, (event.x, event.y))
            self.zoom_start = None
        elif self.mode == "DRAW" and self.crop_mode.get() == "Freehand":
            self.finish_polygon(None)

    def finish_polygon(self, event):
        if self.mode != "DRAW" or len(self.drawing_points) < 3: return
        x0, y0 = self.drawing_points[-1]
        x1, y1 = self.drawing_points[0]
        self.canvas.create_line(x0, y0, x1, y1, fill="yellow", width=2, tags="overlay")
        self.canvas.create_polygon(self.drawing_points, outline="yellow", fill="", tags="overlay")
        self.btn_calc.config(state="normal")

    # --- Calculations & File IO ---
    def calculate_only(self):
        if not self.drawing_points:
            messagebox.showwarning("Error", "Please draw an area first!")
            return
            
        real_points = []
        for (cx, cy) in self.drawing_points:
            view_x = (cx - self.canvas_offset_x) / self.display_scale
            view_y = (cy - self.canvas_offset_y) / self.display_scale
            real_points.append((view_x + self.view_offset[0], view_y + self.view_offset[1]))
        
        poly_arr = np.array(real_points)
        min_x = max(0, int(np.min(poly_arr[:, 0])))
        max_x = int(np.max(poly_arr[:, 0]))
        min_y = max(0, int(np.min(poly_arr[:, 1])))
        max_y = int(np.max(poly_arr[:, 1]))
        
        roi_crop = self.original_raw_image.crop((min_x, min_y, max_x, max_y))
        roi_processed = apply_filters_to_image(roi_crop, self.adj_contrast, self.adj_brightness, self.adj_noise)
        
        crop_points = []
        for (rx, ry) in real_points: crop_points.append((rx - min_x, ry - min_y))
        mask_img = Image.new('1', (roi_crop.width, roi_crop.height), 0)
        ImageDraw.Draw(mask_img).polygon(crop_points, outline=1, fill=1)
        mask = np.array(mask_img)
        
        img_data = np.array(roi_processed)
        roi_pixels = img_data[mask]
        valid_pixels = roi_pixels[roi_pixels > 0]
        
        if valid_pixels.size == 0: result = 0.0
        else:
            if self.algo_mode.get() == "Otsu": thresh = calculate_otsu_threshold(valid_pixels)
            else:
                try: thresh = float(self.ent_cutoff.get())
                except: thresh = 128
            count_above = np.sum(valid_pixels > thresh)
            result = 100 * (count_above / valid_pixels.size)
        
        self.current_calculated_value = result
        self.lbl_result.config(text=f"Index: {result:.4f}%")
        self.btn_save.config(state="normal")

    def save_and_next(self):
        if self.current_calculated_value is None: return
        with open(os.path.join(self.folder_path, "innervation_results.txt"), "a") as f:
            f.write(f"{self.files[self.current_index]:<30}\t{self.current_calculated_value:.6f}\n")
        self.current_index += 1
        self.load_image_from_disk()

    def discard_and_next(self):
        self.current_index += 1
        self.load_image_from_disk()

if __name__ == "__main__":
    app = InnervationApp()
    app.mainloop()
