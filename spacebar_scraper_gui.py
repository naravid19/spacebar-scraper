
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import threading
import queue
import time
import datetime
from urllib.parse import urljoin
from typing import List, Dict, Set, Optional, Tuple, Any

import requests
from bs4 import BeautifulSoup
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.toast import ToastNotification
from ttkbootstrap.dialogs import Messagebox

# --- Constants & Configuration ---
CATEGORIES = {
    "การเมือง (Politics)": "politics",
    "ธุรกิจ (Business)": "business",
    "สังคม (Social)": "social",
    "โลก (World)": "world",
    "วัฒนธรรม (Culture)": "culture",
    "ไลฟ์สไตล์ (Lifestyle)": "lifestyle",
    "กีฬา (Sport)": "sport",
    "Deep Space (บทความพิเศษ)": "deep-space"
}

APP_TITLE = "Spacebar News Scraper Pro"
APP_SIZE = (580, 780)  # Slightly larger for better spacing
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- Logic Layer: Scraper ---
class SpacebarScraper:
    """
    Business Logic Layer: Handles the web scraping process.
    """
    def __init__(self, msg_queue: queue.Queue):
        self.msg_queue = msg_queue
        self.stop_event = threading.Event()

    def log(self, message: str) -> None:
        """Sends a log message to the GUI."""
        self.msg_queue.put(("LOG", message))

    def progress(self, value: int, maximum: Optional[int] = None) -> None:
        """Sends a progress update to the GUI."""
        self.msg_queue.put(("PROGRESS", (value, maximum)))
    
    def status_update(self, message: str) -> None:
        """Sends a status label update to the GUI."""
        self.msg_queue.put(("STATUS", message))

    def done(self, success: bool, summary: str) -> None:
        """Signals completion or failure."""
        self.msg_queue.put(("DONE", (success, summary)))

    def get_normal_news_links(self, soup: BeautifulSoup) -> List[Any]:
        """Extracts standard article links from the soup object, avoiding highlights if needed."""
        # Remove highlight block to avoid duplicates if necessary
        highlight_header = soup.find("h2", string="เรื่องเด่นประจำวัน")
        if highlight_header:
            highlight_block = highlight_header.find_parent("div", class_="w-full")
            if highlight_block:
                highlight_block.decompose()
        # Find all article links
        news_links = soup.find_all("a", attrs={"aria-label": ["articleLink", "latestArticleLink"]})
        return news_links

    def run(self, category: str, start_page: int, end_page: int, csv_path: str) -> None:
        """
        Main scraping loop.
        
        Args:
            category: The category slug to scrape.
            start_page: Page number to start from.
            end_page: Page number to end at (0 for until end).
            csv_path: File path to save the CSV.
        """
        base_url = "https://spacebar.th"
        articles: List[Dict[str, str]] = []
        seen_urls: Set[str] = set()
        total_scraped = 0
        page = start_page
        start_time = time.time()
        
        self.log(f"--- เริ่มต้นดึงข้อมูล: {category} (หน้า {start_page} - {end_page if end_page > 0 else 'จนจบ'}) ---")
        
        try:
            with requests.Session() as session:
                session.headers.update(HEADERS)
                
                while not self.stop_event.is_set():
                    # Check end condition
                    if end_page != 0 and page > end_page:
                        break

                    # Update Status
                    self.status_update(f"กำลังประมวลผลหน้าที่ {page}...")
                    
                    # Update Progress Bar (Page based)
                    if end_page != 0:
                        self.progress(page - start_page, end_page - start_page + 1)
                    else:
                        self.progress(0, 0) # Indeterminate mode

                    # Construct URL safely
                    if page == 1:
                        category_url = urljoin(base_url, f"/category/{category}")
                    else:
                        category_url = urljoin(base_url, f"/category/{category}/page/{page}")
                    
                    self.log(f"Loading Page: {category_url}")

                    try:
                        resp = session.get(category_url, timeout=20)
                        resp.raise_for_status()
                    except Exception as e:
                        self.log(f"[Error] Failed page {page}: {e}")
                        time.sleep(2)
                        page += 1
                        continue

                    resp.encoding = "utf-8"
                    soup = BeautifulSoup(resp.text, "html.parser")
                    news_links = self.get_normal_news_links(soup)

                    if not news_links:
                        self.log(f"[Info] No more news at page {page}. Stopping.")
                        break

                    found_this_page = 0
                    
                    # Process each news link
                    for idx, link in enumerate(news_links, start=1):
                        if self.stop_event.is_set():
                            break

                        try:
                            # 1. Extract Headline from listing
                            headline_div = link.find("div", class_="w-full text-base font-semibold text-gray-700 hover:text-accentual-blue-main mb-2 line-clamp-3")
                            if headline_div:
                                headline = headline_div.get_text(strip=True)
                            else:
                                headline_tag = link.find("h3")
                                headline = headline_tag.get_text(strip=True) if headline_tag else "No Headline"

                            # 2. Extract URL
                            raw_url = link.get("href", "")
                            news_url = urljoin(base_url, raw_url)
                            
                            # Filter
                            if f"/{category}/" not in news_url and not news_url.endswith(f"/{category}"):
                                continue
                            if news_url in seen_urls:
                                continue
                            
                            seen_urls.add(news_url)

                            # 3. Enter News Page
                            try:
                                news_resp = session.get(news_url, timeout=15)
                                news_resp.raise_for_status()
                            except Exception as e:
                                self.log(f"  [Skip] Content load failed: {news_url} ({e})")
                                continue

                            news_resp.encoding = "utf-8"
                            news_soup = BeautifulSoup(news_resp.text, "html.parser")

                            # Title
                            title_tag = news_soup.find("h1", class_="article-title")
                            title = title_tag.get_text(strip=True) if title_tag else headline

                            # Date
                            date_tag = news_soup.find("p", class_="text-gray-400 text-subheadsm mb-4 md:mb-0")
                            date = date_tag.get_text(strip=True) if date_tag else "-"

                            # Content
                            content_div = news_soup.find("div", class_="payload-richtext")
                            content = ""
                            if content_div:
                                # Extract text with newlines for readability
                                content_parts = []
                                for tag in content_div.find_all(['p', 'li', 'blockquote', 'h2', 'h3']):
                                    text = tag.get_text(strip=True)
                                    if text:
                                        content_parts.append(text)
                                content = "\n\n".join(content_parts)
                            
                            # Add to list
                            articles.append({
                                "หัวข้อ": title,
                                "เนื้อหา": content,
                                "วันที่": date,
                                "URL": news_url,
                            })

                            found_this_page += 1
                            total_scraped += 1
                            self.log(f"  + [{total_scraped}] {title[:40]}... | {date}")
                            
                            # Politeness delay
                            time.sleep(0.5)

                        except Exception as inner_e:
                            self.log(f"  [Error] Parsing item {idx}: {inner_e}")

                    self.log(f"[Summary] Page {page}: Found {found_this_page} new articles")
                    
                    if found_this_page == 0:
                        self.log(f"[Info] No items matched criteria on page {page}.")
                        break

                    page += 1

            # Save to CSV
            elapsed = time.time() - start_time
            if articles:
                df = pd.DataFrame(articles)
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(csv_path)) or ".", exist_ok=True)
                
                df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                msg = f"Saved successfully: {csv_path}\nTotal Articles: {total_scraped}\nTime: {elapsed:.2f}s"
                self.log(">>> " + msg.replace("\n", " | "))
                self.done(True, msg)
            else:
                msg = f"No articles found.\nTime: {elapsed:.2f}s"
                self.log(msg)
                self.done(False, msg)

        except Exception as e:
            self.log(f"[CRITICAL ERROR] {e}")
            self.done(False, f"Critical Error: {e}")

