import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext
import subprocess
import re
import os

class VideoQualityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Quality Analyzer")

        self.ffmpeg_dir = ""
        self.ref_video_path = ""
        self.enc_video_path = ""

        self.create_widgets()

        self.tooltip_label = tk.Label(self.root, bg="lightyellow", relief="solid", borderwidth=1, wraplength=300)
        self.tooltip_label.place_forget()

        self.metric_tooltips = {
            'vmaf': (
                "VMAF (Video Multi-method Assessment Fusion) – это комбинированный алгоритм оценки качества видео, "
                "разработанный Netflix. Он объединяет несколько показателей, чтобы дать общую оценку визуального качества. "
                "Значения варьируются от 0 до 100, где более 90 обычно означает высокое качество, а менее 70 – низкое."
            )
        }
        self.metric_channel_tooltips = {
            'ssim': {
                'Y': (
                    "SSIM Y: Это оценка структурного сходства для яркостного канала (Y). "
                    "Значение ближе к 1 означает, что яркостная составляющая в сравнении с референсом практически идентична. "
                    "Этот показатель важен, так как человеческий глаз особенно чувствителен к изменениям яркости."
                ),
                'U': (
                    "SSIM U: Оценка структурного сходства для хроматической компоненты U. "
                    "Данный показатель влияет на цветовую составляющую видео. "
                    "Близкие к 1 значения означают высокое сходство цветовых характеристик."
                ),
                'V': (
                    "SSIM V: Оценка структурного сходства для хроматической компоненты V. "
                    "Как и U, этот параметр отвечает за точность цветопередачи. "
                    "Высокие значения указывают на сохранение цветовой информации при сжатии."
                ),
                'All': (
                    "SSIM All: Итоговое значение, объединяющее оценки по каналам Y, U и V. "
                    "Оно даёт общее представление о качестве видео. "
                    "Значение близкое к 1 означает, что общее качество сохраняется на высоком уровне."
                )
            },
            'psnr': {
                'Y': (
                    "PSNR Y: Это отношение сигнал/шум для яркостного канала в децибелах. "
                    "Высокие значения (например, выше 40 дБ) свидетельствуют о хорошем качестве передачи яркости. "
                    "Данный показатель важен для оценки потерь деталей в яркости."
                ),
                'U': (
                    "PSNR U: Отношение сигнал/шум для U-компоненты, отвечающей за цветовую информацию. "
                    "Высокое значение указывает на минимальные потери в этой части цвета при сжатии."
                ),
                'V': (
                    "PSNR V: Отношение сигнал/шум для V-компоненты. "
                    "Как и для U, высокое значение показывает сохранение цветовой информации без значительных искажений."
                ),
                'Avg': (
                    "PSNR Average: Среднее значение PSNR, объединяющее показатели по каналам. "
                    "Оно отражает общее качество видео по отношению сигнал/шум. "
                    "Чем выше значение, тем лучше качество с меньшими искажениями."
                )
            }
        }

    def create_widgets(self):
        btn_select_ffmpeg = ttk.Button(self.root, text="Выбрать папку с FFmpeg", command=self.set_ffmpeg_dir)
        btn_select_ffmpeg.grid(row=0, column=0, padx=5, pady=5)
        self.ffmpeg_label = ttk.Label(self.root, text="FFmpeg: Не выбрана")
        self.ffmpeg_label.grid(row=0, column=1, padx=5, pady=5)

        btn_select_ref = ttk.Button(self.root, text="Исходное видео", command=lambda: self.set_video("ref"))
        btn_select_ref.grid(row=1, column=0, padx=5, pady=5)
        btn_select_enc = ttk.Button(self.root, text="Закодированное видео", command=lambda: self.set_video("enc"))
        btn_select_enc.grid(row=2, column=0, padx=5, pady=5)

        self.ref_video_label = ttk.Label(self.root, text="Исходное: Не выбрано", wraplength=500)
        self.ref_video_label.grid(row=1, column=1, padx=5, pady=5)
        self.enc_video_label = ttk.Label(self.root, text="Закодированное: Не выбрано", wraplength=500)
        self.enc_video_label.grid(row=2, column=1, padx=5, pady=5)

        self.results_frame = ttk.LabelFrame(self.root, text="Результаты")
        self.results_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        self.metric_result_labels = {}
        for metric in ['ssim', 'psnr', 'vmaf']:
            metric_frame = ttk.LabelFrame(self.results_frame, text=metric.upper())
            metric_frame.pack(fill="x", padx=5, pady=2)
            if metric in ['ssim', 'psnr']:
                self.metric_result_labels[metric] = {}
                end_key = 'All' if metric == 'ssim' else 'Avg'
                channels = ['Y', 'U', 'V', end_key]
                for ch in channels:
                    label = ttk.Label(metric_frame, text=f"{ch}: N/A")
                    label.pack(side="left", padx=5, pady=2)
                    label.bind("<Enter>", lambda event, m=metric, ch=ch: self.show_channel_tooltip(event, m, ch))
                    label.bind("<Leave>", self.hide_tooltip)
                    self.metric_result_labels[metric][ch] = label
            else:
                label = ttk.Label(metric_frame, text="Score: N/A")
                label.pack(side="left", padx=5, pady=2)
                label.bind("<Enter>", lambda event, m=metric: self.show_metric_tooltip(event, m))
                label.bind("<Leave>", self.hide_tooltip)
                self.metric_result_labels[metric] = label

        self.console_text = scrolledtext.ScrolledText(self.root, width=130, height=22)
        self.console_text.grid(row=4, column=0, columnspan=2, padx=5, pady=5)

        btn_analyze = ttk.Button(self.root, text="Анализ", command=self.run_analysis)
        btn_analyze.grid(row=5, column=0, padx=5, pady=5)
        btn_save = ttk.Button(self.root, text="Сохранить вывод консоли", command=self.save_results)
        btn_save.grid(row=5, column=1, padx=5, pady=5)
        btn_copy = ttk.Button(self.root, text="Копировать вывод консоли в буфер", command=self.copy_results)
        btn_copy.grid(row=6, column=0, columnspan=2, pady=5)

    def set_ffmpeg_dir(self):
        self.ffmpeg_dir = filedialog.askdirectory(title="Выберите папку с FFmpeg")
        self.ffmpeg_label.config(text=f"FFmpeg: {self.ffmpeg_dir}")

    def set_video(self, video_type):
        selected_path = filedialog.askopenfilename(title=f"Выберите {video_type} видео")
        if not selected_path:
            return
        if video_type == "ref":
            self.ref_video_path = selected_path
            self.ref_video_label.config(text=f"Исходное: {os.path.basename(selected_path)}")
        else:
            self.enc_video_path = selected_path
            self.enc_video_label.config(text=f"Закодированное: {os.path.basename(selected_path)}")

    def show_metric_tooltip(self, event, metric):
        x = event.widget.winfo_rootx() - self.root.winfo_rootx() + 25
        y = event.widget.winfo_rooty() - self.root.winfo_rooty() + 25
        tooltip_text = self.metric_tooltips.get(metric, "")
        self.tooltip_label.config(text=tooltip_text)
        self.tooltip_label.place(x=x, y=y)

    def show_channel_tooltip(self, event, metric, channel):
        x = event.widget.winfo_rootx() - self.root.winfo_rootx() + 25
        y = event.widget.winfo_rooty() - self.root.winfo_rooty() + 25
        tooltip_text = self.metric_channel_tooltips.get(metric, {}).get(channel, "")
        self.tooltip_label.config(text=tooltip_text)
        self.tooltip_label.place(x=x, y=y)

    def hide_tooltip(self, event):
        self.tooltip_label.place_forget()

    def run_ffmpeg_command(self, command):
        try:
            self.console_text.insert(tk.END, f">>> {' '.join(command)}\n")
            self.console_text.see(tk.END)
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            for line in process.stdout:
                self.console_text.insert(tk.END, line)
                self.console_text.see(tk.END)
                self.root.update()
            process.wait()
            return process.returncode == 0
        except Exception as e:
            self.console_text.insert(tk.END, f"Ошибка: {str(e)}\n")
            return False

    def run_analysis(self):
        if not all([self.ffmpeg_dir, self.ref_video_path, self.enc_video_path]):
            self.console_text.insert(tk.END, "Ошибка: Сначала выберите FFmpeg и оба видео!\n")
            return

        os.environ["PATH"] = os.environ["PATH"] + os.pathsep + self.ffmpeg_dir

        self.console_text.insert(tk.END, "\n=== Запуск SSIM ===\n")
        ssim_cmd = [
            "ffmpeg",
            "-i", self.ref_video_path,
            "-i", self.enc_video_path,
            "-lavfi", "[0:v]setpts=PTS-STARTPTS[ref];[1:v]setpts=PTS-STARTPTS[enc];[ref][enc]ssim=stats_file=ssim.log",
            "-f", "null", "-"
        ]
        if self.run_ffmpeg_command(ssim_cmd):
            ssim_output = self.console_text.get("1.0", tk.END)
            ssim_match = re.search(
                r"SSIM\s+Y:(\d+\.\d+).*U:(\d+\.\d+).*V:(\d+\.\d+).*All:(\d+\.\d+)",
                ssim_output, re.DOTALL | re.IGNORECASE
            )
            if ssim_match:
                self.metric_result_labels['ssim']['Y'].config(text=f"Y: {ssim_match.group(1)}")
                self.metric_result_labels['ssim']['U'].config(text=f"U: {ssim_match.group(2)}")
                self.metric_result_labels['ssim']['V'].config(text=f"V: {ssim_match.group(3)}")
                self.metric_result_labels['ssim']['All'].config(text=f"All: {ssim_match.group(4)}")
            else:
                for ch in ['Y', 'U', 'V', 'All']:
                    self.metric_result_labels['ssim'][ch].config(text=f"{ch}: Ошибка")

        self.console_text.insert(tk.END, "\n=== Запуск PSNR ===\n")
        psnr_cmd = [
            "ffmpeg",
            "-i", self.ref_video_path,
            "-i", self.enc_video_path,
            "-lavfi", "[0:v]setpts=PTS-STARTPTS[ref];[1:v]setpts=PTS-STARTPTS[enc];[ref][enc]psnr=stats_file=psnr.log",
            "-f", "null", "-"
        ]
        if self.run_ffmpeg_command(psnr_cmd):
            psnr_output = self.console_text.get("1.0", tk.END)
            psnr_match = re.search(
                r"PSNR\s+y:(\d+\.\d+)\s+u:(\d+\.\d+)\s+v:(\d+\.\d+)\s+average:(\d+\.\d+)",
                psnr_output, re.IGNORECASE
            )
            if psnr_match:
                self.metric_result_labels['psnr']['Y'].config(text=f"Y: {psnr_match.group(1)}")
                self.metric_result_labels['psnr']['U'].config(text=f"U: {psnr_match.group(2)}")
                self.metric_result_labels['psnr']['V'].config(text=f"V: {psnr_match.group(3)}")
                self.metric_result_labels['psnr']['Avg'].config(text=f"Avg: {psnr_match.group(4)}")
            else:
                for ch in ['Y', 'U', 'V', 'Avg']:
                    self.metric_result_labels['psnr'][ch].config(text=f"{ch}: Ошибка")

        self.console_text.insert(tk.END, "\n=== Запуск VMAF ===\n")
        vmaf_cmd = [
            "ffmpeg",
            "-i", self.ref_video_path,
            "-i", self.enc_video_path,
            "-lavfi", "[0:v]setpts=PTS-STARTPTS[ref];[1:v]setpts=PTS-STARTPTS[enc];[ref][enc]libvmaf=n_threads=32:log_path=log.json",
            "-f", "null", "-"
        ]
        if self.run_ffmpeg_command(vmaf_cmd):
            vmaf_output = self.console_text.get("1.0", tk.END)
            vmaf_match = re.search(r"VMAF score:\s*(\d+\.\d+)", vmaf_output)
            if vmaf_match:
                self.metric_result_labels['vmaf'].config(text=f"Score: {vmaf_match.group(1)}")
            else:
                self.metric_result_labels['vmaf'].config(text="Score: Ошибка")

    def save_results(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(self.console_text.get("1.0", tk.END))

    def copy_results(self):
        log_text = self.console_text.get("1.0", tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(log_text.strip())

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoQualityApp(root)
    root.mainloop()
