import customtkinter as ctk
from tkinter import filedialog, messagebox, Text, END
import configparser
import os
import webbrowser
from core.utils import logger
import threading
import asyncio
from core.utils.bot import Bot
from core.captcha import ServiceAnticaptcha, ServiceCapmonster, Service2Captcha
from PIL import Image, ImageTk
import csv

CONFIG_FILE = "data/settings.ini"

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("dark-blue")

class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NodePay Bot")
        self.root.geometry("900x700")
        # self.root.resizable(True, True)
        try:
            favicon = ImageTk.PhotoImage(Image.open("core/static/faviconV2.png"))
            self.root.iconphoto(True, favicon)
        except Exception as e:
            logger.error(f"Failed to load favicon: {e}")
        self.config = configparser.ConfigParser()
        self.load_settings()
        self.threads_entry = ctk.CTkEntry(self.root)
        self.captcha_service_var = ctk.StringVar(value="capmonster")
        self.captcha_api_entry = ctk.CTkEntry(self.root)
        self.ref_code_entry = ctk.CTkEntry(self.root)
        self.delay_min_entry = ctk.CTkEntry(self.root)
        self.delay_max_entry = ctk.CTkEntry(self.root)
        self.create_widgets()
        self.bot = None
        self.bot_thread = None
        self.running = False
        self.CaptchaService = None
    
    # Callback to check if it's updated correctly
    def on_captcha_service_change(self, value):
        logger.debug(f"Captcha service updated to: {value}")

    def create_widgets(self):
        self.root.configure(bg="#F1F3FF")
        self.main_frame = ctk.CTkFrame(self.root, fg_color="#F1F3FF")
        self.main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Header frame
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="#F1F3FF")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.header_frame.columnconfigure(0, weight=1)
        self.header_frame.columnconfigure(1, weight=0)
        self.header_frame.columnconfigure(2, weight=0)
        self.header_frame.columnconfigure(3, weight=0)  # Add this line for the new column

        # Logo and title
        self.logo_frame = ctk.CTkFrame(self.header_frame, fg_color="#F1F3FF")
        self.logo_frame.grid(row=0, column=0, sticky="w")

        try:
            self.logo_image = ctk.CTkImage(light_image=Image.open("core/static/logo.png"), size=(60, 60))
            self.logo_label = ctk.CTkLabel(self.logo_frame, image=self.logo_image, text="")
            self.logo_label.pack(side="left", padx=(0, 10))
        except Exception as e:
            logger.error(f"Failed to load logo: {e}")

        self.nodepay_label = ctk.CTkLabel(
            self.logo_frame,
            text="NodePay+",
            font=("Helvetica", 24, "bold"),
            fg_color="#F1F3FF"
        )
        self.nodepay_label.pack(side="left")

        # Watermark buttons
        button_style = {
            "fg_color": "#593FDE",
            "hover_color": "#452CC6",
            "corner_radius": 20,
            "border_width": 2,
            "border_color": "#FFFFFF",
            "text_color": "white",
            "font": ("Helvetica", 12)
        }

        self.instructions_button = ctk.CTkButton(
            self.header_frame,
            text="Instructions",
            command=lambda: self.open_link("https://teletype.in/@web3enjoyer/nodepay_plus"),
            **button_style
        )
        self.instructions_button.grid(row=0, column=1, padx=(0, 10), sticky="e")

        self.web3_products_button = ctk.CTkButton(
            self.header_frame,
            text="Web3 products",
            command=lambda: self.open_link("https://gemups.com/"),
            **button_style
        )
        self.web3_products_button.grid(row=0, column=2, padx=(0, 10), sticky="e")

        self.enjoyer_button = ctk.CTkButton(
            self.header_frame,
            text="Grass, Dawn, Gradient and more ...",
            command=lambda: self.open_link("https://t.me/web3_enjoyer_club"),
            **button_style
        )
        self.enjoyer_button.grid(row=0, column=3, padx=(0, 10), sticky="e")

        # Main content frame
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="#FFFFFF", corner_radius=20)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.columnconfigure(0, weight=1)

        # File selection frame
        self.file_frame = ctk.CTkFrame(self.content_frame, fg_color="#FFFFFF")
        self.file_frame.pack(fill="x", padx=20, pady=(20, 10))

        self.accounts_label, self.accounts_button = self.create_file_selection("Accounts File:", self.load_accounts_file)
        self.proxies_label, self.proxies_button = self.create_file_selection("Proxies File:", self.load_proxies_file)

        # Input frame
        self.input_frame = ctk.CTkFrame(self.content_frame, fg_color="#FFFFFF")
        self.input_frame.pack(fill="x", padx=20, pady=10)

        # Create a grid layout for input fields
        self.input_frame.columnconfigure(1, weight=1)
        self.input_frame.columnconfigure(3, weight=1)

        # Captcha and API Key on the same line
        self.captcha_label, self.captcha_menu = self.create_input_field("Captcha:", ctk.CTkOptionMenu(
            self.input_frame,
            variable=self.captcha_service_var,
            values=["capmonster","anticaptcha", "2captcha"],  # "2captcha", "anticaptcha", "capsolver",
            width=120,
            text_color="#000",
            command=self.on_captcha_service_change
        ))
        self.captcha_label.grid(row=0, column=0, sticky="w", pady=5, padx=(0, 5))
        self.captcha_menu.grid(row=0, column=1, sticky="w", pady=5)

        self.captcha_api_label, self.captcha_api_entry = self.create_input_field("API Key:", ctk.CTkEntry(self.input_frame, width=100))
        self.captcha_api_label.grid(row=0, column=2, sticky="w", pady=5, padx=(0, 5))
        self.captcha_api_entry.grid(row=0, column=3, sticky="ew", pady=5)

        # Threads and hidden Referral Code toggle on the same line
        self.threads_label, self.threads_entry = self.create_input_field("Threads:", ctk.CTkEntry(self.input_frame, width=60))
        self.threads_label.grid(row=1, column=0, sticky="w", pady=5)
        self.threads_entry.grid(row=1, column=1, sticky="w", pady=5)

        self.toggle_ref_code_button = ctk.CTkButton(
            self.input_frame,
            text="⋮",  # Vertical ellipsis character
            command=self.toggle_ref_code_visibility,
            width=5,
            height=5,
            corner_radius=25,
            fg_color="#FFFFFF",  # Changed to a very light color
            text_color="#A0A0A0",  # Changed to a light gray color
            hover_color="#E9E4FF",
            font=("Helvetica", 14, "bold")
        )
        self.toggle_ref_code_button.grid(row=1, column=1, sticky="e", pady=5, padx=(0, 5))

        self.ref_code_label, self.ref_code_entry = self.create_input_field("Referral Code:", ctk.CTkEntry(self.input_frame, width=100))
        self.ref_code_label.grid(row=1, column=2, sticky="w", pady=5, padx=(0, 10))
        self.ref_code_entry.grid(row=1, column=3, sticky="ew", pady=5)

        # Hide referral code input initially
        self.ref_code_label.grid_remove()
        self.ref_code_entry.grid_remove()

        # Add delay inputs after the threads input
        self.delay_label = ctk.CTkLabel(
            self.input_frame,
            text="Delay (seconds):",
            font=("Helvetica", 14),
            fg_color="#FFFFFF",
            text_color="#2E3A59"
        )
        self.delay_label.grid(row=2, column=0, sticky="w", pady=5, padx=(0, 5))

        self.delay_min_entry = ctk.CTkEntry(self.input_frame, width=60)
        self.delay_min_entry.grid(row=2, column=1, sticky="w", pady=5)

        self.delay_to_label = ctk.CTkLabel(
            self.input_frame,
            text="to",
            font=("Helvetica", 14),
            fg_color="#FFFFFF",
            text_color="#2E3A59"
        )
        self.delay_to_label.grid(row=2, column=1, sticky="w", pady=5, padx=(65, 0))

        self.delay_max_entry = ctk.CTkEntry(self.input_frame, width=60)
        self.delay_max_entry.grid(row=2, column=1, sticky="w", pady=5, padx=(90, 0))

        # Buttons frame
        self.buttons_frame = ctk.CTkFrame(self.content_frame, fg_color="#FFFFFF")
        self.buttons_frame.pack(fill="x", padx=20, pady=(10, 20))

        main_button_style = {
            "fg_color": "#4A55A2",
            "hover_color": "#3D478F",
            "corner_radius": 10,
            "border_width": 0,
            "font": ("Helvetica", 14, "bold"),
            "text_color": "white"
        }

        earnings_button_style = {
            "fg_color": "#E9E4FF",  # Light purple background
            "hover_color": "#D6D6F5",  # Slightly darker on hover
            "corner_radius": 8,
            "border_width": 1,
            "border_color": "#593FDE",  # Purple border
            "font": ("Helvetica", 12),  # Smaller font
            "text_color": "#593FDE",  # Purple text
            "width": 100,  # Fixed width
            "height": 28  # Smaller height
        }

        self.register_button = ctk.CTkButton(
            self.buttons_frame,
            text="Register Accounts",
            command=self.register_accounts,
            **main_button_style
        )
        self.register_button.pack(side="left", padx=(0, 10), expand=True, fill="x")

        self.mining_button = ctk.CTkButton(
            self.buttons_frame,
            text="Start Farm",
            command=self.start_mining,
            **main_button_style
        )
        self.mining_button.pack(side="left", padx=(0, 10), expand=True, fill="x")

        self.stop_button = ctk.CTkButton(
            self.buttons_frame,
            text="Stop Bot",
            command=self.stop_bot,
            **main_button_style
        )
        self.stop_button.pack(side="left", padx=(0, 10), expand=True, fill="x")

        # Add View Earnings button with different style
        self.view_earnings_button = ctk.CTkButton(
            self.buttons_frame,
            text="View Earnings",
            command=self.view_earnings,
            **earnings_button_style
        )
        self.view_earnings_button.pack(side="left", expand=False)  # Changed to expand=False

        # Log frame
        self.log_frame = ctk.CTkFrame(self.content_frame, fg_color="#FFFFFF")
        self.log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.log_box = Text(
            self.log_frame,
            wrap="word",
            bg="#F8F9FA",
            fg="#2E3A59",
            font=("Consolas", 12),
            relief="flat",
            borderwidth=0,
            highlightthickness=0
        )
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

        # Apply styles
        self.beautify_ui()

        # Load saved values
        self.load_values()

    def create_file_selection(self, label_text, command):
        frame = ctk.CTkFrame(self.file_frame, fg_color="#FFFFFF")
        frame.pack(fill="x", pady=5)

        label = ctk.CTkLabel(
            frame,
            text=label_text,
            font=("Helvetica", 14),
            fg_color="#FFFFFF"
        )
        label.pack(side="left")

        button = ctk.CTkButton(
            frame,
            text="Select File",
            command=command,
            fg_color="#E9E4FF",
            text_color="#2E3A59",
            hover_color="#D6D6F5",
            corner_radius=10,
            width=200,
            font=("Helvetica", 14)
        )
        button.pack(side="right")

        return label, button

    def create_input_field(self, label_text, widget):
        label = ctk.CTkLabel(
            self.input_frame,
            text=label_text,
            font=("Helvetica", 14),
            fg_color="#FFFFFF",
            text_color="#2E3A59"
        )

        if isinstance(widget, ctk.CTkEntry):
            widget.configure(
                height=30,
                font=("Helvetica", 14),
                fg_color="#FFFFFF",
                border_color="#4A55A2",
                border_width=1,
                corner_radius=5
            )
        elif isinstance(widget, ctk.CTkOptionMenu):
            widget.configure(
                height=30,
                font=("Helvetica", 14),
                fg_color="#FFFFFF",
                button_color="#4A55A2",
                button_hover_color="#3D478F",
                dropdown_fg_color="#FFFFFF",
                dropdown_hover_color="#E9E4FF",
                corner_radius=5
            )

        return label, widget

    def open_link(self, url):
        webbrowser.open(url)

    def on_mousewheel(self, event):
        if os.name == 'nt':
            self.log_box.yview_scroll(int(-1*(event.delta/120)), "units")
        elif event.num == 4:
            self.log_box.yview_scroll(-1, "units")
        elif event.num == 5:
            self.log_box.yview_scroll(1, "units")

    def load_accounts_file(self):
        file_path = filedialog.askopenfilename(title="Select Accounts File")
        if file_path:
            self.accounts_path = file_path
            filename = os.path.basename(file_path)
            self.accounts_button.configure(text=filename)

    def load_proxies_file(self):
        file_path = filedialog.askopenfilename(title="Select Proxies File")
        if file_path:
            self.proxies_path = file_path
            filename = os.path.basename(file_path)
            self.proxies_button.configure(text=filename)

    def save_settings(self):
        ref_codes = [code.strip() for code in self.ref_code_entry.get().split(',') if code.strip()]
        self.config['DEFAULT'] = {
            'AccountsFile': getattr(self, 'accounts_path', ''),
            'ProxiesFile': getattr(self, 'proxies_path', ''),
            'ReferralCodes': ','.join(ref_codes),
            'Threads': self.threads_entry.get(),
            'CaptchaService': self.captcha_service_var.get(),
            'CaptchaAPIKey': self.captcha_api_entry.get(),
            'DelayMin': self.delay_min_entry.get(),
            'DelayMax': self.delay_max_entry.get()
        }
        with open(CONFIG_FILE, 'w') as configfile:
            self.config.write(configfile)

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            self.config.read(CONFIG_FILE)
        else:
            self.config['DEFAULT'] = {
                'AccountsFile': '',
                'ProxiesFile': '',
                'ReferralCodes': '',
                'Threads': '5',
                'CaptchaService': 'capmonster',
                'CaptchaAPIKey': '',
                'DelayMin': '1',
                'DelayMax': '2'
            }

    def load_values(self):
        accounts = self.config['DEFAULT'].get('AccountsFile', '')
        proxies = self.config['DEFAULT'].get('ProxiesFile', '')
        self.accounts_path = accounts
        self.proxies_path = proxies

        ref_codes = self.config['DEFAULT'].get('ReferralCodes', '')
        self.ref_code_entry.delete(0, 'end')
        self.ref_code_entry.insert(0, ref_codes)
        threads = self.config['DEFAULT'].get('Threads', '5')
        self.threads_entry.insert(0, threads)
        self.captcha_service_var.set(self.config['DEFAULT'].get('CaptchaService', 'capmonster'))
        self.captcha_api_entry.insert(0, self.config['DEFAULT'].get('CaptchaAPIKey', ''))
        self.delay_min_entry.insert(0, self.config['DEFAULT'].get('DelayMin', '1'))
        self.delay_max_entry.insert(0, self.config['DEFAULT'].get('DelayMax', '2'))

        if self.accounts_path:
            accounts_filename = os.path.basename(self.accounts_path)
            self.accounts_button.configure(text=accounts_filename)
        if self.proxies_path:
            proxies_filename = os.path.basename(self.proxies_path)
            self.proxies_button.configure(text=proxies_filename)

    def setup_logger(self):
        logger.remove()
        
        # Configure text styles with bigger font and colors
        self.log_box.tag_configure("INFO", foreground="black", font=("Consolas", 14))
        self.log_box.tag_configure("ERROR", foreground="red", font=("Consolas", 14, "bold"))
        self.log_box.tag_configure("WARNING", foreground="orange", font=("Consolas", 14))
        self.log_box.tag_configure("DEBUG", foreground="purple", font=("Consolas", 14))
        self.log_box.tag_configure("SUCCESS", foreground="green", font=("Consolas", 14, "bold"))

        def gui_log_sink(message):
            log_text = message.strip()
            level = message.record["level"].name
            if level == "INFO":
                tag = "INFO"
            elif level == "ERROR":
                tag = "ERROR"
            elif level == "WARNING":
                tag = "WARNING"
            elif level == "DEBUG":
                tag = "DEBUG"
            elif level == "SUCCESS":
                tag = "SUCCESS"
            else:
                tag = "INFO"
            self.root.after(0, self.append_log, log_text, tag)

        logger.add(gui_log_sink, format="{time} {level} {message}", level="DEBUG")

    def append_log(self, log_text, tag):
        self.log_box.configure(state="normal")
        self.log_box.insert(END, log_text + "\n", tag)
        self.log_box.configure(state="disabled")
        self.log_box.see(END)

    def register_accounts(self):
        captcha_service_var = self.captcha_service_var.get()
        if captcha_service_var == 'anticaptcha':
            self.CaptchaService = ServiceAnticaptcha
        elif captcha_service_var == 'capmonster':
            self.CaptchaService = ServiceCapmonster
        elif captcha_service_var == '2captcha':
            self.CaptchaService = Service2Captcha
        if not self.validate_inputs():
            return
        self.save_settings()
        if not self.running:
            ref_codes = [code.strip() for code in self.ref_code_entry.get().split(',') if code.strip()]
            delay_min = float(self.delay_min_entry.get())
            delay_max = float(self.delay_max_entry.get())
            self.bot = Bot(
                account_path=self.accounts_path,
                proxy_path=self.proxies_path,
                threads=int(self.threads_entry.get()),
                ref_codes=ref_codes,
                captcha_service=self.CaptchaService(api_key=self.captcha_api_entry.get()),
                delay_range=(delay_min, delay_max))
            self.bot_thread = threading.Thread(target=asyncio.run, args=(self.bot.start_registration(),), daemon=True)
            self.bot_thread.start()
            self.running = True
            logger.info("Started account registration with slow start.")

    def start_mining(self):
        captcha_service_var = self.captcha_service_var.get()
        if captcha_service_var == 'anticaptcha':
            self.CaptchaService = ServiceAnticaptcha
        elif captcha_service_var == 'capmonster':
            self.CaptchaService = ServiceCapmonster
        elif captcha_service_var == '2captcha':
            self.CaptchaService = Service2Captcha
        if not self.validate_inputs():
            return
        self.save_settings()
        if not self.running:
            ref_codes = [code.strip() for code in self.ref_code_entry.get().split(',') if code.strip()]
            delay_min = float(self.delay_min_entry.get())
            delay_max = float(self.delay_max_entry.get())
            self.bot = Bot(
                account_path=self.accounts_path,
                proxy_path=self.proxies_path,
                threads=int(self.threads_entry.get()),
                ref_codes=ref_codes,
                captcha_service=self.CaptchaService(api_key=self.captcha_api_entry.get()),
                delay_range=(delay_min, delay_max)
            )
            self.bot_thread = threading.Thread(target=asyncio.run, args=(self.bot.start_mining(),), daemon=True)
            self.bot_thread.start()
            self.running = True

    def stop_bot(self):
        if self.running and self.bot:
            self.bot.stop()
            self.running = False
            logger.info("Bot stopped.")
            if self.bot_thread:
                self.bot_thread.join(timeout=1)  # Wait for the thread to finish
                # if self.bot_thread.is_alive():
                #     logger.warning("Bot thread did not stop in time.")
        else:
            logger.warning("Bot is not running.")

    def validate_inputs(self):
        if not getattr(self, 'accounts_path', ''):
            logger.error("Error: Accounts file not selected!")
            messagebox.showerror("Error", "Accounts file not selected!")
            return False
        if not getattr(self, 'proxies_path', ''):
            logger.error("Error: Proxies file not selected!")
            messagebox.showerror("Error", "Proxies file not selected!")
            return False
        if not self.captcha_api_entry.get():
            logger.error("Error: Captcha API key is missing!")
            messagebox.showerror("Error", "Captcha API key is missing!")
            return False
        try:
            threads = int(self.threads_entry.get())
            if threads <= 0:
                raise ValueError
        except ValueError:
            logger.error("Error: Number of threads must be a positive integer!")
            messagebox.showerror("Error", "Number of threads must be a positive integer!")
            return False
        try:
            delay_min = float(self.delay_min_entry.get())
            delay_max = float(self.delay_max_entry.get())
            if delay_min < 0 or delay_max < 0 or delay_min > delay_max:
                raise ValueError
        except ValueError:
            logger.error("Error: Invalid delay range!")
            messagebox.showerror("Error", "Invalid delay range! Please enter valid positive numbers, with min <= max.")
            return False
        return True

    def beautify_ui(self):
        self.root.configure(bg="#F1F3FF")
        self.main_frame.configure(fg_color="#F1F3FF")

        # Update entry styles
        entry_style = {
            "fg_color": "#FFFFFF",
            "border_color": "#4A55A2",
            "border_width": 1,
            "corner_radius": 10
        }

        for entry in [self.threads_entry, self.captcha_api_entry, self.ref_code_entry, self.delay_min_entry, self.delay_max_entry]:
            entry.configure(**entry_style)

        # Update label styles
        label_style = {
            "font": ("Helvetica", 14),
            "text_color": "#2E3A59"
        }

        for label in [self.accounts_label, self.proxies_label, self.threads_label, self.captcha_label, self.captcha_api_label, self.ref_code_label, self.delay_label]:
            label.configure(**label_style)

        # Update log box style with bigger font
        self.log_box.configure(
            bg="#F8F9FA",
            fg="#2E3A59",
            font=("Consolas", 14),  # Increased font size
            relief="flat",
            padx=10,
            pady=10
        )

    def toggle_ref_code_visibility(self):
        if self.ref_code_label.winfo_viewable():
            self.ref_code_label.grid_remove()
            self.ref_code_entry.grid_remove()
            self.toggle_ref_code_button.configure(text="⋮")
        else:
            self.ref_code_label.grid()
            self.ref_code_entry.grid()
            self.toggle_ref_code_button.configure(text="×")

    def view_earnings(self):
        try:
            # Store earnings window as class attribute
            if hasattr(self, 'earnings_window') and self.earnings_window.winfo_exists():
                self.earnings_window.lift()  # Bring window to front if it exists
                return

            with open('data/earnings.csv', 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                earnings_data = list(reader)

            # Create a new window to display earnings
            self.earnings_window = ctk.CTkToplevel()
            self.earnings_window.title("Account Earnings")
            self.earnings_window.geometry("500x300")
            self.earnings_window.configure(fg_color="#F1F3FF")
            
            # Position the window to the right of the main window
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            self.earnings_window.geometry(f"+{main_x + self.root.winfo_width() + 10}+{main_y}")

            # Create a frame for the content
            content_frame = ctk.CTkFrame(self.earnings_window, fg_color="#FFFFFF", corner_radius=10)
            content_frame.pack(fill="both", expand=True, padx=10, pady=10)

            # Create a text widget to display the data
            self.earnings_text = Text(
                content_frame,
                wrap="none",
                bg="#FFFFFF",
                fg="#2E3A59",
                font=("Consolas", 12),
                relief="flat",
                padx=10,
                pady=10,
                height=15
            )
            self.earnings_text.pack(fill="both", expand=True, padx=5, pady=5)

            # Add scrollbars
            y_scrollbar = ctk.CTkScrollbar(content_frame, command=self.earnings_text.yview)
            y_scrollbar.pack(side="right", fill="y")
            x_scrollbar = ctk.CTkScrollbar(content_frame, command=self.earnings_text.xview, orientation="horizontal")
            x_scrollbar.pack(side="bottom", fill="x")
            self.earnings_text.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)

            # Configure tags for styling
            self.earnings_text.tag_configure("header", font=("Consolas", 12, "bold"), foreground="#4A55A2")
            self.earnings_text.tag_configure("separator", foreground="#4A55A2")
            self.earnings_text.tag_configure("data", font=("Consolas", 11))
            self.earnings_text.tag_configure("earnings", foreground="#593FDE", font=("Consolas", 11, "bold"))

            def update_earnings():
                if not self.earnings_window.winfo_exists():
                    return
                
                try:
                    with open('data/earnings.csv', 'r', newline='') as f:
                        reader = csv.reader(f)
                        next(reader)  # Skip header
                        current_data = list(reader)

                    self.earnings_text.configure(state="normal")
                    self.earnings_text.delete("1.0", "end")
                    
                    # Format and display the data
                    self.earnings_text.insert("1.0", f"{'Email':<35} {'Last Update':<20} {'Total Earnings':<15}\n", "header")
                    self.earnings_text.insert("2.0", "─" * 70 + "\n", "separator")
                    
                    for email, last_update, total_earning in current_data:
                        line = f"{email:<35} {last_update:<20} "
                        self.earnings_text.insert("end", line, "data")
                        self.earnings_text.insert("end", f"{total_earning:>15}\n", "earnings")

                    self.earnings_text.configure(state="disabled")
                    
                    # Schedule next update
                    self.earnings_window.after(5000, update_earnings)  # Update every 5 seconds
                except Exception as e:
                    logger.error(f"Error updating earnings: {e}")

            # Initial display
            update_earnings()

            # Make the window stay on top
            self.earnings_window.attributes('-topmost', True)
            self.earnings_window.update()

        except FileNotFoundError:
            messagebox.showinfo("No Data", "No earnings data available yet.")
        except Exception as e:
            logger.error(f"Error viewing earnings: {e}")
            messagebox.showerror("Error", f"Failed to load earnings data: {e}")

if __name__ == "__main__":
    root = ctk.CTk()
    app = BotGUI(root)
    app.setup_logger()
    root.mainloop()
