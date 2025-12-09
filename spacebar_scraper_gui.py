
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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
App_SIZE = "500x650"
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
                    progress_text = f"กำลังดึงรายการข่าว หน้าที่ {page}..."
                    self.status_update(progress_text)
                    
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
                    
                    self.log(f"กำลังโหลดหน้ารวมข่าว: {category_url}")

                    try:
                        resp = session.get(category_url, timeout=15)
                        resp.raise_for_status()
                    except Exception as e:
                        self.log(f"[Error] ขัดข้องในการโหลดหน้า {page}: {e}")
                        time.sleep(2)
                        page += 1
                        continue

                    resp.encoding = "utf-8"
                    soup = BeautifulSoup(resp.text, "html.parser")
                    news_links = self.get_normal_news_links(soup)

                    if not news_links:
                        self.log(f"[Info] ไม่พบข่าวเพิ่มเติมที่หน้า {page}. จบการทำงาน.")
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
                                self.log(f"  [Skip] โหลดเนื้อหาข่าวไม่ได้: {news_url} ({e})")
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

                    self.log(f"[สรุป] หน้า {page}: ได้ข่าวใหม่ {found_this_page} ข่าว")
                    
                    if found_this_page == 0:
                        self.log(f"[Info] ไม่พบข่าวใหม่ที่ตรงเงื่อนไขในหน้า {page}. อาจสิ้นสุดแล้ว")
                        break

                    page += 1

            # Save to CSV
            if articles:
                df = pd.DataFrame(articles)
                df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                msg = f"บันทึกไฟล์สำเร็จ: {csv_path}\nจำนวนข่าวทั้งหมด: {total_scraped}"
                self.log(">>> " + msg.replace("\n", " "))
                self.done(True, msg)
            else:
                msg = "ไม่พบข้อมูลข่าวเลย"
                self.log(msg)
                self.done(False, msg)

        except Exception as e:
            self.log(f"[CRITICAL ERROR] {e}")
            self.done(False, f"เกิดข้อผิดพลาดร้ายแรง: {e}")

