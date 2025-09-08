import os
import sys
from typing import List, Tuple, Optional
from PIL import Image, ImageOps, ImageColor, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

# 嘗試載入拖曳模組；若失敗則退化為僅支援按鈕選檔
DND_AVAILABLE = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False

# -------- 影像工具 --------
VALID_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}

def is_image_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in VALID_EXTS

def open_image_safe(path: str) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # 修正 EXIF 方向
    return img

def parse_color(value: str) -> Tuple[int, int, int, int]:
    """將顏色字串轉 RGBA；失敗預設白色。"""
    try:
        return ImageColor.getcolor(value, "RGBA")
    except Exception:
        return (255, 255, 255, 255)

def stitch_images(
    paths: List[str],
    orientation: str = "vertical",   # 'vertical' 或 'horizontal'
    scale_to_align_edge: bool = True,
    spacing: int = 0,
    bg_color: str = "#FFFFFF",
    target_edge_mode: str = "max",   # 'max' 或 'min'
) -> Image.Image:
    """依參數合併多張圖片，回傳 PIL Image。"""
    if not paths:
        raise ValueError("沒有選擇任何圖片。")

    images = [open_image_safe(p) for p in paths]
    sizes = [img.size for img in images]  # (w, h)
    widths = [w for (w, h) in sizes]
    heights = [h for (w, h) in sizes]

    if orientation not in ("vertical", "horizontal"):
        raise ValueError("orientation 必須為 'vertical' 或 'horizontal'。")

    # 對齊邊：直向對齊寬；橫向對齊高
    if scale_to_align_edge:
        if orientation == "vertical":
            edge = max(widths) if target_edge_mode == "max" else min(widths)
            resized = []
            for img in images:
                w, h = img.size
                if w == edge:
                    resized.append(img)
                else:
                    r = edge / w
                    resized.append(img.resize((edge, max(1, int(round(h * r)))), Image.LANCZOS))
            images = resized
        else:  # horizontal
            edge = max(heights) if target_edge_mode == "max" else min(heights)
            resized = []
            for img in images:
                w, h = img.size
                if h == edge:
                    resized.append(img)
                else:
                    r = edge / h
                    resized.append(img.resize((max(1, int(round(w * r))), edge), Image.LANCZOS))
            images = resized

    # 重新計尺寸
    sizes = [im.size for im in images]
    widths = [w for (w, h) in sizes]
    heights = [h for (w, h) in sizes]

    bg_rgba = parse_color(bg_color)
    mode = "RGBA" if bg_rgba[3] < 255 else "RGB"
    bg = bg_rgba if mode == "RGBA" else bg_rgba[:3]

    if orientation == "vertical":
        canvas_w = max(widths)
        total_h = sum(heights) + spacing * (len(images) - 1 if len(images) > 1 else 0)
        out = Image.new(mode, (canvas_w, total_h), bg)
        y = 0
        for img in images:
            w, h = img.size
            x = 0  # 想置中可改：x = (canvas_w - w) // 2
            out.paste(img.convert(mode), (x, y))
            y += h + spacing
        return out
    else:
        total_w = sum(widths) + spacing * (len(images) - 1 if len(images) > 1 else 0)
        canvas_h = max(heights)
        out = Image.new(mode, (total_w, canvas_h), bg)
        x = 0
        for img in images:
            w, h = img.size
            y = 0  # 想置中可改：y = (canvas_h - h) // 2
            out.paste(img.convert(mode), (x, y))
            x += w + spacing
        return out

