import os
import subprocess
import threading
import queue
import json
import re
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import Text as TkText
from PIL import Image, ImageTk
from plyer import notification
import yt_dlp
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox

class YTDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🔥 Ultimate YT-Dlp Downloader")
        self.root.geometry("1100x700")
        self.style = ttk.Style("darkly")
        self.download_links = []
        self.queue_data = []
        self.expanded_links = []
        self.current_process = None
        self.link_queue = queue.Queue()
        self.progress_vars = {}
        self.title_map = {}
        self.download_threads = []
        self.cancel_flags = {}
        #self.skip_flags = {}
        self.history = []
        self.folder_path = tk.StringVar()
        self.link_text = tk.StringVar()
        self.download_type = tk.StringVar(value="video")
        self.audio_format = tk.StringVar(value="mp3")
        self.resolution = tk.StringVar(value="1080")
        self.playlist_toggle = tk.BooleanVar(value=False)
        self.playlist_mode = tk.StringVar(value="batch")
        self.subtitles_toggle = tk.BooleanVar(value=False)
        self.thumbnail_toggle = tk.BooleanVar(value=False)
        self.log_visible = tk.BooleanVar(value=True)
        self.build_ui()
        self.load_history()
        self.root.after(100, self.update_log)
        #self.queue_table.bind("<Button-1>", self.handle_queue_click)
        #self.should_skip = threading.Event()
        




    def build_ui(self):
        # ============ TOP BAR ============
        topbar = ttk.Frame(self.root, padding=10)
        topbar.pack(fill=X)
        ttk.Label(topbar, text="Ultimate Downloader", font=("Segoe UI", 16, "bold")).pack(side=LEFT)
        ttk.Button(topbar, text="History", bootstyle="secondary", command=self.show_history).pack(side=RIGHT, padx=5)
        ttk.Button(topbar, text="Settings", bootstyle="secondary", command=self.open_settings).pack(side=RIGHT)

        # ============ URL + OPTIONS ============
        input_frame = ttk.Frame(self.root, padding=10)
        input_frame.pack(fill=X)
        self.url_input = ttk.Text(input_frame, height=3, font=("Segoe UI", 10), wrap="word", foreground="gray")
        self.url_input.pack(fill=X, expand=True, pady=5)
        self.url_input.insert("1.0", "Paste YouTube URL(s) here...")

        def clear_placeholder(event):
            if self.url_input.get("1.0", "end").strip() == "Paste YouTube URL(s) here...":
                self.url_input.delete("1.0", "end")
                self.url_input.config(foreground="white")

        def restore_placeholder(event):
            if self.url_input.get("1.0", "end").strip() == "":
                self.url_input.insert("1.0", "Paste YouTube URL(s) here...")
                self.url_input.config(foreground="gray")

        self.url_input.bind("<FocusIn>", clear_placeholder)
        self.url_input.bind("<FocusOut>", restore_placeholder)


        button_row = ttk.Frame(input_frame)
        button_row.pack(fill=X, pady=5)
        ttk.Button(button_row, text="Add", width=12, bootstyle="primary", command=self.add_links).pack(side=LEFT, padx=5)
        ttk.Button(button_row, text="Clear All", bootstyle="danger", command=self.clear_links).pack(side=LEFT)
        self.link_counter = ttk.Label(button_row, text="Links Added: 0")
        self.link_counter.pack(side=LEFT, padx=20)

        # ============ SAVE TO PATH ============
        path_frame = ttk.Frame(self.root, padding=(10, 0))
        path_frame.pack(fill=X)
        ttk.Label(path_frame, text="Save To:").pack(side=LEFT, padx=(0, 5))
        self.save_path_entry = ttk.Entry(path_frame, textvariable=self.folder_path, width=70, state="readonly")
        self.save_path_entry.pack(side=LEFT)
        ttk.Button(path_frame, text="Browse", command=self.browse_folder, bootstyle="info").pack(side=LEFT, padx=5)

        # ============ DOWNLOAD OPTIONS ============
        options = ttk.Labelframe(self.root, text="Download Options", padding=10)
        options.pack(fill=X, padx=10, pady=10)

        radio_frame = ttk.Frame(options)
        radio_frame.pack(fill=X)
        ttk.Radiobutton(radio_frame, text="Video", variable=self.download_type, value="video", command=self.toggle_options).pack(side=LEFT, padx=5)
        ttk.Radiobutton(radio_frame, text="Audio", variable=self.download_type, value="audio", command=self.toggle_options).pack(side=LEFT, padx=5)
        ttk.Label(radio_frame, text=" | ").pack(side=LEFT)
        ttk.Label(radio_frame, text="Resolution:").pack(side=LEFT, padx=5)
        self.res_dropdown = ttk.Combobox(radio_frame, textvariable=self.resolution, values=["144", "240", "360", "480", "720", "1080"], width=6, state="readonly")
        self.res_dropdown.pack(side=LEFT)
        ttk.Label(radio_frame, text="Audio Format:").pack(side=LEFT, padx=(10, 5))
        self.audio_dropdown = ttk.Combobox(radio_frame, textvariable=self.audio_format, values=["mp3", "m4a", "flac", "wav"], width=10, state="readonly")
        self.audio_dropdown.pack(side=LEFT)

        toggle_row = ttk.Frame(options)
        toggle_row.pack(fill=X, pady=5)
        ttk.Checkbutton(toggle_row, text="Is Playlist?", variable=self.playlist_toggle, bootstyle="round-toggle").pack(side=LEFT, padx=10)
        ttk.Combobox(toggle_row, textvariable=self.playlist_mode, values=["batch", "expand"], width=10, state="readonly").pack(side=LEFT)
        ttk.Checkbutton(toggle_row, text="Download Subtitles", variable=self.subtitles_toggle, bootstyle="round-toggle").pack(side=LEFT, padx=10)
        ttk.Checkbutton(toggle_row, text="Download Thumbnail", variable=self.thumbnail_toggle, bootstyle="round-toggle").pack(side=LEFT, padx=10)
        # ============ DOWNLOAD QUEUE ============
        queue_frame = ttk.Labelframe(self.root, text="Download Queue", padding=10)
        queue_frame.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))

        columns = ("Title", "Size", "Progress", "Status", "ETA", "Speed")
        self.queue_table = ttk.Treeview(queue_frame, columns=columns, show="headings", height=8)
        for col in columns:
            self.queue_table.heading(col, text=col)
            if col == "Title":
                self.queue_table.column(col, width=320, anchor="w")
            elif col == "Size":
                self.queue_table.column(col, width=80, anchor="center")
            elif col == "Progress":
                self.queue_table.column(col, width=100, anchor="center")
            
            else:
                self.queue_table.column(col, width=80, anchor="center")
        self.queue_table.pack(fill=BOTH, expand=True)

        # ============ GLOBAL ACTIONS ============
        actions_frame = ttk.Frame(self.root)
        actions_frame.pack(pady=5)
        ttk.Button(actions_frame, text="⬇️ Download All", width=18, bootstyle="success", command=self.start_all_downloads).pack(side=LEFT, padx=10)
        ttk.Button(actions_frame, text="❌ Cancel All", width=18, bootstyle="danger", command=self.cancel_all).pack(side=LEFT)
        ttk.Button(actions_frame, text="⏭️ Skip Current Download", width=18, bootstyle="warning", command=self.skip_current).pack(side=LEFT, padx=10)


        # ============ LOG AREA (Collapsible) ============
        self.log_toggle_button = ttk.Button(self.root, text="▼ Hide Log", bootstyle="secondary", command=self.toggle_log)
        self.log_toggle_button.pack(fill=X)

        self.log_frame = ttk.Frame(self.root)

        self.log_text = TkText(self.log_frame, height=8, bg="black", fg="lime", insertbackground='white', font=("Courier", 10))
        self.log_text.pack(fill=BOTH, expand=True)
        self.log_text.insert("end", "Logs will appear here...\n")
        self.log_frame.pack(fill=BOTH, expand=False, padx=10, pady=5)

        self.log_queue = queue.Queue()

    def toggle_options(self):
        if self.download_type.get() == "audio":
            self.audio_dropdown.configure(state="readonly")
            self.res_dropdown.configure(state="disabled")
        else:
            self.audio_dropdown.configure(state="disabled")
            self.res_dropdown.configure(state="readonly")

    def toggle_log(self):
        if self.log_visible.get():
            self.log_frame.pack_forget()
            self.log_toggle_button.config(text="▲ Show Log")
            self.log_visible.set(False)
        else:
            self.log_frame.pack(fill=BOTH, expand=False, padx=10, pady=5)
            self.log_toggle_button.config(text="▼ Hide Log")
            self.log_visible.set(True)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)

    def add_links(self):
        text = self.url_input.get("1.0", "end").strip()
        links = [link.strip() for link in text.splitlines() if link.strip()]

        for link in links:
            if link not in self.download_links:
                self.download_links.append(link)
                row_id = self.queue_table.insert(
                    "", "end",
                    values=(link, "—", "0%", "Pending", "--:--", "--")
                )


                self.queue_data.append({"id": row_id, "link": link, "title": link})
                #self.skip_flags[row_id] = threading.Event()

        self.link_counter.config(text=f"Links Added: {len(self.download_links)}")
        self.url_input.delete("1.0", "end")
    
    



    def clear_links(self):
        self.download_links.clear()
        self.queue_data.clear()
        self.queue_table.delete(*self.queue_table.get_children())
        self.link_counter.config(text=f"Links Added: 0")
    
    #def handle_queue_click(self, event):
       # region = self.queue_table.identify_region(event.x, event.y)
        #column = self.queue_table.identify_column(event.x)
       # row_id = self.queue_table.identify_row(event.y)

        #if region == "cell" and column == "#7":  # Actions column
           # self.skip_download(row_id)


    #def preload_titles_and_queue(self):
    #    if self.playlist_toggle.get() and self.playlist_mode.get() == "expand":
            #expanded = []
           # for link in links_to_expand:
               # self.log_queue.put(f"🔍 Expanding playlist: {link}")
               # try:
                  #  cmd = ["yt-dlp", "--flat-playlist", "-j", link]
               #     result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                  #  for line in result.stdout.strip().splitlines():
                     #   video_id = json.loads(line).get("id")
                       # if video_id:
                       #     expanded.append(f"https://www.youtube.com/watch?v={video_id}")
              #  except Exception as e:
                 #   self.log_queue.put(f"⚠️ Playlist expansion failed: {e}")
           # links_to_expand = expanded

        #for link in links_to_expand:
           # title = link
           # try:
              #  ydl_opts = {"quiet": True, "skip_download": True}
              #  Wwith yt_dlp.YoutubeDL(ydl_opts) as ydl:
                  #  info = ydl.extract_info(link, download=False)
                   # title = info.get("title", link)
                   # self.title_map[link] = title
            #except Exception as e:
               # self.log_queue.put(f"⚠️ Title fetch failed for {link}: {e}")
                #title = link

            #row_id = self.queue_table.insert("", "end", values=(title, "—", "0%", "Pending", "--:--", "--", ""))
          #  self.queue_data.append({"id": row_id, "link": link, "title": title})
    def start_all_downloads(self):
        if not self.folder_path.get() or not os.path.isdir(self.folder_path.get()):
            messagebox.showerror("Error", "Please select a valid save folder.")
            return

        self.should_cancel = threading.Event()
        self.should_skip = threading.Event()

        # Launch a single worker thread
        threading.Thread(target=self.download_worker, daemon=True).start()

    def cancel_all(self):
        self.should_cancel.set()
    def skip_current(self):
        self.should_skip.set()
    def download_worker(self):
        for item in self.queue_data:
            if self.should_cancel.is_set():
                self.update_queue_status(item["id"], "Cancelled")
                continue
            self.download_single(item)
        



    def download_single(self, item):
        link = item["link"]
        row_id = item["id"]
        save_folder = os.path.join(self.folder_path.get(), datetime.datetime.now().strftime("%Y-%m-%d"))
        os.makedirs(save_folder, exist_ok=True)
        archive = os.path.join(save_folder, "archive.txt")

        self.update_queue_status(row_id, "Downloading...", progress="0%")

        cmd = [
            "yt-dlp", link,
            "-P", save_folder,
            "--download-archive", archive,
            "--no-abort-on-error",
            "--newline",
            "--no-warnings",
            "--restrict-filenames"
        ]

        if self.download_type.get() == "audio":
            cmd += [
                "-x", "--audio-format", self.audio_format.get(),
                "--audio-quality", "0"
            ]
        elif self.download_type.get() == "video":
            res = self.resolution.get()
            cmd += [
                "-f", f"bestvideo[height<={res}]+bestaudio/best",
                "--merge-output-format", "mp4"
            ]
        
        


        if self.subtitles_toggle.get():
            cmd += ["--write-subs", "--sub-lang", "en", "--convert-subs", "srt"]
        if self.thumbnail_toggle.get():
            cmd += ["--write-thumbnail", "--embed-thumbnail"]

        if self.playlist_toggle.get() and self.playlist_mode.get() == "batch":
            cmd += ["--yes-playlist", "--output", "%(playlist_index)03d - %(title).100s.%(ext)s"]
        else:
            cmd += ["--no-playlist", "--output", "%(title).100s.%(ext)s"]

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            item["process"] = proc
            for line in proc.stdout:
                if self.should_cancel.is_set():
                    proc.kill()
                    self.update_queue_status(row_id, "Cancelled")
                    return
                if self.should_skip.is_set():
                    proc.kill()
                    self.update_queue_status(row_id, "Skipped")
                    self.log_queue.put(f"⏭️ Skipped: {link}")
                    self.should_skip.clear()
                    return


                percent = re.search(r'(\d{1,3}\.\d)%', line)
                eta = re.search(r'ETA\s+(\d{2}:\d{2})', line)
                speed = re.search(r'(\d+(\.\d+)?[KM]iB/s)', line)
                #size = re.search(r'\d{1,3}\.\d+%\s+of\s+([\d\.]+\w+)', line) or \
                    #re.search(r'Total file size:\s+([\d\.]+\s+\w+)', line)
                size_match = re.search(r'of\s+~?\s*([\d\.]+\s*[KMGT]?i?B)', line)
                if not size_match:
                    size_match = re.search(r'Total file size:\s+([\d\.]+\s*[KMGT]?i?B)', line)

                if size_match:
                    self.queue_table.set(row_id, "Size", size_match.group(1).strip())


                #if size_match:
                    #self.queue_table.set(row_id, "Size", size_match.group(1))

                if percent:
                    self.queue_table.set(row_id, "Progress", f"{percent.group(1)}%")
                if eta:
                    self.queue_table.set(row_id, "ETA", eta.group(1))
                if speed:
                    self.queue_table.set(row_id, "Speed", speed.group(1))

                self.log_queue.put(line.strip())



            proc.wait()
            self.update_queue_status(row_id, "Completed")
            self.save_to_history(link)

        except Exception as e:
            self.update_queue_status(row_id, "Error")
            self.log_queue.put(f"⚠️ Download failed: {e}")
    
    def skip_download(self, row_id):
        for item in self.queue_data:
            if item["id"] == row_id:
                proc = item.get("process")
                if proc and proc.poll() is None:  # If process is still running
                    proc.kill()  # Force kill the yt-dlp process
                self.update_queue_status(row_id, "Skipped")
                return


    def update_queue_status(self, row_id, status, progress=None):
        self.queue_table.set(row_id, "Status", status)
        if progress:
            self.queue_table.set(row_id, "Progress", progress)

    def save_to_history(self, link):
        self.history.append(link)
        with open("download_history.json", "w") as f:
            json.dump(self.history, f)

    def show_history(self):
        win = ttk.Toplevel(self.root)
        win.title("📜 Download History")
        txt = TkText(win, wrap="word", height=20, bg="#101010", fg="#00FF00", insertbackground="white")
        txt.pack(expand=True, fill="both")
        txt.insert("1.0", "\n".join(self.history))
        txt.config(state="disabled")

    def open_settings(self):
        win = ttk.Toplevel(self.root)
        win.title("⚙️ Settings")
        win.geometry("300x150")

        ttk.Label(win, text="History:").pack(pady=5)
        ttk.Button(win, text="🧹 Clear History", command=self.clear_history, bootstyle="danger").pack()

    def clear_history(self):
        self.history.clear()
        if os.path.exists("download_history.json"):
            os.remove("download_history.json")
        messagebox.showinfo("Cleared", "Download history cleared.")

    def update_log(self):
        try:
            while True:
                line = self.log_queue.get_nowait()

                # Check if it's a progress line (contains % and ETA)
                if re.search(r'\d{1,3}\.\d+%.*?ETA', line):
                    self.log_text.delete("end-2l", "end-1l")  # remove previous progress line
                self.log_text.insert("end", line + "\n")
                self.log_text.see("end")

        except queue.Empty:
            pass
        self.root.after(100, self.update_log)

    def load_history(self):
        if os.path.exists("download_history.json"):
            try:
                with open("download_history.json", "r") as f:
                    self.history = json.load(f)
            except Exception as e:
                self.log_queue.put(f"⚠️ Failed to load history: {e}")
                self.history = []

if __name__ == "__main__":
    root = ttk.Window(themename="darkly")
    app = YTDownloaderApp(root)
    root.mainloop()