# --- Presentation Layer: GUI (Material Design) ---
class SpacebarGUI:
    """
    Presentation Layer: Controls the GUI and Interaction.
    """
    def __init__(self):
        # Initialize Window with Material Theme
        self.root = ttk.Window(themename="flatly", title=APP_TITLE, size=APP_SIZE)
        self.root.place_window_center()
        self.root.minsize(580, 780)
        
        self.msg_queue: queue.Queue = queue.Queue()
        self.scraper_thread: Optional[threading.Thread] = None
        self.scraper: Optional[SpacebarScraper] = None

        self.last_saved_path: Optional[str] = None

        self.build_ui()
        
        # Start queue monitor
        self.root.after(100, self.monitor_queue)
        self.root.mainloop()

    def build_ui(self):
        # Main Container
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)

        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=X, pady=(0, 20))
        
        ttk.Label(header_frame, text="Spacebar News Scraper", font=("Roboto", 20, "bold"), bootstyle="primary").pack(side=LEFT)
        # Badge is not available in all versions, using inverse Label instead
        ttk.Label(header_frame, text=" PRO ", bootstyle="inverse-success", font=("Segoe UI", 9, "bold")).pack(side=LEFT, padx=10, pady=5)

        # --- Settings Card ---
        settings_frame = ttk.LabelFrame(main_frame, text=" Configuration ", padding=15, bootstyle="info")
        settings_frame.pack(fill=X, pady=(0, 15))

        # Category
        ttk.Label(settings_frame, text="หมวดหมู่ข่าว (Category)", font=("Segoe UI", 10)).pack(anchor=W, pady=(0, 5))
        self.category_var = tk.StringVar(value=list(CATEGORIES.keys())[0])
        self.cb_category = ttk.Combobox(settings_frame, textvariable=self.category_var, values=list(CATEGORIES.keys()), state="readonly", bootstyle="primary")
        self.cb_category.pack(fill=X, pady=(0, 10))

        # Pages Row
        page_frame = ttk.Frame(settings_frame)
        page_frame.pack(fill=X, pady=(0, 10))
        
        # Start Page
        start_group = ttk.Frame(page_frame)
        start_group.pack(side=LEFT, fill=X, expand=YES, padx=(0, 10))
        ttk.Label(start_group, text="เริ่มหน้า (Start)").pack(anchor=W)
        self.entry_start = ttk.Spinbox(start_group, from_=1, to=9999, bootstyle="secondary")
        self.entry_start.set("1")
        self.entry_start.pack(fill=X)

        # End Page
        end_group = ttk.Frame(page_frame)
        end_group.pack(side=LEFT, fill=X, expand=YES)
        ttk.Label(end_group, text="ถึงหน้า (End) [0=All]").pack(anchor=W)
        self.entry_end = ttk.Spinbox(end_group, from_=0, to=9999, bootstyle="secondary")
        self.entry_end.set("1")
        self.entry_end.pack(fill=X)

        # File Path
        ttk.Label(settings_frame, text="บันทึกไฟล์ (Save Path)").pack(anchor=W, pady=(0, 5))
        file_frame = ttk.Frame(settings_frame)
        file_frame.pack(fill=X)
        
        self.path_var = tk.StringVar(value="spacebar_news.csv")
        self.entry_path = ttk.Entry(file_frame, textvariable=self.path_var, bootstyle="secondary")
        self.entry_path.pack(side=LEFT, fill=X, expand=YES)
        ttk.Button(file_frame, text="📂", width=4, command=self.browse_file, bootstyle="outline-secondary").pack(side=LEFT, padx=(5, 0))

        # --- Actions ---
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=X, pady=10)

        self.btn_start = ttk.Button(action_frame, text="START SCRAPING", command=self.start_task, bootstyle="success", width=20)
        self.btn_start.pack(side=LEFT, fill=X, expand=YES, padx=(0, 5))

        self.btn_stop = ttk.Button(action_frame, text="STOP", command=self.stop_task, bootstyle="danger", state="disabled", width=10)
        self.btn_stop.pack(side=LEFT, fill=X, expand=NO, padx=(5, 0))

        # --- Utility Buttons ---
        util_frame = ttk.Frame(main_frame)
        util_frame.pack(fill=X, pady=(0, 10))
        
        # Theme Toggle
        self.chk_dark = ttk.Checkbutton(util_frame, text="Dark Mode", bootstyle="round-toggle", command=self.toggle_theme)
        self.chk_dark.pack(side=RIGHT)

        # Clear Log
        ttk.Button(util_frame, text="Clear Log", command=self.clear_log, bootstyle="outline-secondary", width=12).pack(side=LEFT, padx=(0, 5))
        
        # Open Folder (Initially disabled)
        self.btn_open_folder = ttk.Button(util_frame, text="Open Folder", command=self.open_output_folder, bootstyle="outline-info", state="disabled", width=12)
        self.btn_open_folder.pack(side=LEFT)

        # --- Status & Log ---
        self.lbl_status = ttk.Label(main_frame, text="Ready to scrape", font=("Segoe UI", 9), bootstyle="secondary")
        self.lbl_status.pack(anchor=W)

        self.progress = ttk.Floodgauge(main_frame, bootstyle="success", font=("Segoe UI", 8), mask="{}%", value=0, maximum=100)
        self.progress.pack(fill=X, pady=(5, 10))

        ttk.Label(main_frame, text="System Log", font=("Segoe UI", 9, "bold")).pack(anchor=W)
        
        # Log Text
        self.log_text = ttk.ScrolledText(main_frame, height=12, state="disabled", font=("Consolas", 9))
        self.log_text.pack(fill=BOTH, expand=YES)

    def browse_file(self) -> None:
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")], initialfile="spacebar_news.csv")
        if filename:
            self.path_var.set(filename)

    def toggle_theme(self) -> None:
        # Toggle between Flatly (Light) and Superhero (Dark)
        current = self.root.style.theme.name
        new_theme = "superhero" if "flatly" in current else "flatly"
        self.root.style.theme_use(new_theme)
    
    def clear_log(self) -> None:
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")

    def open_output_folder(self) -> None:
        if self.last_saved_path and os.path.exists(self.last_saved_path):
            folder_path = os.path.dirname(os.path.abspath(self.last_saved_path))
            os.startfile(folder_path)
        else:
            Messagebox.show_warning("Folder path not found or file not saved yet.", "Path Error")

    def append_log(self, text: str) -> None:
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {text}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def lock_ui(self, locked: bool) -> None:
        state = "disabled" if locked else "normal"
        readonly = "disabled" if locked else "readonly"
        
        self.entry_start.configure(state=state)
        self.entry_end.configure(state=state)
        self.entry_path.configure(state=state)
        self.cb_category.configure(state=readonly)
        self.btn_start.configure(state=state)
        self.btn_stop.configure(state="normal" if locked else "disabled")
        # Disable Open Folder while running to prevent confusion, re-enable if valid path exists later
        if locked:
           self.btn_open_folder.configure(state="disabled")

    def start_task(self) -> None:
        # Validation
        try:
            start = int(self.entry_start.get())
            end = int(self.entry_end.get())
            if start < 1: raise ValueError("Start Page must be >= 1")
            if end != 0 and end < start: raise ValueError("End Page must be >= Start Page (or 0)")
        except ValueError as e:
            Messagebox.show_error(str(e), "Invalid Input")
            return

        csv_path = self.path_var.get()
        if not csv_path:
            Messagebox.show_error("Please specify a CSV file path.", "Missing Path")
            return

        cat_name = self.category_var.get()
        cat_slug = CATEGORIES.get(cat_name, "politics")

        # Prepare UI
        self.lock_ui(True)
        self.progress.configure(value=0, maximum=100) # Reset
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state="disabled")
        
        # Init Scraper
        self.scraper = SpacebarScraper(self.msg_queue)
        self.scraper_thread = threading.Thread(target=self.scraper.run, args=(cat_slug, start, end, csv_path), daemon=True)
        self.scraper_thread.start()

    def stop_task(self) -> None:
        if self.scraper:
            self.scraper.stop_event.set()
            self.append_log(">>> Stopping... please wait")
            self.btn_stop.configure(state="disabled")

    def monitor_queue(self) -> None:
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                
                if msg_type == "LOG":
                    self.append_log(data)
                elif msg_type == "STATUS":
                    self.lbl_status.config(text=data)
                elif msg_type == "PROGRESS":
                    val, maximum = data
                    if maximum:
                        self.progress.configure(mode="determinate", maximum=maximum, value=val)
                    else:
                        self.progress.configure(mode="indeterminate")
                        self.progress.start(10)
                elif msg_type == "DONE":
                    success, summary = data
                    self.lock_ui(False)
                    self.progress.stop()
                    self.progress.configure(value=100)
                    self.lbl_status.config(text="Finished" if success else "Stopped/Error")
                    
                    if success:
                        self.last_saved_path = self.path_var.get()
                        self.btn_open_folder.configure(state="normal")
                        ToastNotification(title="Success", message=summary, bootstyle="success", duration=3000).show_toast()
                    else:
                        Messagebox.show_error(summary, "Error")
                    
                self.msg_queue.task_done()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.monitor_queue)

if __name__ == "__main__":
    app = SpacebarGUI()
