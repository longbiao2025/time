import tkinter as tk
from tkinter import ttk
from tkinter import simpledialog, messagebox
import time
import threading
import platform

class CountdownTimerApp:
    def __init__(self, root):
        self.root = root
        root.title("倒计时")
        root.overrideredirect(True)  # 移除窗口标题栏和边框
        root.attributes('-topmost', True)

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = 160  # Fixed width
        window_height = 40  # Fixed height
        margin_right = 20
        margin_top = 20

        x_pos = screen_width - window_width - margin_right
        y_pos = margin_top
        root.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")
        root.resizable(False, False)
        root.config(bg="black")

        # macOS 风格字体设置
        if platform.system() == "Darwin":
            font_family = "PingFang SC"
            self.font_size_default = 24
        else:
            font_family = "SimHei"  # Or another suitable font for Windows/Linux
            self.font_size_default = 20

        self.time_display = tk.Label(root, text="右键设置", font=(font_family, self.font_size_default),
                                     bg="black", fg="yellow", padx=0, pady=0, bd=0, highlightthickness=0)  # Remove padding and borders
        self.time_display.pack(padx=0, pady=0, fill=tk.BOTH, expand=True, side=tk.LEFT)  # Fill entire window, no padding, align to left

        self.is_running = False
        self.start_time = 0
        self.paused_time = 0
        self.total_paused_time = 0
        self.countdown_duration = 0
        self.overtime_seconds = 0
        self.is_flashing = False
        self.flash_start_time = 0
        self.timer_running = False
        self.overtime_start_time = 0  # Initialize overtime_start_time

        self.create_right_click_menu()
        self.time_display.bind("<Double-Button-1>", self.toggle_pause_resume)
        self.time_display.bind("<Button-1>", self.start_drag)
        self.time_display.bind("<B1-Motion>", self.drag_window)

        # 针对Mac系统适配右键点击事件
        if platform.system() == "Darwin":
            # 在Mac上同时监听Button-2和Button-3以确保兼容性
            self.time_display.bind("<Button-2>", self.show_right_click_menu)
            self.time_display.bind("<Button-3>", self.show_right_click_menu)
        else:
            # 对于非Mac系统（如Windows、Linux），仅监听Button-3
            self.time_display.bind("<Button-3>", self.show_right_click_menu)

        self.x_offset = 0
        self.y_offset = 0

        self.check_instance()
        # 删除了 keep_on_top 循环，改用更优雅的事件驱动逻辑

    def check_instance(self):
        try:
            self.instance_check_var = tk.IntVar()
            self.instance_check_var.set(1)
        except Exception as e:
            messagebox.showerror("错误", "程序已经在运行！")
            self.root.destroy()

    def create_right_click_menu(self):
        self.right_click_menu = tk.Menu(self.root, tearoff=0)
        self.right_click_menu.add_command(label="【退出】", command=self.close_app, foreground="red")  # "【退出】" menu item at the top, with red color
        time_options = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60]
        for option in time_options:
            self.right_click_menu.add_command(label=f"{option}分钟", command=lambda m=option: self.set_countdown_time(m))
        self.right_click_menu.add_command(label="自定义", command=self.set_custom_time)

    def show_right_click_menu(self, event):
        # 【关键修改】：弹出菜单前临时取消主窗口置顶，防止挡住菜单
        self.root.attributes('-topmost', False)
        try:
            # tk_popup 会阻塞执行，直到用户点选了菜单或点击了其他地方关闭菜单
            self.right_click_menu.tk_popup(event.x_root, event.y_root)
        finally:
            # 菜单一旦关闭，立刻恢复主窗口的置顶状态
            self.root.attributes('-topmost', True)

    def set_countdown_time(self, minutes):
        self.countdown_duration = minutes * 60
        self.start_timer()

    def set_custom_time(self):
        # 获取主窗口位置和高度
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_height = self.root.winfo_height()

        dialog = tk.Toplevel(self.root)
        dialog.title("设置时间")
        dialog.transient(self.root) # 使得dialog依附于主窗口
        dialog.grab_set() # 强制dialog为顶层窗口
        
        # 确保弹窗也置顶
        dialog.attributes('-topmost', True) 

        dialog_x = root_x
        dialog_y = root_y + root_height
        dialog.geometry(f"+{dialog_x}+{dialog_y}")

        tk.Label(dialog, text="请输入时间（分钟）：").pack(pady=5)
        entry = tk.Entry(dialog)
        entry.pack(pady=5)
        entry.focus_set() # 默认聚焦到输入框

        def ok_command():
            custom_minutes_str = entry.get()
            try:
                custom_minutes = int(custom_minutes_str)
                if custom_minutes < 1:
                    messagebox.showerror("提示", "不允许小于 1 分钟", parent=dialog)
                    return
                self.countdown_duration = custom_minutes * 60
                self.start_timer()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("提示", "请输入整数", parent=dialog)

        def cancel_command():
            dialog.destroy()

        ok_button = tk.Button(dialog, text="确定", command=ok_command)
        ok_button.pack(side=tk.LEFT, padx=5, pady=5)
        cancel_button = tk.Button(dialog, text="取消", command=cancel_command)
        cancel_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # 绑定回车键到 ok_command
        dialog.bind("<Return>", lambda event: ok_command())

        dialog.wait_window(dialog) # 等待dialog关闭

    def start_timer(self):
        self.is_running = True
        self.start_time = time.time()
        self.paused_time = 0
        self.total_paused_time = 0
        self.countdown_duration = int(self.countdown_duration)  # Ensure countdown_duration is int
        self.overtime_seconds = 0
        self.is_flashing = False
        self.time_display.config(fg="yellow", bg="black")
        self.update_timer_display()
        if not self.timer_running:
            self.timer_running = True
            self.run_timer_loop()

    def run_timer_loop(self):
        if self.is_running:
            self.update_timer_display()
            self.root.after(100, self.run_timer_loop)
        else:
            self.timer_running = False

    def update_timer_display(self):
        if not self.is_running:
            return

        elapsed_time_seconds = int(time.time() - self.start_time - self.total_paused_time)

        if self.countdown_duration > 0:  # Countdown mode
            remaining_seconds = max(0, self.countdown_duration - elapsed_time_seconds)
            if remaining_seconds > 0:  # Still in countdown
                minutes = remaining_seconds // 60
                seconds = remaining_seconds % 60
                time_str = f"剩余 {minutes:01d}:{seconds:02d}"

                if 55 <= remaining_seconds <= 60 and not self.is_flashing:
                    self.start_flash()
                elif not (55 <= remaining_seconds <= 60) and self.is_flashing:
                    self.stop_flash()
            else:  # Countdown finished, switch to overtime
                self.countdown_duration = 0
                self.overtime_seconds = 0
                self.total_paused_time = 0  # Reset paused time when switching to overtime
                minutes = self.overtime_seconds // 60
                seconds = self.overtime_seconds % 60
                time_str = f"超时 {minutes:01d}:{seconds:02d}"
                self.time_display.config(bg="red")
                self.stop_flash()
                self.is_running = True
                self.overtime_start_time = time.time()

        else:  # Overtime mode (countdown_duration is 0)
            self.overtime_seconds = int(time.time() - self.overtime_start_time - self.total_paused_time)  # Subtract paused time in overtime
            minutes = self.overtime_seconds // 60
            seconds = self.overtime_seconds % 60
            time_str = f"超时 {minutes:01d}:{seconds:02d}"
            self.time_display.config(bg="red")

        self.time_display.config(text=time_str)

    def start_flash(self):
        if not self.is_flashing:
            self.is_flashing = True
            self.flash_start_time = time.time()
            self._flash_color_toggle()

    def stop_flash(self):
        if self.is_flashing:
            self.is_flashing = False
            self.time_display.config(bg="black")

    def _flash_color_toggle(self):
        if not self.is_flashing:
            return

        current_bg = self.time_display.cget("bg")
        if current_bg == "black":
            next_bg = "red"
        else:
            next_bg = "black"
        self.time_display.config(bg=next_bg)
        self.root.after(500, self._flash_color_toggle)

    def toggle_pause_resume(self, event=None):
        if not self.countdown_duration and self.overtime_seconds == 0 and not self.is_running:
            return

        if self.is_running:
            self.is_running = False
            self.paused_time = time.time()
            self.time_display.config(text="暂停中", bg="#808080")
            self.stop_flash()
        else:
            if self.paused_time:
                self.total_paused_time += (time.time() - self.paused_time)
                self.paused_time = 0
            self.is_running = True
            self.time_display.config(bg="black")
            if not self.timer_running:
                self.timer_running = True
                self.run_timer_loop()

    def start_drag(self, event):
        self.x_offset = event.x
        self.y_offset = event.y
        # 【轻量防掉层】：抛弃死循环，每次鼠标点击窗口时，顺手重新声明一次置顶
        # 这样即使在 macOS 下偶尔掉到后面，点它一下或者拖动一下就立刻回到最上层
        self.root.attributes('-topmost', True)

    def drag_window(self, event):
        x = self.root.winfo_pointerx() - self.x_offset
        y = self.root.winfo_pointery() - self.y_offset
        self.root.geometry(f"+{x}+{y}")

    def close_app(self, event=None):
        print("开始执行 close_app 方法...")
        self.is_running = False
        try:
            print("尝试退出 Tkinter 主循环...")
            self.root.quit()
            print("Tkinter 主循环退出完成。")
        except Exception as e:
            print(f"退出 Tkinter 主循环时出错: {e}")
            import traceback
            traceback.print_exc()
        print("close_app 方法结束。")


if __name__ == "__main__":
    root = tk.Tk()
    if platform.system() == "Darwin":
        root.tk.call('::tk::unsupported::MacWindowStyle', 'style', root, 'document')
        root.tk.call('set', '::tk::mac::Appearance', 'light')

    app = CountdownTimerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close_app)
    root.mainloop()