"""
番茄钟 (Pomodoro Timer) — 桌面应用程序
基于番茄工作法：工作 25 分钟 → 休息 5 分钟，每 4 轮后长休息 15 分钟
"""

import tkinter as tk
from tkinter import ttk
import winsound
import threading
import math
import time

# ── 常量 ──────────────────────────────────────────────
WORK_MIN = 25
SHORT_BREAK_MIN = 5
LONG_BREAK_MIN = 15
TOMATO_RED = "#E74C3C"
TOMATO_LIGHT = "#FADBD8"
BG_COLOR = "#FFF5F0"
TEXT_DARK = "#2C3E50"
TEXT_LIGHT = "#7F8C8D"
BTN_START = "#27AE60"
BTN_PAUSE = "#F39C12"
BTN_RESET = "#95A5A6"

FONT_TIMER = ("Segoe UI", 72, "bold")
FONT_LABEL = ("Segoe UI", 18, "bold")
FONT_BTN = ("Segoe UI", 13, "bold")
FONT_COUNTER = ("Segoe UI", 11)

# ── 主窗口 ──────────────────────────────────────────────
class PomodoroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🍅 番茄钟")
        self.root.geometry("480x620")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_COLOR)

        # 窗口居中
        self.center_window()

        # 状态变量
        self.running = False
        self.paused = False
        self.remaining_seconds = WORK_MIN * 60
        self.current_mode = "work"          # work / short_break / long_break
        self.sessions_completed = 0         # 已完成的工作轮数
        self.after_id = None

        # 构建 UI
        self.build_ui()

        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ── 窗口居中 ──────────────────────────────────────
    def center_window(self):
        w, h = 480, 620
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ── 构建界面 ──────────────────────────────────────
    def build_ui(self):
        # ---- 标题 ----
        title_frame = tk.Frame(self.root, bg=BG_COLOR)
        title_frame.pack(pady=(30, 5))
        tk.Label(
            title_frame, text="🍅 番茄钟", font=("Segoe UI", 22, "bold"),
            fg=TOMATO_RED, bg=BG_COLOR
        ).pack()

        # ---- 环形计时器画布 ----
        self.canvas_size = 300
        self.canvas = tk.Canvas(
            self.root, width=self.canvas_size, height=self.canvas_size,
            bg=BG_COLOR, highlightthickness=0
        )
        self.canvas.pack(pady=5)
        self.draw_timer_face(1.0)  # 满圆环

        # ---- 计时数字（叠加在画布上方） ----
        self.time_label = tk.Label(
            self.root, text=self.format_time(self.remaining_seconds),
            font=FONT_TIMER, fg=TEXT_DARK, bg=BG_COLOR
        )
        # 用 place 定位在画布上方
        self.time_label.place(relx=0.5, rely=0.406, anchor="center")

        # ---- 模式标签 ----
        self.mode_label = tk.Label(
            self.root, text="🔴 专注工作", font=FONT_LABEL,
            fg=TOMATO_RED, bg=BG_COLOR
        )
        self.mode_label.pack(pady=(5, 10))

        # ---- 按钮区域 ----
        btn_frame = tk.Frame(self.root, bg=BG_COLOR)
        btn_frame.pack(pady=5)

        self.start_btn = tk.Button(
            btn_frame, text="▶  开始", font=FONT_BTN,
            bg=BTN_START, fg="white", activebackground="#219A52",
            relief="flat", padx=28, pady=10, cursor="hand2",
            command=self.toggle_start_pause
        )
        self.start_btn.grid(row=0, column=0, padx=8)

        self.reset_btn = tk.Button(
            btn_frame, text="↺  重置", font=FONT_BTN,
            bg=BTN_RESET, fg="white", activebackground="#7F8C8D",
            relief="flat", padx=28, pady=10, cursor="hand2",
            command=self.reset
        )
        self.reset_btn.grid(row=0, column=1, padx=8)

        self.skip_btn = tk.Button(
            btn_frame, text="⏭  跳过", font=FONT_BTN,
            bg="#8E44AD", fg="white", activebackground="#7D3C98",
            relief="flat", padx=28, pady=10, cursor="hand2",
            command=self.skip
        )
        self.skip_btn.grid(row=0, column=2, padx=8)

        # ---- 模式切换 ----
        mode_frame = tk.Frame(self.root, bg=BG_COLOR)
        mode_frame.pack(pady=15)
        tk.Label(mode_frame, text="切换模式：", font=FONT_COUNTER,
                 fg=TEXT_LIGHT, bg=BG_COLOR).pack(side="left", padx=(0, 10))

        for text, mode in [("🍅 工作", "work"),
                           ("☕ 短休", "short_break"),
                           ("😴 长休", "long_break")]:
            btn = tk.Button(
                mode_frame, text=text, font=("Segoe UI", 11),
                relief="flat", padx=10, pady=5, cursor="hand2",
                command=lambda m=mode: self.switch_mode(m)
            )
            btn.pack(side="left", padx=4)

        # ---- 进度圆点 ----
        dot_frame = tk.Frame(self.root, bg=BG_COLOR)
        dot_frame.pack(pady=12)
        tk.Label(dot_frame, text="已完成：", font=FONT_COUNTER,
                 fg=TEXT_LIGHT, bg=BG_COLOR).pack(side="left", padx=(0, 6))
        self.dot_labels = []
        for i in range(8):
            dot = tk.Label(dot_frame, text="○", font=("Segoe UI", 14),
                           fg="#BDC3C7", bg=BG_COLOR)
            dot.pack(side="left", padx=2)
            self.dot_labels.append(dot)

        # ---- 置顶复选框 ----
        self.top_var = tk.BooleanVar(value=False)
        self.top_cb = tk.Checkbutton(
            self.root, text="窗口置顶", variable=self.top_var,
            font=FONT_COUNTER, fg=TEXT_LIGHT, bg=BG_COLOR,
            selectcolor=BG_COLOR, activebackground=BG_COLOR,
            command=self.toggle_always_on_top, cursor="hand2"
        )
        self.top_cb.pack(pady=(0, 20))

    # ── 绘制环形进度 ──────────────────────────────────
    def draw_timer_face(self, fraction):
        """fraction: 0.0 ~ 1.0，1.0 表示满圈"""
        self.canvas.delete("face")
        cx = self.canvas_size // 2
        cy = self.canvas_size // 2
        radius = 110
        width = 18

        # 背景圆环
        self.canvas.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            outline="#F0E0D6", width=width, tags="face"
        )

        if fraction <= 0:
            return

        # 前景弧线
        angle = fraction * 360
        # tk 的 arc 从 3 点方向逆时针画；我们从 12 点顺时针画
        start_angle = 90
        extent = -angle

        color = TOMATO_RED if self.current_mode == "work" else \
                "#3498DB" if self.current_mode == "short_break" else "#2ECC71"

        self.canvas.create_arc(
            cx - radius, cy - radius, cx + radius, cy + radius,
            start=start_angle, extent=extent,
            outline=color, width=width,
            style="arc", tags="face"
        )

    # ── 时间格式化 ──────────────────────────────────────
    @staticmethod
    def format_time(total_seconds):
        m = total_seconds // 60
        s = total_seconds % 60
        return f"{m:02d}:{s:02d}"

    # ── 启动/暂停 ──────────────────────────────────────
    def toggle_start_pause(self):
        if not self.running:
            self.running = True
            self.paused = False
            self.start_btn.config(text="⏸  暂停", bg=BTN_PAUSE,
                                  activebackground="#D68910")
            self.countdown()
        else:
            self.paused = not self.paused
            if self.paused:
                self.start_btn.config(text="▶  继续", bg=BTN_START,
                                      activebackground="#219A52")
            else:
                self.start_btn.config(text="⏸  暂停", bg=BTN_PAUSE,
                                      activebackground="#D68910")
                self.countdown()

    # ── 倒计时 ──────────────────────────────────────────
    def countdown(self):
        if not self.running or self.paused:
            return

        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.time_label.config(text=self.format_time(self.remaining_seconds))
            fraction = self.remaining_seconds / self.total_seconds_for_mode()
            self.draw_timer_face(fraction)
            self.after_id = self.root.after(1000, self.countdown)
        else:
            self.running = False
            self.start_btn.config(text="▶  开始", bg=BTN_START,
                                  activebackground="#219A52")
            self.on_timer_end()

    # ── 当前模式总秒数 ──────────────────────────────────
    def total_seconds_for_mode(self):
        if self.current_mode == "work":
            return WORK_MIN * 60
        elif self.current_mode == "short_break":
            return SHORT_BREAK_MIN * 60
        else:
            return LONG_BREAK_MIN * 60

    # ── 计时结束 ────────────────────────────────────────
    def on_timer_end(self):
        # 播放提示音（Windows）
        for _ in range(3):
            winsound.Beep(1000, 200)
            time.sleep(0.15)

        if self.current_mode == "work":
            self.sessions_completed += 1
            self.update_dots()
            msg = f"🎉 工作 {WORK_MIN} 分钟完成！\n休息一下吧～"
            # 自动切换到短休或长休
            if self.sessions_completed % 4 == 0:
                self.switch_mode("long_break")
            else:
                self.switch_mode("short_break")
        else:
            msg = "⏰ 休息时间结束！\n准备开始新一轮工作吧～"
            self.switch_mode("work")

        # 弹窗提示（非阻塞）
        self.root.after(100, lambda: self.show_notification(msg))

    # ── 通知弹窗 ────────────────────────────────────────
    def show_notification(self, msg):
        top = tk.Toplevel(self.root)
        top.title("番茄钟提醒")
        top.geometry("320x130")
        top.resizable(False, False)
        top.configure(bg="white")
        top.transient(self.root)
        top.grab_set()

        # 居中于主窗口
        x = self.root.winfo_x() + (self.root.winfo_width() - 320) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 130) // 2
        top.geometry(f"+{x}+{y}")

        tk.Label(top, text=msg, font=("Segoe UI", 13),
                 fg=TEXT_DARK, bg="white").pack(expand=True, pady=(20, 5))
        tk.Button(top, text="确定", font=("Segoe UI", 11),
                  bg=TOMATO_RED, fg="white", relief="flat",
                  padx=25, pady=6, command=top.destroy,
                  cursor="hand2").pack(pady=(0, 15))

    # ── 重置 ────────────────────────────────────────────
    def reset(self):
        self.running = False
        self.paused = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.remaining_seconds = self.total_seconds_for_mode()
        self.time_label.config(text=self.format_time(self.remaining_seconds))
        self.draw_timer_face(1.0)
        self.start_btn.config(text="▶  开始", bg=BTN_START,
                              activebackground="#219A52")

    # ── 跳过 ────────────────────────────────────────────
    def skip(self):
        self.running = False
        self.paused = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.remaining_seconds = 0
        self.time_label.config(text="00:00")
        self.draw_timer_face(0.0)
        self.start_btn.config(text="▶  开始", bg=BTN_START,
                              activebackground="#219A52")
        self.on_timer_end()

    # ── 切换模式 ────────────────────────────────────────
    def switch_mode(self, mode):
        if self.running:
            self.running = False
            self.paused = False
            if self.after_id:
                self.root.after_cancel(self.after_id)
                self.after_id = None
            self.start_btn.config(text="▶  开始", bg=BTN_START,
                                  activebackground="#219A52")

        self.current_mode = mode
        self.remaining_seconds = self.total_seconds_for_mode()
        self.time_label.config(text=self.format_time(self.remaining_seconds))
        self.draw_timer_face(1.0)

        # 更新模式标签
        mode_text = {
            "work": ("🔴 专注工作", TOMATO_RED),
            "short_break": ("☕ 短休息", "#3498DB"),
            "long_break": ("😴 长休息", "#2ECC71"),
        }
        text, color = mode_text[mode]
        self.mode_label.config(text=text, fg=color)

    # ── 更新进度圆点 ────────────────────────────────────
    def update_dots(self):
        for i, dot in enumerate(self.dot_labels):
            if i < self.sessions_completed % 4 or \
               (self.sessions_completed % 4 == 0 and i < 4):
                pass  # 每 4 轮重置显示
        completed = self.sessions_completed % 4
        if completed == 0 and self.sessions_completed > 0:
            completed = 4
        for i, dot in enumerate(self.dot_labels):
            if i < completed:
                dot.config(text="●", fg=TOMATO_RED)
            elif i < 4:
                dot.config(text="○", fg="#BDC3C7")
            else:
                dot.config(text="")

    # ── 窗口置顶 ────────────────────────────────────────
    def toggle_always_on_top(self):
        self.root.attributes("-topmost", self.top_var.get())

    # ── 关闭窗口 ────────────────────────────────────────
    def on_close(self):
        self.running = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.root.destroy()


# ── 入口 ──────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = PomodoroApp(root)
    root.mainloop()
