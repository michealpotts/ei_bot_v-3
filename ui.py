"""
Simple Tkinter UI for the scraper: email/password, start/stop, log display.
Run with: python main.py --ui
"""
import asyncio
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext

from main import run_scraper


class QueueStdout:
    """Writes to both a queue (for UI) and original stdout."""
    def __init__(self, log_queue, original):
        self.log_queue = log_queue
        self.original = original

    def write(self, s):
        if s and s.strip():
            self.log_queue.put(s.strip())
        self.original.write(s)

    def flush(self):
        self.original.flush()


def run_async_scraper(email: str, password: str, stop_event: threading.Event, log_queue: queue.Queue):
    """Run the scraper in a new event loop (called from a background thread)."""
    try:
        # Redirect stdout so all print() go to the log queue
        tee = QueueStdout(log_queue, sys.stdout)
        old_stdout = sys.stdout
        sys.stdout = tee
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_scraper(email, password, headless=True, stop_event=stop_event))
        finally:
            sys.stdout = old_stdout
            log_queue.put("[Scraper finished]")
    except Exception as e:
        log_queue.put(f"[ERROR] {e}")
        import traceback
        log_queue.put(traceback.format_exc())


def run_ui():
    root = tk.Tk()
    root.title("Scraper Bot")
    root.minsize(500, 400)
    root.geometry("620x520")

    # Variables
    stop_event: threading.Event | None = None
    scraper_thread: threading.Thread | None = None
    log_queue: queue.Queue = queue.Queue()
    poll_id = None

    # Styles (don't use "Segoe UI" in option_add - Tk parses "UI" as size and fails)
    root.configure(bg="#1e1e2e")

    # Main frame
    main = ttk.Frame(root, padding=12)
    main.pack(fill=tk.BOTH, expand=True)

    # Credentials
    cred_frame = ttk.Frame(main)
    cred_frame.pack(fill=tk.X, pady=(0, 8))

    ttk.Label(cred_frame, text="Email:").grid(row=0, column=0, sticky=tk.W, padx=(0, 8), pady=4)
    email_var = tk.StringVar()
    email_entry = ttk.Entry(cred_frame, textvariable=email_var, width=40)
    email_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 16), pady=4)

    ttk.Label(cred_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, padx=(0, 8), pady=4)
    password_var = tk.StringVar()
    password_entry = ttk.Entry(cred_frame, textvariable=password_var, width=40, show="•")
    password_entry.grid(row=1, column=1, sticky=tk.EW, padx=(0, 16), pady=4)

    cred_frame.columnconfigure(1, weight=1)

    # Buttons
    btn_frame = ttk.Frame(main)
    btn_frame.pack(fill=tk.X, pady=(0, 8))

    start_btn = ttk.Button(btn_frame, text="Start", command=None)
    stop_btn = ttk.Button(btn_frame, text="Stop", command=None, state=tk.DISABLED)

    def start():
        email = email_var.get().strip()
        password = password_var.get().strip()
        if not email or not password:
            log_widget.insert(tk.END, "[ERROR] Enter email and password.\n", "error")
            log_widget.see(tk.END)
            return
        nonlocal stop_event, scraper_thread, poll_id
        stop_event = threading.Event()
        log_widget.delete(1.0, tk.END)
        log_widget.insert(tk.END, "-------------------------- bot working -----------------------------\n", "info")
        start_btn.configure(state=tk.DISABLED)
        stop_btn.configure(state=tk.NORMAL)
        scraper_thread = threading.Thread(
            target=run_async_scraper,
            args=(email, password, stop_event, log_queue),
            daemon=True,
        )
        scraper_thread.start()

        def poll():
            nonlocal poll_id
            try:
                while True:
                    msg = log_queue.get_nowait()
                    tag = "error" if "[ERROR]" in msg else "info"
                    log_widget.insert(tk.END, msg + "\n", tag)
                    log_widget.see(tk.END)
            except queue.Empty:
                pass
            if scraper_thread and scraper_thread.is_alive():
                poll_id = root.after(200, poll)
            else:
                start_btn.configure(state=tk.NORMAL)
                stop_btn.configure(state=tk.DISABLED)

        poll_id = root.after(200, poll)

    def stop():
        if stop_event:
            stop_event.set()
            log_widget.insert(tk.END, "[INFO] Stop requested. Waiting for scraper to finish...\n", "info")
            log_widget.see(tk.END)

    start_btn.configure(command=start)
    stop_btn.configure(command=stop)
    start_btn.pack(side=tk.LEFT, padx=(0, 8))
    stop_btn.pack(side=tk.LEFT)

    # Log area
    ttk.Label(main, text="Logs:").pack(anchor=tk.W, pady=(8, 0))
    log_frame = ttk.Frame(main)
    log_frame.pack(fill=tk.BOTH, expand=True, pady=4)
    log_widget = scrolledtext.ScrolledText(
        log_frame,
        wrap=tk.WORD,
        height=16,
        state=tk.NORMAL,
        bg="#313244",
        fg="#cdd6f4",
        insertbackground="#cdd6f4",
        font=("Consolas", 9),
    )
    log_widget.pack(fill=tk.BOTH, expand=True)
    log_widget.tag_configure("info", foreground="#a6e3a1")
    log_widget.tag_configure("error", foreground="#f38ba8")

    main.columnconfigure(0, weight=1)
    main.rowconfigure(3, weight=1)

    root.mainloop()


if __name__ == "__main__":
    run_ui()