# --- Presentation Layer: GUI ---
class SpacebarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(App_SIZE)
        # self.root.resizable(False, False) # Allow resizing slightly for better UX

        self.msg_queue = queue.Queue()
        self.scraper_thread = None
        self.scraper = None

        self.setup_styles()
        self.build_ui()
        
        # Start queue monitor
        self.root.after(100, self.monitor_queue)

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam') # Clean base theme

        # Define Colors
        self.colors = {
            'bg_light': '#F8F9FA', 'fg_light': '#212529',
            'bg_dark': '#212529', 'fg_dark': '#F8F9FA',
            'accent': '#0D6EFD', 'accent_hover': '#0B5ED7',
            'card_light': '#FFFFFF', 'card_dark': '#2C3034',
            'input_bg_light': '#FFFFFF', 'input_bg_dark': '#343A40'
        }
        
        # Initial Light Mode
        self.is_dark = False
        self.apply_theme()

    def apply_theme(self):
        bg = self.colors['bg_dark'] if self.is_dark else self.colors['bg_light']
        fg = self.colors['fg_dark'] if self.is_dark else self.colors['fg_light']
        card_bg = self.colors['card_dark'] if self.is_dark else self.colors['card_light']
        input_bg = self.colors['input_bg_dark'] if self.is_dark else self.colors['input_bg_light']
        
        self.root.configure(bg=bg)
        
        # Configure TTK Styles
        self.style.configure("TFrame", background=bg)
        self.style.configure("Card.TFrame", background=card_bg, relief="flat", borderwidth=0)
        
        self.style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), background=bg, foreground=self.colors['accent'])
        self.style.configure("SubLabel.TLabel", font=("Segoe UI", 8), background=card_bg, foreground="gray")
        self.style.configure("Card.TLabel", background=card_bg, foreground=fg, font=("Segoe UI", 10))
        
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6, background=self.colors['accent'], foreground="white", borderwidth=0)
        self.style.map("TButton", background=[('active', self.colors['accent_hover'])])
        self.style.configure("Stop.TButton", background="#DC3545")
        self.style.map("Stop.TButton", background=[('active', '#BB2D3B')])

        self.style.configure("TEntry", fieldbackground=input_bg, foreground=fg, padding=5)
        self.style.configure("TCombobox", fieldbackground=input_bg, background=input_bg, foreground=fg, padding=5)
        
        # Checkbutton
        self.style.configure("TCheckbutton", background=bg, foreground=fg, font=("Segoe UI", 9))

        # Helper for Log widget
        if hasattr(self, 'log_text'):
            self.log_text.config(bg=card_bg, fg=fg, insertbackground=fg)

    def build_ui(self):
        # Main Container with Padding
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Header
        header_lbl = ttk.Label(main_frame, text="Spacebar News Extractor", style="Header.TLabel")
        header_lbl.pack(anchor="w", pady=(0, 15))

        # --- Settings Card ---
        settings_frame = ttk.Frame(main_frame, style="Card.TFrame", padding=15)
        settings_frame.pack(fill="x", pady=(0, 10))

        # Category
        ttk.Label(settings_frame, text="หมวดหมู่ข่าว (Category)", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=5)
        self.category_var = tk.StringVar(value=list(CATEGORIES.keys())[0])
        self.cb_category = ttk.Combobox(settings_frame, textvariable=self.category_var, values=list(CATEGORIES.keys()), state="readonly")
        self.cb_category.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        # Pages
        page_frame = ttk.Frame(settings_frame, style="Card.TFrame")
        page_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10)
        
        ttk.Label(page_frame, text="เริ่มหน้า:", style="Card.TLabel").pack(side="left")
        self.entry_start = ttk.Entry(page_frame, width=5, justify="center")
        self.entry_start.insert(0, "1")
        self.entry_start.pack(side="left", padx=5)

        ttk.Label(page_frame, text="ถึงหน้า:", style="Card.TLabel").pack(side="left", padx=(15, 0))
        self.entry_end = ttk.Entry(page_frame, width=5, justify="center")
        self.entry_end.insert(0, "1")
        self.entry_end.pack(side="left", padx=5)
        
        ttk.Label(page_frame, text="(ใส่ 0 หากต้องการดึงจนจบ)", style="SubLabel.TLabel").pack(side="left", padx=5)

        # File Path
        ttk.Label(settings_frame, text="บันทึกไฟล์ (Save as)", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=5)
        file_frame = ttk.Frame(settings_frame, style="Card.TFrame")
        file_frame.grid(row=2, column=1, sticky="ew", padx=(10, 0))
        
        self.path_var = tk.StringVar(value="spacebar_news.csv")
        self.entry_path = ttk.Entry(file_frame, textvariable=self.path_var)
        self.entry_path.pack(side="left", fill="x", expand=True)
        ttk.Button(file_frame, text="Browse", width=6, command=self.browse_file).pack(side="left", padx=(5, 0))

        settings_frame.columnconfigure(1, weight=1)

        # --- Action Area ---
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill="x", pady=10)

        self.btn_start = ttk.Button(action_frame, text="Start Scraping", command=self.start_task)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_stop = ttk.Button(action_frame, text="Stop", command=self.stop_task, style="Stop.TButton", state="disabled")
        self.btn_stop.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # Dark Mode Toggle
        self.dark_var = tk.BooleanVar(value=False)
        self.chk_dark = ttk.Checkbutton(main_frame, text="Dark Mode / โหมดมืด", variable=self.dark_var, command=self.toggle_dark_mode, style="TCheckbutton")
        self.chk_dark.pack(anchor="e", pady=(0, 10))

        # --- Status & Log ---
        self.lbl_status = ttk.Label(main_frame, text="Ready", font=("Segoe UI", 9))
        self.lbl_status.pack(anchor="w")

        self.progress = ttk.Progressbar(main_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(5, 10))

        ttk.Label(main_frame, text="System Log:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        
        # Log Text with Scrollbar
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill="both", expand=True)
        
        self.log_text = tk.Text(log_frame, height=10, state="disabled", font=("Consolas", 9), relief="flat", padx=10, pady=10)
        self.log_text.pack(side="left", fill="both", expand=True)
        
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scroll.set)

    def browse_file(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")], initialfile="spacebar_news.csv")
        if filename:
            self.path_var.set(filename)

    def toggle_dark_mode(self):
        self.is_dark = self.dark_var.get()
        self.apply_theme()

    def append_log(self, text):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {text}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def lock_ui(self, locked):
        state = "disabled" if locked else "normal"
        readonly = "disabled" if locked else "readonly"
        
        self.entry_start.config(state=state)
        self.entry_end.config(state=state)
        self.entry_path.config(state=state)
        self.cb_category.config(state=readonly)
        self.btn_start.config(state=state)
        self.btn_stop.config(state="normal" if locked else "disabled")

    def start_task(self):
        # Validation
        try:
            start = int(self.entry_start.get())
            end = int(self.entry_end.get())
            if start < 1: raise ValueError("Start Page must be >= 1")
            if end != 0 and end < start: raise ValueError("End Page must be >= Start Page (or 0)")
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
            return

        csv_path = self.path_var.get()
        if not csv_path:
            messagebox.showerror("Error", "Please specify a CSV file path.")
            return

        cat_name = self.category_var.get()
        cat_slug = CATEGORIES.get(cat_name, "politics")

        # Prepare UI
        self.lock_ui(True)
        self.progress['value'] = 0
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")
        
        # Init Scraper
        self.scraper = SpacebarScraper(self.msg_queue)
        self.scraper_thread = threading.Thread(target=self.scraper.run, args=(cat_slug, start, end, csv_path), daemon=True)
        self.scraper_thread.start()

    def stop_task(self):
        if self.scraper:
            self.scraper.stop_event.set()
            self.append_log(">>> กำลังหยุดการทำงาน... กรุณารอสักครู่")
            self.btn_stop.config(state="disabled")

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
                        self.progress.config(mode="determinate", maximum=maximum, value=val)
                    else:
                        self.progress.config(mode="indeterminate")
                        self.progress.start(10)
                elif msg_type == "DONE":
                    success, summary = data
                    self.lock_ui(False)
                    self.progress.stop()
                    self.progress['value'] = 100
                    self.lbl_status.config(text="เสร็จสิ้น" if success else "หยุด/เกิดข้อผิดพลาด")
                    messagebox.showinfo("Result", summary)
                    
                self.msg_queue.task_done()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.monitor_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = SpacebarGUI(root)
    root.mainloop()
