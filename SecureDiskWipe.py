import os
import sys
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import psutil
from typing import Literal

# Constants for Windows System
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3

PatternType = Literal['zeros', 'ones', 'random']


def install_modules():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])


try:
    import psutil
except ModuleNotFoundError:
    install_modules()
    import psutil


def generate_pattern(size: int, pattern_type: PatternType = 'random') -> bytes:
    if pattern_type == 'zeros':
        return b'\x00' * size
    elif pattern_type == 'ones':
        return b'\xFF' * size
    else:
        return os.urandom(size)


def wipe_disk_linux(disk_name: str, pattern_type: PatternType = 'random', passes: int = 3, log_box=None) -> None:
    try:
        with open(disk_name, 'rb+') as disk:
            disk.seek(0, os.SEEK_END)
            disk_size: int = disk.tell()
            disk.seek(0)

            buffer_size: int = 512
            num_sectors: int = disk_size // buffer_size

            for times in range(passes):
                for sector in range(num_sectors):
                    buffer: bytes = generate_pattern(buffer_size, pattern_type)
                    disk.write(buffer)
                if log_box:
                    log_box.insert(tk.END, f"Pass {times + 1} complete.\n")
                    log_box.see(tk.END)
            disk.flush()
            os.fsync(disk.fileno())
        if log_box:
            log_box.insert(tk.END, "The Disk Wipe was Completed.\n")
            log_box.see(tk.END)
    except OSError as e:
        print(f"Failed to open or write to the disk: {e}")
        sys.exit(503)


class DiskWiperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Disk Wiper")
        self.root.geometry("600x500")

        self.partitions = psutil.disk_partitions()

        self.create_widgets()

    def create_widgets(self):
        # Frame for Disk Selection
        disk_frame = ttk.LabelFrame(self.root, text="Select Disk")
        disk_frame.pack(fill="x", padx=10, pady=5)

        self.partition_label = ttk.Label(disk_frame, text="Select Partition:")
        self.partition_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.partition_combo = ttk.Combobox(disk_frame, values=[p.device for p in self.partitions], state='readonly')
        self.partition_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.partition_combo.current(0)

        # Frame for Wipe Options
        options_frame = ttk.LabelFrame(self.root, text="Options")
        options_frame.pack(fill="x", padx=10, pady=5)

        self.pattern_label = ttk.Label(options_frame, text="Choose Pattern:")
        self.pattern_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.pattern_combo = ttk.Combobox(options_frame, values=['zeros', 'ones', 'random'], state='readonly')
        self.pattern_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.pattern_combo.current(2)  # Default to 'random'

        self.passes_label = ttk.Label(options_frame, text="Number of Passes:")
        self.passes_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.passes_entry = ttk.Entry(options_frame)
        self.passes_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.passes_entry.insert(0, '3')

        # Frame for Progress
        progress_frame = ttk.LabelFrame(self.root, text="Progress")
        progress_frame.pack(fill="x", padx=10, pady=5)

        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", padx=5, pady=5)

        # Frame for Logs
        logs_frame = ttk.LabelFrame(self.root, text="Logs")
        logs_frame.pack(fill="both", padx=10, pady=5, expand=True)

        self.log_box = ScrolledText(logs_frame, wrap=tk.WORD, height=10)
        self.log_box.pack(fill="both", expand=True, padx=5, pady=5)

        # Wipe Button
        self.wipe_button = ttk.Button(self.root, text="Start Wipe", command=self.start_wipe)
        self.wipe_button.pack(pady=10)

    def start_wipe(self):
        selected_partition = self.partition_combo.get()
        pattern = self.pattern_combo.get()
        passes = self.passes_entry.get()

        if not selected_partition:
            messagebox.showerror("Error", "Please select a partition to wipe.")
            return

        if not passes.isdigit() or int(passes) < 1:
            messagebox.showerror("Error", "Passes should be a positive integer.")
            return

        passes = int(passes)

        if messagebox.askyesno("Confirmation", "Are you sure you want to wipe the disk? This action is irreversible!"):
            system_type = platform.system()

            self.progress_bar['value'] = 0
            self.log_box.insert(tk.END, "Wiping process started...\n")

            if system_type == 'Linux':
                num_sectors = self.estimate_num_sectors(selected_partition)
                self.progress_bar['maximum'] = passes * num_sectors
                self.wipe_disk_with_progress(selected_partition, pattern, passes)
            else:
                messagebox.showerror("Error", f"Unsupported operating system: {system_type}")

    def estimate_num_sectors(self, disk_name):
        try:
            with open(disk_name, 'rb') as disk:
                disk.seek(0, os.SEEK_END)
                disk_size = disk.tell()
                disk.seek(0)
                buffer_size = 512  # Sector size
                return disk_size // buffer_size
        except OSError as e:
            messagebox.showerror("Error", f"Failed to estimate sectors: {e}")
            return 0

    def wipe_disk_with_progress(self, disk_name, pattern, passes):
        try:
            with open(disk_name, 'rb+') as disk:
                disk_size = self.estimate_num_sectors(disk_name) * 512
                buffer_size = 512
                num_sectors = disk_size // buffer_size

                for times in range(passes):
                    for sector in range(num_sectors):
                        buffer = generate_pattern(buffer_size, pattern)
                        disk.write(buffer)
                        self.progress_bar['value'] += 1
                        self.root.update_idletasks()
                    self.log_box.insert(tk.END, f"Pass {times + 1} complete.\n")
                    self.log_box.see(tk.END)
                disk.flush()
                os.fsync(disk.fileno())
            self.log_box.insert(tk.END, "The Disk Wipe was Completed.\n")
            self.log_box.see(tk.END)
        except OSError as e:
            msg = f"Failed to open or write to the disk: {e}"
            self.log_box.insert(tk.END, msg + "\n")
            messagebox.showerror("Error", msg)


if __name__ == "__main__":
    root = tk.Tk()
    app = DiskWiperApp(root)
    root.mainloop()