# -------- GUI --------
class ImageStitcherApp:
    def __init__(self):
        # 根視窗
        if DND_AVAILABLE:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()
        self.root.title("圖片拼接工具（上下 / 左右）— 即時預覽可顯示/隱藏")
        self.paths: List[str] = []

        # 即時預覽狀態
        self.live_preview_enabled = tk.BooleanVar(value=True)
        self.preview_img_full: Optional[Image.Image] = None
        self.preview_img_tk: Optional[ImageTk.PhotoImage] = None
        self.preview_scale = tk.DoubleVar(value=0.5)  # 初始顯示比例
        self._preview_job = None  # debounce 排程

        # ----- 外層容器 -----
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        # 常駐工具列：放置「即時預覽」勾選（永遠可見）
        toolbar = ttk.Frame(main)
        toolbar.pack(fill="x", pady=(0, 6))
        ttk.Checkbutton(
            toolbar,
            text="即時預覽",
            variable=self.live_preview_enabled,
            command=self.toggle_live_preview
        ).pack(side="left")

        # ----- 三欄版面 -----
        # 左欄：清單與操作
        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=False)
        self.left_panel = left  # 供動態調整 pack

        ttk.Label(left, text="圖片清單（可拖曳）" if DND_AVAILABLE else "圖片清單").pack(anchor="w")

        self.listbox = tk.Listbox(left, selectmode=tk.EXTENDED, height=22, width=44)
        self.listbox.pack(fill="both", expand=True)

        if DND_AVAILABLE:
            self.listbox.drop_target_register(DND_FILES)
            self.listbox.dnd_bind("<<Drop>>", self.on_drop)

        lbtns = ttk.Frame(left)
        lbtns.pack(fill="x", pady=(6, 0))
        ttk.Button(lbtns, text="新增圖片…", command=self.add_files).pack(side="left")
        ttk.Button(lbtns, text="移除選取", command=self.remove_selected).pack(side="left", padx=6)
        ttk.Button(lbtns, text="全部清空", command=self.clear_all).pack(side="left", padx=0)

        order = ttk.Frame(left)
        order.pack(fill="x", pady=(6, 0))
        ttk.Button(order, text="↑ 上移", command=lambda: self.move_selection(-1)).pack(side="left")
        ttk.Button(order, text="↓ 下移", command=lambda: self.move_selection(1)).pack(side="left", padx=6)

        # 中欄：即時預覽（可被隱藏/顯示）
        mid = ttk.Frame(main)
        self.mid_panel = mid  # 保存以便 pack/forget
        mid.pack(side="left", fill="both", expand=True, padx=(10, 10))

        head = ttk.Frame(mid)
        head.pack(fill="x")
        ttk.Label(head, text="即時預覽").pack(side="left")
        # 勾選已移到頂部 toolbar

        # 預覽控制列
        ctrl = ttk.Frame(mid)
        ctrl.pack(fill="x", pady=(4, 4))
        ttk.Label(ctrl, text="縮放").pack(side="left")
        scale = ttk.Scale(ctrl, from_=0.05, to=2.0, variable=self.preview_scale,
                          command=lambda _=None: self.render_preview_scaled())
        scale.pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(ctrl, text="適應寬度", command=self.fit_preview_width).pack(side="left")
        self.size_label = ttk.Label(ctrl, text="", width=20)
        self.size_label.pack(side="right")

        # 預覽畫布 + 捲軸
        canvas_wrap = ttk.Frame(mid)
        canvas_wrap.pack(fill="both", expand=True)

        self.vbar = ttk.Scrollbar(canvas_wrap, orient="vertical")
        self.hbar = ttk.Scrollbar(canvas_wrap, orient="horizontal")
        self.preview_canvas = tk.Canvas(
            canvas_wrap, bg="#111",
            xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set,
            highlightthickness=0
        )
        self.vbar.config(command=self.preview_canvas.yview)
        self.hbar.config(command=self.preview_canvas.xview)

        self.preview_canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar.grid(row=1, column=0, sticky="ew")
        canvas_wrap.rowconfigure(0, weight=1)
        canvas_wrap.columnconfigure(0, weight=1)

        # 右欄：設定與輸出
        right = ttk.Frame(main)
        self.right_panel = right  # 供 before=... 以及動態調整
        right.pack(side="left", fill="y", expand=False, padx=(0, 0))

        # 參數變數
        self.var_orient = tk.StringVar(value="vertical")  # 'vertical' or 'horizontal'
        self.var_scale = tk.BooleanVar(value=True)
        self.var_spacing = tk.IntVar(value=0)
        self.var_bg = tk.StringVar(value="#FFFFFF")
        self.var_target_mode = tk.StringVar(value="max")  # 'max' or 'min'

        # 輸出模式相關
        self.var_output_mode = tk.StringVar(value="single")  # 'single' or 'direct'
        self.var_out_dir = tk.StringVar(value="")
        self.var_direct_ext = tk.StringVar(value="png")      # 'png'/'jpg'/'webp'
        self.var_direct_index = tk.IntVar(value=1)

        # 自動 reset
        self.var_auto_reset = tk.BooleanVar(value=False)

        # ---- 設定項 ----
        box_cfg = ttk.LabelFrame(right, text="拼接設定")
        box_cfg.pack(fill="x")

        row_orient = ttk.Frame(box_cfg); row_orient.pack(fill="x", pady=(4, 0))
        ttk.Label(row_orient, text="拼接方向：").pack(side="left")
        ttk.Radiobutton(row_orient, text="上下（直向）", value="vertical", variable=self.var_orient,
                        command=self.schedule_preview_update).pack(side="left")
        ttk.Radiobutton(row_orient, text="左右（橫向）", value="horizontal", variable=self.var_orient,
                        command=self.schedule_preview_update).pack(side="left", padx=6)

        ttk.Checkbutton(
            box_cfg,
            text="等比例對齊邊（直向=同寬、橫向=同高）",
            variable=self.var_scale,
            command=self.schedule_preview_update
        ).pack(anchor="w", pady=(6, 0))

        row1 = ttk.Frame(box_cfg); row1.pack(fill="x", pady=(6, 0))
        ttk.Label(row1, text="對齊基準：").pack(side="left")
        ttk.Radiobutton(row1, text="取最大", value="max", variable=self.var_target_mode,
                        command=self.schedule_preview_update).pack(side="left")
        ttk.Radiobutton(row1, text="取最小", value="min", variable=self.var_target_mode,
                        command=self.schedule_preview_update).pack(side="left")

        row2 = ttk.Frame(box_cfg); row2.pack(fill="x", pady=(6, 0))
        ttk.Label(row2, text="間距(px)：").pack(side="left")
        e = ttk.Entry(row2, textvariable=self.var_spacing, width=8)
        e.pack(side="left")
        e.bind("<KeyRelease>", lambda _e: self.schedule_preview_update())

        row3 = ttk.Frame(box_cfg); row3.pack(fill="x", pady=(6, 4))
        ttk.Label(row3, text="背景色：").pack(side="left")
        self.bg_entry = ttk.Entry(row3, textvariable=self.var_bg, width=12)
        self.bg_entry.pack(side="left")
        ttk.Button(row3, text="選色…", command=self.pick_color).pack(side="left", padx=6)

        ttk.Separator(right, orient="horizontal").pack(fill="x", pady=8)

        # ---- 輸出模式 ----
        mode_box = ttk.LabelFrame(right, text="輸出模式")
        mode_box.pack(fill="x", pady=(0, 8))

        row_mode = ttk.Frame(mode_box); row_mode.pack(fill="x", pady=(6, 0))
        ttk.Radiobutton(row_mode, text="單次輸出（跳出存檔視窗）", value="single", variable=self.var_output_mode).pack(anchor="w")
        ttk.Radiobutton(row_mode, text="直接輸出（固定資料夾與檔名遞增）", value="direct", variable=self.var_output_mode,
                        command=self.update_direct_widgets_state).pack(anchor="w")

        direct_box = ttk.Frame(mode_box); direct_box.pack(fill="x", pady=(6, 6))
        self.direct_box = direct_box

        row_dir = ttk.Frame(direct_box); row_dir.pack(fill="x", pady=(2, 0))
        ttk.Label(row_dir, text="輸出資料夾：").pack(side="left")
        self.dir_label = ttk.Label(row_dir, textvariable=self.var_out_dir, width=24, relief="sunken", anchor="w")
        self.dir_label.pack(side="left", padx=(4, 4))
        ttk.Button(row_dir, text="選擇…", command=self.choose_output_dir).pack(side="left")

        row_de = ttk.Frame(direct_box); row_de.pack(fill="x", pady=(4, 0))
        ttk.Label(row_de, text="副檔名：").pack(side="left")
        ttk.Combobox(row_de, textvariable=self.var_direct_ext, values=("png", "jpg", "webp"),
                     width=6, state="readonly").pack(side="left", padx=(2, 12))
        ttk.Label(row_de, text="下一個編號：").pack(side="left")
        self.index_entry = ttk.Entry(row_de, textvariable=self.var_direct_index, width=6)
        self.index_entry.pack(side="left")

        ttk.Checkbutton(mode_box, text="自動 reset（輸出後清空清單並編號重置為 1）",
                        variable=self.var_auto_reset).pack(anchor="w", pady=(2, 2))

        # 狀態/進度/按鈕
        self.status_var = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.status_var, foreground="#2a7").pack(fill="x")

        self.progress = ttk.Progressbar(right, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(4, 0))
        ttk.Button(right, text="開始拼接並輸出", command=self.run_stitch).pack(fill="x", pady=(8, 0))

        # 美化
        try:
            style = ttk.Style()
            if sys.platform != "win32":
                style.theme_use("clam")
        except Exception:
            pass

        self.root.minsize(1080, 640)
        self.update_direct_widgets_state()

        # 初始安排一次預覽 + 整理版面
        self.schedule_preview_update()
        self.toggle_live_preview()  # 依 live_preview_enabled 初始值整理一次布局

        # 視窗尺寸變更時可適配寬度
        self.preview_canvas.bind("<Configure>", lambda _e: self.fit_preview_width_once())

        # 滑鼠滾輪捲動
        def _on_mousewheel(event):
            if sys.platform == "darwin":
                delta = -1 * int(event.delta)
            else:
                delta = -1 * int(event.delta / 120)
            self.preview_canvas.yview_scroll(delta, "units")
        self.preview_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.preview_canvas.bind_all("<Button-4>", lambda e: self.preview_canvas.yview_scroll(-1, "units"))
        self.preview_canvas.bind_all("<Button-5>", lambda e: self.preview_canvas.yview_scroll(1, "units"))

    # ----- 顯示/隱藏即時預覽（修正版） -----
    def toggle_live_preview(self):
        show = self.live_preview_enabled.get()
        if show:
            # 把中欄插回左/右中間
            self.mid_panel.pack(
                side="left", fill="both", expand=True, padx=(10, 10),
                before=self.right_panel
            )
            # 還原左右欄配置：左欄不吃滿、右欄固定寬
            self.left_panel.pack_configure(side="left", fill="both", expand=False)
            self.right_panel.pack_configure(side="left", fill="y", expand=False)
            # 立刻重建預覽
            self.schedule_preview_update()
        else:
            # 停止排程、清空畫布
            if self._preview_job:
                self.root.after_cancel(self._preview_job)
                self._preview_job = None
            self.preview_img_full = None
            self.preview_img_tk = None
            self._draw_preview(None)
            self.size_label.config(text="")
            # 隱藏中欄
            self.mid_panel.pack_forget()
            # 讓左欄吃掉剩餘空間，避免留白
            self.left_panel.pack_configure(side="left", fill="both", expand=True)
            # 右欄維持縱向（如需兩欄都撐滿，可改為 fill="both", expand=True）
            self.right_panel.pack_configure(side="left", fill="y", expand=False)

    # ----- 清單 & 檔案 -----
    def on_drop(self, event):
        raw = event.data
        paths = self._split_drop_paths(raw)
        self._add_paths(paths)

    @staticmethod
    def _split_drop_paths(data: str) -> List[str]:
        result = []
        token = ""
        in_brace = False
        for ch in data:
            if ch == "{":
                in_brace = True
                if token.strip():
                    result.append(token.strip()); token = ""
            elif ch == "}":
                in_brace = False
                if token:
                    result.append(token); token = ""
            elif ch == " " and not in_brace:
                if token.strip():
                    result.append(token.strip()); token = ""
            else:
                token += ch
        if token.strip():
            result.append(token.strip())
        clean = []
        for p in result:
            if os.path.isdir(p):
                for root, _, files in os.walk(p):
                    for f in files:
                        fp = os.path.join(root, f)
                        if is_image_file(fp):
                            clean.append(fp)
            else:
                if is_image_file(p):
                    clean.append(p)
        return clean

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="選擇圖片",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tif *.tiff"),
                       ("All files", "*.*")],
        )
        if not paths: return
        self._add_paths(paths)

    def _add_paths(self, paths: List[str]):
        new_paths = [p for p in paths if is_image_file(p)]
        if not new_paths:
            messagebox.showwarning("沒有可用的圖片", "未偵測到支援的圖片格式。"); return
        self.paths.extend(new_paths)
        for p in new_paths:
            self.listbox.insert(tk.END, p)
        self.schedule_preview_update()

    def remove_selected(self):
        sel = list(self.listbox.curselection())
        if not sel: return
        for idx in reversed(sel):
            self.listbox.delete(idx)
            del self.paths[idx]
        self.schedule_preview_update()

    def clear_all(self):
        self.listbox.delete(0, tk.END)
        self.paths.clear()
        self.schedule_preview_update()

    def move_selection(self, direction: int):
        sel = list(self.listbox.curselection())
        if not sel: return
        if direction < 0:
            for i in sel:
                if i == 0: continue
                self._swap_items(i, i - 1)
            self.listbox.selection_clear(0, tk.END)
            for i in [max(0, s - 1) for s in sel]:
                self.listbox.selection_set(i)
        else:
            for i in reversed(sel):
                if i == self.listbox.size() - 1: continue
                self._swap_items(i, i + 1)
            self.listbox.selection_clear(0, tk.END)
            for i in [min(self.listbox.size() - 1, s + 1) for s in sel]:
                self.listbox.selection_set(i)
        self.schedule_preview_update()

    def _swap_items(self, i, j):
        vi = self.listbox.get(i); vj = self.listbox.get(j)
        self.listbox.delete(i); self.listbox.insert(i, vj)
        self.listbox.delete(j); self.listbox.insert(j, vi)
        self.paths[i], self.paths[j] = self.paths[j], self.paths[i]

    # ----- 設定 & 輸出 -----
    def pick_color(self):
        color = colorchooser.askcolor(title="選擇背景色", initialcolor=self.var_bg.get())
        if color and color[1]:
            self.var_bg.set(color[1]); self.schedule_preview_update()

    def update_direct_widgets_state(self):
        direct = (self.var_output_mode.get() == "direct")
        for child in self.direct_box.winfo_children():
            try: child.configure(state=("normal" if direct else "disabled"))
            except tk.TclError: pass

    def choose_output_dir(self):
        path = filedialog.askdirectory(title="選擇輸出資料夾")
        if path: self.var_out_dir.set(path)

    # ----- 即時預覽 -----
    def schedule_preview_update(self):
        if not self.live_preview_enabled.get():
            return
        if self._preview_job:
            self.root.after_cancel(self._preview_job)
        # 300ms 防抖：避免每個小變化都重算
        self._preview_job = self.root.after(300, self.render_preview_full)

    def render_preview_full(self):
        self._preview_job = None
        if not self.paths or not self.live_preview_enabled.get():
            self.preview_img_full = None
            self._draw_preview(None); self.size_label.config(text="")
            return
        try:
            spacing = int(self.var_spacing.get())
            if spacing < 0: raise ValueError
        except Exception:
            # 間距不合法時先不更新
            return
        try:
            img = stitch_images(
                self.paths,
                orientation=self.var_orient.get(),
                scale_to_align_edge=self.var_scale.get(),
                spacing=spacing,
                bg_color=self.var_bg.get(),
                target_edge_mode=self.var_target_mode.get(),
            )
            self.preview_img_full = img
            # 初次或清單更動時，讓它自動適應寬度
            self.fit_preview_width()
            self.render_preview_scaled()
        except Exception:
            self.preview_img_full = None
            self._draw_preview(None)
            self.size_label.config(text=f"預覽失敗")

    def render_preview_scaled(self):
        if self.preview_img_full is None or not self.live_preview_enabled.get():
            return
        W, H = self.preview_img_full.size
        scale = max(0.05, min(3.0, float(self.preview_scale.get())))
        sw = max(1, int(W * scale))
        sh = max(1, int(H * scale))
        disp = self.preview_img_full.resize((sw, sh), Image.LANCZOS)
        self.preview_img_tk = ImageTk.PhotoImage(disp)
        self._draw_preview(self.preview_img_tk)
        self.preview_canvas.config(scrollregion=(0, 0, sw, sh))
        self.size_label.config(text=f"{W}×{H} @ {int(scale*100)}%")

    def _draw_preview(self, tk_img: Optional[ImageTk.PhotoImage]):
        self.preview_canvas.delete("all")
        if tk_img is None:
            return
        self.preview_canvas.create_image(0, 0, anchor="nw", image=tk_img)

    def fit_preview_width_once(self):
        if self.preview_img_full is None or not self.live_preview_enabled.get():
            return
        self.fit_preview_width()

    def fit_preview_width(self):
        if self.preview_img_full is None or not self.live_preview_enabled.get():
            return
        self.root.update_idletasks()
        canvas_w = max(1, self.preview_canvas.winfo_width())
        img_w = max(1, self.preview_img_full.size[0])
        scale = min(3.0, max(0.05, (canvas_w * 0.98) / img_w))
        self.preview_scale.set(scale)

    # ----- 輸出 -----
    def run_stitch(self):
        if not self.paths:
            messagebox.showwarning("沒有圖片", "請先加入至少一張圖片。"); return

        # 讀取設定
        try:
            spacing = int(self.var_spacing.get())
            if spacing < 0: raise ValueError
        except Exception:
            messagebox.showerror("參數錯誤", "間距必須為 0 或正整數。"); return

        self._set_progress(5); self.root.update_idletasks()

        try:
            img = stitch_images(
                self.paths,
                orientation=self.var_orient.get(),
                scale_to_align_edge=self.var_scale.get(),
                spacing=spacing,
                bg_color=self.var_bg.get(),
                target_edge_mode=self.var_target_mode.get(),
            )
        except Exception as e:
            self._set_progress(0)
            messagebox.showerror("發生錯誤", f"拼接失敗：\n{e}")
            return

        self._set_progress(60)
        mode = self.var_output_mode.get()
        success_path = None

        if mode == "single":
            save_path = filedialog.asksaveasfilename(
                title="另存輸出圖片",
                defaultextension=".png",
                filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg;*.jpeg"), ("WebP", "*.webp"), ("All files", "*.*")],
                initialfile="stitched.png",
            )
            if not save_path:
                self._set_progress(0); return
            try:
                self._save_image(img, save_path)
                success_path = save_path
                self._set_progress(100)
                messagebox.showinfo("完成", f"已輸出：\n{save_path}")
            except Exception as e:
                messagebox.showerror("發生錯誤", f"存檔失敗：\n{e}")
            finally:
                self._set_progress(0)
        else:
            out_dir = self.var_out_dir.get().strip()
            if not out_dir:
                self._set_progress(0)
                messagebox.showwarning("未設定資料夾", "請先在『直接輸出』中選擇輸出資料夾。"); return
            if not os.path.isdir(out_dir):
                self._set_progress(0)
                messagebox.showerror("資料夾不存在", f"找不到資料夾：\n{out_dir}"); return
            try:
                idx = int(self.var_direct_index.get())
                if idx < 1: raise ValueError
            except Exception:
                self._set_progress(0)
                messagebox.showerror("參數錯誤", "『下一個編號』需為 >= 1 的整數。"); return
            ext = self.var_direct_ext.get().lower()
            if ext not in ("png", "jpg", "webp"): ext = "png"

            save_path = os.path.join(out_dir, f"{idx}.{ext}")
            while os.path.exists(save_path):
                idx += 1
                save_path = os.path.join(out_dir, f"{idx}.{ext}")
            try:
                self._save_image(img, save_path)
                success_path = save_path
                self.var_direct_index.set(idx + 1)
                self._set_progress(100)
                self.status_var.set(f"輸出成功：{save_path}")
            except Exception as e:
                self.status_var.set("")
                messagebox.showerror("發生錯誤", f"存檔失敗：\n{e}")
            finally:
                self._set_progress(0)

        # 自動 reset
        if success_path and self.var_auto_reset.get():
            self.clear_all()
            self.var_direct_index.set(1)

    def _save_image(self, img: Image.Image, save_path: str):
        ext = os.path.splitext(save_path)[1].lower()
        kwargs = {}
        if ext in (".jpg", ".jpeg"):
            kwargs["quality"] = 95
            if img.mode != "RGB":
                img = img.convert("RGB")
        img.save(save_path, **kwargs)

    def _set_progress(self, val: int):
        self.progress["value"] = max(0, min(100, val))

def main():
    app = ImageStitcherApp()
    app.root.mainloop()

if __name__ == "__main__":
    main()
