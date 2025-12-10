
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import threading
import queue
import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.toast import ToastNotification
from ttkbootstrap.dialogs import Messagebox
import datetime

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
App_SIZE = "500x700"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- Logic Layer: Scraper ---
class SpacebarScraper:
    def __init__(self, msg_queue):
        self.msg_queue = msg_queue
        self.stop_event = threading.Event()

    def log(self, message):
        self.msg_queue.put(("LOG", message))

    def progress(self, value, maximum=None):
        self.msg_queue.put(("PROGRESS", (value, maximum)))
    
    def status_update(self, message):
        self.msg_queue.put(("STATUS", message))

    def done(self, success, summary):
        self.msg_queue.put(("DONE", (success, summary)))

    def get_normal_news_links(self, soup):
        # Remove highlight block to avoid duplicates if necessary
        highlight_header = soup.find("h2", string="เรื่องเด่นประจำวัน")
        if highlight_header:
            highlight_block = highlight_header.find_parent("div", class_="w-full")
            if highlight_block:
                highlight_block.decompose()
        # Find all article links
        news_links = soup.find_all("a", attrs={"aria-label": ["articleLink", "latestArticleLink"]})
        return news_links

    def run(self, category, start_page, end_page, csv_path):
        base_url = "https://spacebar.th"
        articles = []
        seen_urls = set()
        total_scraped = 0
        page = start_page
        
        self.log(f"--- เริ่มต้นดึงข้อมูล: {category} (หน้า {start_page} - {end_page if end_page > 0 else 'จนจบ'}) ---")
        
        try:
            with requests.Session() as session:
                session.headers.update(HEADERS)
                
                while not self.stop_event.is_set():
                    # Check end condition
                    if end_page != 0 and page > end_page:
                        break

                    # Update Status
                    progress_text = f"正在 processing Page {page}..." # Thai text issues in some consoles, using EN for debug safety, change back to Thai in final
                    self.status_update(f"กำลังประมวลผลหน้าที่ {page}...")
                    
                    # Update Progress Bar (Page based)
                    if end_page != 0:
                        self.progress(page - start_page, end_page - start_page + 1)
                    else:
                        self.progress(0, 0) # Indeterminate

                    # Construct URL
                    if page == 1:
                        category_url = f"{base_url}/category/{category}"
                    else:
                        category_url = f"{base_url}/category/{category}/page/{page}"
                    
                    self.log(f"Loading Page: {category_url}")

                    try:
                        resp = session.get(category_url, timeout=15)
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
                            news_url = link.get("href", "")
                            if news_url.startswith("/"):
                                news_url = base_url + news_url
                            
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
            if articles:
                df = pd.DataFrame(articles)
                df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                msg = f"Saved successfully: {csv_path}\nTotal Articles: {total_scraped}"
                self.log(">>> " + msg.replace("\n", " "))
                self.done(True, msg)
            else:
                msg = "No articles found."
                self.log(msg)
                self.done(False, msg)

        except Exception as e:
            self.log(f"[CRITICAL ERROR] {e}")
            self.done(False, f"Critical Error: {e}")

# --- Presentation Layer: GUI (Material Design) ---
class SpacebarGUI:
    def __init__(self):
        # Initialize Window with Material Theme
        # available themes: cosmo, flatly, journal, lumen, minty, pulse, sand, united, yeti, morph, simplex, cerculean
        # dark themes: solar, superhero, cyborg, darkly
        # Switching to 'flatly' as 'materia' caused issues on some systems
        self.root = ttk.Window(themename="flatly", title=APP_TITLE, size=(550, 750))
        self.root.place_window_center()
        
        self.msg_queue = queue.Queue()
        self.scraper_thread = None
        self.scraper = None

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

        # Theme Toggle
        theme_frame = ttk.Frame(main_frame)
        theme_frame.pack(fill=X, pady=(0, 10))
        self.chk_dark = ttk.Checkbutton(theme_frame, text="Dark Mode", bootstyle="round-toggle", command=self.toggle_theme)
        self.chk_dark.pack(anchor=E)

        # --- Status & Log ---
        self.lbl_status = ttk.Label(main_frame, text="Ready to scrape", font=("Segoe UI", 9), bootstyle="secondary")
        self.lbl_status.pack(anchor=W)

        self.progress = ttk.Floodgauge(main_frame, bootstyle="success", font=("Segoe UI", 8), mask="{}%", value=0, maximum=100)
        self.progress.pack(fill=X, pady=(5, 10))

        ttk.Label(main_frame, text="System Log", font=("Segoe UI", 9, "bold")).pack(anchor=W)
        
        # Log Text
        self.log_text = ttk.ScrolledText(main_frame, height=10, state="disabled", font=("Consolas", 9))
        self.log_text.pack(fill=BOTH, expand=YES)

    def browse_file(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")], initialfile="spacebar_news.csv")
        if filename:
            self.path_var.set(filename)

    def toggle_theme(self):
        # Toggle between Flatly (Light) and Superhero (Dark)
        current = self.root.style.theme.name
        new_theme = "superhero" if "flatly" in current else "flatly"
        self.root.style.theme_use(new_theme)

    def append_log(self, text):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {text}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def lock_ui(self, locked):
        state = "disabled" if locked else "normal"
        readonly = "disabled" if locked else "readonly"
        
        self.entry_start.configure(state=state)
        self.entry_end.configure(state=state)
        self.entry_path.configure(state=state)
        self.cb_category.configure(state=readonly)
        self.btn_start.configure(state=state)
        self.btn_stop.configure(state="normal" if locked else "disabled")

    def start_task(self):
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

    def stop_task(self):
        if self.scraper:
            self.scraper.stop_event.set()
            self.append_log(">>> Stopping... please wait")
            self.btn_stop.configure(state="disabled")

    def monitor_queue(self):
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
