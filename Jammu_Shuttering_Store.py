import random
import sys
import os
import json
import datetime as dt
import locale
import time
import uuid
from tkinter import messagebox, ttk
import customtkinter as ctk
import pyautogui
from tkcalendar import Calendar
from PIL import Image
import qrcode
import fitz  # PyMuPDF
from fpdf import FPDF
import subprocess
from fpdf.enums import XPos, YPos


class RentalBillApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self._init_variables()
        self._setup_config()
        self._setup_ui()
        self.setup_keyboard_shortcuts()
        self.clear_all(mess=False)  # Initialize with a new customer ID

    def _setup_config(self):
        """Initialize configuration settings"""
        self.title(f"{self.company_name} - Rental Billing System")
        self._state_before_windows_set_titlebar_color = 'zoomed'
        self.original_argv = sys.argv.copy()

        # Create necessary directories
        os.makedirs("bills", exist_ok=True)
        os.makedirs("data", exist_ok=True)
        os.makedirs("settings", exist_ok=True)

        try:
            locale.setlocale(locale.LC_ALL, 'en_IN')
        except locale.Error:
            locale.setlocale(locale.LC_ALL, '')

    def _init_variables(self):
        """Initialize all application variables"""
        # Company Details
        self.company_name = "Company Name"
        self.company_mobile = "987*******"
        self.company_address = "_________, _______(14****)"
        self.company_upi = "ABC@okbank"

        # Color palette
        self.primary_color = "#2b579a"
        self.secondary_color = "#5cb85c"
        self.accent_color = "#f0ad4e"
        self.danger_color = "#d9534f"
        self.info_color = "#5bc0de"
        self.light_bg_color = "#f8f9fa"
        self.border_color = "#dee2e6"

        # Font settings
        self.font_heading = ctk.CTkFont(size=24, weight="bold", family="Segoe UI")
        self.font_subheading = ctk.CTkFont(size=18, weight="bold", family="Segoe UI")
        self.font_normal_bold = ctk.CTkFont(size=14, weight="bold", family="Segoe UI")
        self.font_normal = ctk.CTkFont(size=14, family="Segoe UI")
        self.font_small = ctk.CTkFont(size=12, family="Segoe UI")

        # Application variables
        self.customer_id = ctk.StringVar()
        self.customer_name = ctk.StringVar()
        self.customer_mobile = ctk.StringVar()
        self.customer_address = ctk.StringVar()
        self.previous_balance = ctk.DoubleVar(value=0.0)
        self.payment_received = ctk.DoubleVar(value=0.0)

        # Data storage
        self.items = []
        self.transactions = []

        # Load settings
        self.load_settings()

    def _generate_customer_id(self):
        """Generates a unique customer ID."""
        timestamp = dt.datetime.now().strftime("%m%d%H%M")
        random_part = random.randint(100, 999)
        return f"CUST-{timestamp}-{random_part}"

    def _setup_ui(self):
        """Set up the main user interface"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._create_header()
        self._create_main_tabs()
        self._create_action_buttons()

    def _create_header(self):
        """Create the application header"""
        header_frame = ctk.CTkFrame(self, fg_color=self.primary_color, corner_radius=0, height=80)
        header_frame.grid(row=0, column=0, sticky="nsew")
        header_frame.grid_columnconfigure(1, weight=1)

        logo_frame = ctk.CTkFrame(header_frame, fg_color="transparent", width=80)
        logo_frame.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        try:
            logo_img = ctk.CTkImage(Image.open("logo.png"), size=(60, 60))
            ctk.CTkLabel(logo_frame, image=logo_img, text="").pack()
        except FileNotFoundError:
            ctk.CTkLabel(logo_frame, text="🏢", font=("Segoe UI", 40)).pack()

        info_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        info_frame.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        self.header_title = ctk.CTkLabel(
            info_frame, text=self.company_name, font=self.font_heading, text_color="white"
        )
        self.header_title.pack(anchor="w", pady=(5, 0))

        self.header_subtitle = ctk.CTkLabel(
            info_frame, text=f"📱 {self.company_mobile} | 📍 {self.company_address}",
            font=self.font_normal, text_color="white"
        )
        self.header_subtitle.pack(anchor="w")

    def _create_main_tabs(self):
        """Create the main tab view"""
        self.tabview = ctk.CTkTabview(self, border_width=1, border_color=self.border_color)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 5))
        self.tabview._segmented_button.configure(font=self.font_normal_bold, height=35)

        self.create_dashboard_tab(self.tabview.add("Dashboard"))
        self.create_customer_tab(self.tabview.add("Customer Info"))
        self.create_items_tab(self.tabview.add("Rental Items"))
        self.create_transactions_tab(self.tabview.add("Transactions"))

    def _create_action_buttons(self):
        """Create the action buttons at the bottom"""
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        btn_style = {"height": 40, "font": self.font_normal_bold, "corner_radius": 8}

        buttons = [
            ("💾 Save Data", self.save_customer_data, self.secondary_color, "#449d44"),
            ("🔍 Search PDFs", self.open_pdf_search, self.info_color, "#31b0d5"),
            ("🖨️ Generate Bill", self.generate_bill, self.primary_color, "#1e3f74"),
            ("🗑️ New Customer", lambda: self.clear_all(mess=True), self.danger_color, "#c9302c"),
            ("📱 Share WhatsApp", self.share_whatsapp, "#25D366", "#128C7E"),
            ("⚙️ Settings", self.open_settings, "#6c757d", "#5a6268"),
            ("❌ Exit", self.quit, self.danger_color, "#c9302c")
        ]

        num_buttons = len(buttons)
        for i in range(num_buttons):
            btn_frame.grid_columnconfigure(i, weight=1)

        for i, (text, command, hover, fg) in enumerate(buttons):
            ctk.CTkButton(
                btn_frame, text=text, command=command, fg_color=fg, hover_color=hover, **btn_style
            ).grid(row=0, column=i, padx=5, pady=5, sticky="ew")

    def create_customer_tab(self, tab):
        """Create the customer information tab"""
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        cust_frame = ctk.CTkFrame(tab, border_width=2, border_color="#ddd", corner_radius=10)
        cust_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)

        # Section Header
        header_frame = ctk.CTkFrame(cust_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 15))

        ctk.CTkLabel(
            header_frame,
            text="Customer Information",
            font=self.font_subheading,
            text_color=self.primary_color
        ).pack(side="left")

        line = ctk.CTkFrame(header_frame, fg_color="#ddd", height=2)
        line.pack(side="left", fill="x", expand=True, padx=10)

        # Form Fields
        fields = [
            ("Customer ID:", self.customer_id),
            ("Name:", self.customer_name),
            ("Mobile:", self.customer_mobile),
            ("Address:", self.customer_address),
            ("Add Charges and Fees (₹):", self.previous_balance),
            ("Payment Received (₹):", self.payment_received),
        ]

        for label, var in fields:
            frame = ctk.CTkFrame(cust_frame, fg_color="transparent")
            frame.pack(fill="x", padx=20, pady=8)

            ctk.CTkLabel(
                frame,
                text=label,
                font=self.font_normal,
                width=150,
                anchor="e"
            ).pack(side="left", padx=5)

            entry = ctk.CTkEntry(
                frame,
                textvariable=var,
                font=self.font_normal,
                height=38,
                border_width=1,
                corner_radius=6,
                border_color="#ced4da"
            )
            entry.pack(side="left", fill="x", expand=True)

            if label == "Customer ID:" or label == 'Payment Received (₹):':
                entry.configure(state="readonly", fg_color="#eee")

            if label.endswith("(₹):"):
                entry.configure(width=150, justify="right")

        ledger_frame = ctk.CTkFrame(cust_frame, fg_color="transparent")
        ledger_frame.pack(fill="x", padx=20, pady=15)
        ctk.CTkButton(
            ledger_frame,
            text="Add Payment / View Ledger",
            command=self.open_payment_ledger,
            font=self.font_normal,
            fg_color=self.accent_color,
            hover_color="#ec971f"
        ).pack(side="right")

    def create_items_tab(self, tab):
        """Create the rental items management tab"""
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(tab, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        item_frame = ctk.CTkFrame(main_frame, border_width=2, border_color="#ddd", corner_radius=10)
        item_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Section Header
        header_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 15))

        ctk.CTkLabel(
            header_frame,
            text="Rental Items Management",
            font=self.font_subheading,
            text_color=self.primary_color
        ).pack(side="left")

        line = ctk.CTkFrame(header_frame, fg_color="#ddd", height=2)
        line.pack(side="left", fill="x", expand=True, padx=10)

        # Item Treeview
        tree_card = ctk.CTkFrame(item_frame, corner_radius=8)
        tree_card.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.item_tree = ttk.Treeview(
            master=tree_card,
            columns=("Name", "Rent"),
            show="headings",
            height=8,
            selectmode="browse"
        )

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background="#ffffff",
                        foreground="black",
                        rowheight=40,
                        fieldbackground="#ffffff",
                        font=('Segoe UI', 14))
        style.configure("Treeview.Heading",
                        background=self.primary_color,
                        foreground="white",
                        font=('Segoe UI', 14, 'bold'))
        style.map('Treeview', background=[('selected', '#3472bc')])

        self.item_tree.heading("Name", text="Item Name")
        self.item_tree.heading("Rent", text="Daily Rent (₹)")
        self.item_tree.column("Name", width=300, anchor="w")
        self.item_tree.column("Rent", width=180, anchor="e")

        y_scroll = ttk.Scrollbar(tree_card, orient="vertical", command=self.item_tree.yview)
        x_scroll = ttk.Scrollbar(tree_card, orient="horizontal", command=self.item_tree.xview)
        self.item_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.item_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        tree_card.grid_rowconfigure(0, weight=1)
        tree_card.grid_columnconfigure(0, weight=1)

        # Item Entry Frame
        entry_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        entry_frame.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            entry_frame,
            text="Add New Item:",
            font=self.font_normal
        ).pack(side="left", padx=5)

        self.item_name_entry = ctk.CTkEntry(
            entry_frame,
            placeholder_text="Item Name",
            width=200,
            height=38,
            font=self.font_normal,
            border_color="#ced4da"
        )
        self.item_name_entry.pack(side="left", padx=5)

        self.rent_entry = ctk.CTkEntry(
            entry_frame,
            placeholder_text="Daily Rent",
            width=120,
            height=38,
            font=self.font_normal,
            border_color="#ced4da"
        )
        self.rent_entry.pack(side="left", padx=5)

        btn_style = {
            "width": 100,
            "height": 38,
            "font": self.font_normal,
            "corner_radius": 6
        }

        self.add_item_btn = ctk.CTkButton(
            entry_frame,
            text="➕ Add",
            command=self.add_item,
            fg_color=self.secondary_color,
            hover_color="#449d44",
            **btn_style
        )
        self.add_item_btn.pack(side="left", padx=5)

        ctk.CTkButton(
            entry_frame,
            text="✏️ Edit",
            command=self.edit_item,
            fg_color=self.accent_color,
            hover_color="#ec971f",
            **btn_style
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            entry_frame,
            text="🗑️ Remove",
            command=self.remove_item,
            fg_color=self.danger_color,
            hover_color="#c9302c",
            **btn_style
        ).pack(side="left", padx=5)

    def edit_item(self):
        """Edit the selected rental item directly in the items tab"""
        selected = self.item_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an item to edit")
            return

        index = self.item_tree.index(selected[0])
        current_name, current_rent = self.items[index]

        # Store original values
        self._editing_item_index = index
        self._editing_item_id = selected[0]

        # Pre-fill the entry fields
        self.item_name_entry.delete(0, "end")
        self.item_name_entry.insert(0, current_name)

        self.rent_entry.delete(0, "end")
        self.rent_entry.insert(0, str(current_rent))

        # Change Add button to Update
        for btn in self.item_tree.master.master.winfo_children():
            if isinstance(btn, ctk.CTkFrame):  # The entry frame
                for child in btn.winfo_children():
                    if isinstance(child, ctk.CTkButton) and child.cget("text") == "➕ Add":
                        child.configure(text="🔄 Update",
                                        command=self._update_item,
                                        fg_color=self.accent_color,
                                        hover_color="#ec971f")
                        self._add_item_btn = child  # Store reference to restore later

        self.item_name_entry.focus()

    def _update_item(self):
        """Update the rental item with current form values"""
        try:
            if not hasattr(self, '_editing_item_index'):
                raise ValueError("No item selected for editing")

            new_name = self.item_name_entry.get().strip()
            new_rent = self.rent_entry.get().strip()

            if not new_name:
                raise ValueError("Item name cannot be empty")

            try:
                new_rent = float(new_rent)
                if new_rent <= 0:
                    raise ValueError("Rent must be positive")
            except ValueError as e:
                raise ValueError(f"Invalid rent amount: {str(e)}")

            # Update the item
            self.items[self._editing_item_index] = (new_name, new_rent)
            self.item_tree.item(self._editing_item_id, values=(new_name, f"₹{new_rent:.2f}"))
            self.item_combo.configure(values=[item[0] for item in self.items])

            # Reset the form
            self._reset_item_form()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _reset_item_form(self):
        """Reset the item form to its default state"""
        self.item_name_entry.delete(0, "end")
        self.rent_entry.delete(0, "end")

        # Restore the Add button if it was changed
        if hasattr(self, '_add_item_btn'):
            self._add_item_btn.configure(text="➕ Add",
                                         command=self.add_item,
                                         fg_color=self.secondary_color,
                                         hover_color="#449d44")

        # Clear editing references
        if hasattr(self, '_editing_item_index'):
            del self._editing_item_index
        if hasattr(self, '_editing_item_id'):
            del self._editing_item_id

        self.item_name_entry.focus()

    def create_transactions_tab(self, tab):
        """Create the transactions tab"""
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(tab, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Transactions Frame
        trans_frame = ctk.CTkFrame(main_frame, border_width=2, border_color="#ddd", corner_radius=10)
        trans_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Section Header
        header_frame = ctk.CTkFrame(trans_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 15))

        ctk.CTkLabel(
            header_frame,
            text="Rental Transactions",
            font=self.font_subheading,
            text_color=self.primary_color
        ).pack(side="left")

        line = ctk.CTkFrame(header_frame, fg_color="#ddd", height=2)
        line.pack(side="left", fill="x", expand=True, padx=10)

        # Transaction Treeview
        tree_card = ctk.CTkFrame(trans_frame, corner_radius=8)
        tree_card.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.trans_tree = ttk.Treeview(
            master=tree_card,
            columns=("Date", "Item", "Qty", "Action"),
            show="headings",
            height=12,
            selectmode="browse"
        )

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background="#ffffff",
                        foreground="black",
                        rowheight=35,
                        fieldbackground="#ffffff",
                        font=('Segoe UI', 12))
        style.configure("Treeview.Heading",
                        background=self.primary_color,
                        foreground="white",
                        font=('Segoe UI', 12, 'bold'))
        style.map('Treeview', background=[('selected', '#3472bc')])

        self.trans_tree.heading("Date", text="Date")
        self.trans_tree.heading("Item", text="Item Name")
        self.trans_tree.heading("Qty", text="Quantity")
        self.trans_tree.heading("Action", text="Action")

        self.trans_tree.column("Date", width=150, anchor="w")
        self.trans_tree.column("Item", width=250, anchor="w")
        self.trans_tree.column("Qty", width=100, anchor="center")
        self.trans_tree.column("Action", width=120, anchor="center")

        y_scroll = ttk.Scrollbar(tree_card, orient="vertical", command=self.trans_tree.yview)
        x_scroll = ttk.Scrollbar(tree_card, orient="horizontal", command=self.trans_tree.xview)
        self.trans_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.trans_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        tree_card.grid_rowconfigure(0, weight=1)
        tree_card.grid_columnconfigure(0, weight=1)

        # Transaction Entry Frame
        entry_frame = ctk.CTkFrame(trans_frame, fg_color="transparent")
        entry_frame.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            entry_frame,
            text="Date:",
            font=self.font_normal
        ).pack(side="left", padx=5)

        self.date_entry = ctk.CTkEntry(
            entry_frame,
            width=120,
            height=38,
            font=self.font_normal,
            border_color="#ced4da"
        )
        self.date_entry.pack(side="left", padx=5)

        ctk.CTkLabel(
            entry_frame,
            text="Item:",
            font=self.font_normal
        ).pack(side="left", padx=5)

        self.item_combo = ctk.CTkComboBox(
            entry_frame,
            width=200,
            height=38,
            font=self.font_normal,
            dropdown_fg_color="white",
            dropdown_text_color="black",
            state="readonly",
            button_color=self.primary_color
        )
        self.item_combo.pack(side="left", padx=5)

        ctk.CTkLabel(
            entry_frame,
            text="Qty:",
            font=self.font_normal
        ).pack(side="left", padx=5)

        self.qty_entry = ctk.CTkEntry(
            entry_frame,
            width=80,
            height=38,
            font=self.font_normal,
            border_color="#ced4da"
        )
        self.qty_entry.pack(side="left", padx=5)

        btn_style = {
            "width": 100,
            "height": 38,
            "font": self.font_normal,
            "corner_radius": 6
        }

        ctk.CTkButton(
            entry_frame,
            text="➕ Rent",
            command=lambda: self.add_transaction("Rent"),
            fg_color=self.secondary_color,
            hover_color="#449d44",
            **btn_style
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            entry_frame,
            text="➖ Return",
            command=lambda: self.add_transaction("Return"),
            fg_color=self.accent_color,
            hover_color="#ec971f",
            **btn_style
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            entry_frame,
            text="✏️ Edit",
            command=self.edit_transaction,
            fg_color=self.info_color,
            hover_color="#31b0d5",
            **btn_style
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            entry_frame,
            text="🗑️ Remove",
            command=self.remove_transaction,
            fg_color=self.danger_color,
            hover_color="#c9302c",
            **btn_style
        ).pack(side="left", padx=5)

        # Calendar Frame
        calendar_frame = ctk.CTkFrame(main_frame, border_width=2, border_color="#ddd", corner_radius=10)
        calendar_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        header_frame = ctk.CTkFrame(calendar_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            header_frame,
            text="Date Picker",
            font=self.font_subheading,
            text_color=self.primary_color
        ).pack(side="left")

        line = ctk.CTkFrame(header_frame, fg_color="#ddd", height=2)
        line.pack(side="left", fill="x", expand=True, padx=10)

        self.cal = Calendar(
            calendar_frame,
            selectmode='day',
            date_pattern='y-mm-dd',
            font=('Segoe UI', 14),
            background='white',
            foreground='black',
            selectforeground='white',
            bordercolor='#ddd',
            headersbackground='#f0f0f0',
            normalbackground='white',
            weekendbackground='white',
            othermonthbackground='#f9f9f9',
            othermonthwebackground='#f9f9f9'
        )
        self.cal.pack(padx=10, pady=10, fill="both", expand=True)

        ctk.CTkButton(
            calendar_frame,
            text="Set Selected Date",
            command=self.set_selected_date,
            fg_color=self.primary_color,
            hover_color="#1e3f74",
            height=38,
            font=self.font_normal,
            corner_radius=6
        ).pack(pady=(0, 10), padx=10, fill="x")

    def edit_transaction(self):
        """Edit the selected transaction"""
        selected = self.trans_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a transaction to edit")
            return

        index = self.trans_tree.index(selected[0])
        date, item, qty, rent = self.transactions[index]
        action = "Rent" if qty > 0 else "Return"

        # Create edit dialog
        edit_window = ctk.CTkToplevel(self)
        edit_window.title("Edit Transaction")
        edit_window.geometry("500x300+650+300")
        edit_window.resizable(False, False)
        edit_window.transient(self)
        edit_window.grab_set()

        ctk.CTkLabel(
            edit_window,
            text="Edit Transaction",
            font=self.font_subheading
        ).pack(pady=10)

        # Date
        date_frame = ctk.CTkFrame(edit_window, fg_color="transparent")
        date_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(date_frame, text="Date:").pack(side="left")
        date_entry = ctk.CTkEntry(date_frame)
        from_cal_btn = ctk.CTkButton(
            date_frame,
            text="📅",
            width=30,
            height=36,
            command=lambda: self.open_calendar(date_entry),
            fg_color="#e9ecef",
            hover_color="#dee2e6",
            text_color="#495057",
            corner_radius=8
        )
        from_cal_btn.pack(side="left", padx=(5, 15))
        date_entry.pack(side="left", fill="x", expand=True)
        date_entry.insert(0, str(date))

        # Item
        item_frame = ctk.CTkFrame(edit_window, fg_color="transparent")
        item_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(item_frame, text="Item:").pack(side="left")
        item_combo = ctk.CTkComboBox(
            item_frame,
            values=[item[0] for item in self.items],
            state="readonly"
        )
        item_combo.pack(side="left", fill="x", expand=True)
        item_combo.set(item)

        # Quantity
        qty_frame = ctk.CTkFrame(edit_window, fg_color="transparent")
        qty_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(qty_frame, text="Quantity:").pack(side="left")
        qty_entry = ctk.CTkEntry(qty_frame)
        qty_entry.pack(side="left", fill="x", expand=True)
        qty_entry.insert(0, str(abs(qty)))

        # Action
        action_frame = ctk.CTkFrame(edit_window, fg_color="transparent")
        action_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(action_frame, text="Action:").pack(side="left")
        action_var = ctk.StringVar(value=action)
        ctk.CTkRadioButton(
            action_frame,
            text="Rent",
            variable=action_var,
            value="Rent"
        ).pack(side="left", padx=10)
        ctk.CTkRadioButton(
            action_frame,
            text="Return",
            variable=action_var,
            value="Return"
        ).pack(side="left", padx=10)

        def save_changes():
            try:
                # Validate date
                date_str = date_entry.get().strip()
                if not date_str:
                    raise ValueError("Please enter a date")

                try:
                    year, month, day = map(int, date_str.split('-'))
                    new_date = dt.date(year, month, day)
                except ValueError:
                    raise ValueError("Invalid date format (YYYY-MM-DD)")

                # Validate item
                new_item = item_combo.get()
                if not new_item:
                    raise ValueError("Please select an item")

                # Validate quantity
                new_qty_str = qty_entry.get().strip()
                if not new_qty_str:
                    raise ValueError("Please enter quantity")

                try:
                    new_qty = int(new_qty_str)
                    if new_qty < 0:
                        raise ValueError("Quantity must be positive")
                except ValueError:
                    raise ValueError("Quantity must be a positive number")

                # Adjust quantity based on action
                if action_var.get() == "Return":
                    new_qty = -new_qty

                # Find the item's rent
                new_rent = next((item[1] for item in self.items if item[0] == new_item), None)

                # Update transaction
                self.transactions[index] = (new_date, new_item, new_qty, new_rent)

                # Update treeview
                self.trans_tree.item(selected[0], values=(
                    str(new_date),
                    new_item,
                    abs(new_qty),
                    action_var.get()
                ))

                edit_window.destroy()

            except Exception as e:
                messagebox.showerror("Error", str(e))

        btn_frame = ctk.CTkFrame(edit_window, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(
            btn_frame,
            text="Save",
            command=save_changes,
            fg_color=self.secondary_color,
            width=100
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=edit_window.destroy,
            fg_color=self.danger_color,
            width=100
        ).pack(side="left", padx=10)

    def clear_filters(self):
        """Clear all search filters"""
        self.search_entry.delete(0, "end")
        self.search_entry.configure(placeholder_text="Search by customer name, mobile, ID, or #receipt ID...",)
        self.from_date_entry.delete(0, "end")
        self.from_date_entry.configure(placeholder_text="Start date")
        self.to_date_entry.delete(0, "end")
        self.to_date_entry.configure(placeholder_text="End date",)
        self.refresh_dashboard()

    def create_dashboard_tab(self, tab):
        """Create the dashboard tab with premium search UI and improved tables"""
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Create search card with modern styling
        search_card = ctk.CTkFrame(
            tab,
            border_width=0,
            corner_radius=12,
            fg_color="#f8f9fa"
        )
        search_card.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        search_card.grid_columnconfigure(1, weight=1)

        # Section header with icon
        header_frame = ctk.CTkFrame(search_card, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            header_frame,
            text="🔍 Advanced Bill Search",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.primary_color
        ).pack(side="left")

        # Add help tooltip
        help_icon = ctk.CTkLabel(
            header_frame,
            text="ⓘ",
            font=ctk.CTkFont(size=14),
            text_color="#6c757d",
            cursor="hand2"
        )
        help_icon.pack(side="left", padx=5)
        help_icon.bind("<Button-1>", lambda e: self.show_search_help())

        # Search row - improved with icon
        search_row = ctk.CTkFrame(search_card, fg_color="transparent")
        search_row.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=5)

        # Customer search with icon
        search_icon = ctk.CTkLabel(
            search_row,
            text="👤",
            font=ctk.CTkFont(size=14),
            width=20
        )
        search_icon.pack(side="left", padx=(0, 5))

        self.search_entry = ctk.CTkEntry(
            search_row,
            placeholder_text="Search by customer name, mobile, ID, or #receipt ID...",
            width=250,
            font=self.font_normal,
            border_color="#dee2e6",
            corner_radius=8,
            height=36
        )
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<Return>", lambda e: self.filter_bills())

        # Date range row - improved layout
        date_row = ctk.CTkFrame(search_card, fg_color="transparent")
        date_row.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=5)

        # From date with icon
        ctk.CTkLabel(
            date_row,
            text="📅 From:",
            font=self.font_normal
        ).pack(side="left", padx=(0, 5))

        self.from_date_entry = ctk.CTkEntry(
            date_row,
            placeholder_text="Start date",
            width=120,
            font=self.font_normal,
            border_color="#dee2e6",
            corner_radius=8,
            height=36
        )
        self.from_date_entry.pack(side="left")

        # Calendar picker button
        from_cal_btn = ctk.CTkButton(
            date_row,
            text="▼",
            width=30,
            height=36,
            command=lambda: self.open_calendar(self.from_date_entry),
            fg_color="#e9ecef",
            hover_color="#dee2e6",
            text_color="#495057",
            corner_radius=8
        )
        from_cal_btn.pack(side="left", padx=(5, 15))

        # To date with icon
        ctk.CTkLabel(
            date_row,
            text="📅 To:",
            font=self.font_normal
        ).pack(side="left", padx=(0, 5))

        self.to_date_entry = ctk.CTkEntry(
            date_row,
            placeholder_text="End date",
            width=120,
            font=self.font_normal,
            border_color="#dee2e6",
            corner_radius=8,
            height=36
        )
        self.to_date_entry.pack(side="left")

        # Calendar picker button
        to_cal_btn = ctk.CTkButton(
            date_row,
            text="▼",
            width=30,
            height=36,
            command=lambda: self.open_calendar(self.to_date_entry),
            fg_color="#e9ecef",
            hover_color="#dee2e6",
            text_color="#495057",
            corner_radius=8
        )
        to_cal_btn.pack(side="left", padx=(5, 0))

        # Action buttons - modern styling
        btn_row = ctk.CTkFrame(search_card, fg_color="transparent")
        btn_row.grid(row=3, column=0, columnspan=3, sticky="e", padx=10, pady=(5, 10))

        ctk.CTkButton(
            btn_row,
            text="Apply Filters",
            command=self.filter_bills,
            width=120,
            height=36,
            font=self.font_normal,
            fg_color=self.primary_color,
            hover_color="#1a4b8c",
            corner_radius=8,
            border_width=0
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_row,
            text="Clear All",
            command=self.clear_filters,
            width=100,
            height=36,
            font=self.font_normal,
            fg_color="transparent",
            hover_color="#e9ecef",
            text_color="#495057",
            corner_radius=8,
            border_width=1,
            border_color="#dee2e6"
        ).pack(side="left")

        # Quick filter chips
        quick_filter_frame = ctk.CTkFrame(search_card, fg_color="transparent")
        quick_filter_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            quick_filter_frame,
            text="Quick Filters:",
            font=ctk.CTkFont(size=13),
            text_color="#6c757d"
        ).pack(side="left", padx=(0, 10))

        time_filters = [
            ("Today", "today", "#e2f0fd"),
            ("This Week", "week", "#d1e7ff"),
            ("This Month", "month", "#c0dfff"),
            ("Last Month", "last_month", "#afd7ff")
        ]

        for text, filter_type, color in time_filters:
            btn = ctk.CTkButton(
                quick_filter_frame,
                text=text,
                command=lambda t=filter_type: self.set_quick_filter(t),
                width=80,
                height=28,
                font=ctk.CTkFont(size=12),
                fg_color=color,
                hover_color="#b8d6fb",
                text_color=self.primary_color,
                corner_radius=20,
                border_width=0
            )
            btn.pack(side="left", padx=5)

        status_filters = [
            ("Unpaid", "unpaid", "#fee2e2", self.danger_color),
            ("Paid", "paid", "#dcfce7", self.secondary_color),
            ("Partial", "partial", "#fef9c3", "#f59f00")
        ]

        for text, filter_type, color, text_color in status_filters:
            btn = ctk.CTkButton(
                quick_filter_frame,
                text=text,
                command=lambda t=filter_type: self.set_quick_filter(t),
                width=80,
                height=28,
                font=ctk.CTkFont(size=12),
                fg_color=color,
                hover_color="#f3f4f6",
                text_color=text_color,
                corner_radius=20,
                border_width=0
            )
            btn.pack(side="left", padx=5)

        # Main content frame
        main_frame = ctk.CTkFrame(tab, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.dashboard_main_frame = main_frame

        # Metrics row
        metrics_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        metrics_frame.pack(fill="x", padx=5, pady=5)
        self.dashboard_metrics_frame = metrics_frame

        # Data row with 2 columns
        data_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        data_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Customer list (left)
        customer_frame = ctk.CTkFrame(data_frame, border_width=2, border_color="#ddd", corner_radius=10)
        customer_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(
            customer_frame,
            text="Customer List (Double-click to load)",
            font=self.font_subheading,
            text_color="#2b579a"
        ).pack(pady=(10, 5))

        self.customer_tree = ttk.Treeview(
            master=customer_frame,
            columns=("ID", "Name", "Mobile", "Last Transaction", "Balance"),
            show="headings",
            height=12
        )

        style = ttk.Style()
        style.configure("Customer.Treeview",
                        background="#ffffff",
                        foreground="black",
                        rowheight=25,
                        fieldbackground="#ffffff",
                        font=('Helvetica', 10))
        style.configure("Customer.Treeview.Heading",
                        background="#2b579a",
                        foreground="white",
                        font=('Helvetica', 10, 'bold'))

        self.customer_tree.heading("ID", text="Customer ID")
        self.customer_tree.heading("Name", text="Name")
        self.customer_tree.heading("Mobile", text="Mobile")
        self.customer_tree.heading("Last Transaction", text="Last Transaction")
        self.customer_tree.heading("Balance", text="Balance")

        self.customer_tree.column("ID", width=160)
        self.customer_tree.column("Name", width=180)
        self.customer_tree.column("Mobile", width=120)
        self.customer_tree.column("Last Transaction", width=120)
        self.customer_tree.column("Balance", width=120, anchor="e")

        y_scroll = ttk.Scrollbar(customer_frame, orient="vertical", command=self.customer_tree.yview)
        self.customer_tree.configure(yscrollcommand=y_scroll.set)

        self.customer_tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")

        self.customer_tree.bind("<Double-1>", lambda event: self.load_selected_customer())

        # In-hand items summary (right)
        in_hand_frame = ctk.CTkFrame(data_frame, border_width=2, border_color="#ddd", corner_radius=10)
        in_hand_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(
            in_hand_frame,
            text="In-Hand Items Summary",
            font=self.font_subheading,
            text_color="#2b579a"
        ).pack(pady=(10, 5))

        self.in_hand_tree = ttk.Treeview(
            master=in_hand_frame,
            columns=("Item", "Rented", "Returned", "In-Hand"),
            show="headings",
            height=12
        )

        style.configure("InHand.Treeview",
                        background="#ffffff",
                        foreground="black",
                        rowheight=25,
                        fieldbackground="#ffffff",
                        font=('Helvetica', 10))
        style.configure("InHand.Treeview.Heading",
                        background="#2b579a",
                        foreground="white",
                        font=('Helvetica', 10, 'bold'))

        self.in_hand_tree.heading("Item", text="Item")
        self.in_hand_tree.heading("Rented", text="Rented")
        self.in_hand_tree.heading("Returned", text="Returned")
        self.in_hand_tree.heading("In-Hand", text="In-Hand")

        self.in_hand_tree.column("Item", width=150)
        self.in_hand_tree.column("Rented", width=80, anchor="center")
        self.in_hand_tree.column("Returned", width=80, anchor="center")
        self.in_hand_tree.column("In-Hand", width=80, anchor="center")

        y_scroll = ttk.Scrollbar(in_hand_frame, orient="vertical", command=self.in_hand_tree.yview)
        #
        self.in_hand_tree.configure(yscrollcommand=y_scroll.set)

        self.in_hand_tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")

        # Load initial data
        self.refresh_dashboard()

    def show_search_help(self):
        """Show help tooltip for search functionality"""
        help_text = """🔍 Search Tips:
        - Search by name, mobile, or address
        - Search by customer ID or #receipt ID
        - Use date ranges to find bills between specific dates
        - Quick filters for common time periods
        - Toggle advanced filters for more options
        - Press Enter to apply filters"""

        tooltip = ctk.CTkToplevel(self)
        tooltip.title("Search Help")
        tooltip.geometry("300x180")
        tooltip.resizable(False, False)
        tooltip.transient(self)
        tooltip.grab_set()

        ctk.CTkLabel(
            tooltip,
            text=help_text,
            font=ctk.CTkFont(size=13),
            justify="left",
            wraplength=280
        ).pack(padx=15, pady=15, fill="both", expand=True)

        ctk.CTkButton(
            tooltip,
            text="Got It",
            command=tooltip.destroy,
            width=80
        ).pack(pady=(0, 10))

    def open_calendar(self, target_entry):
        """Improved calendar popup with better styling"""
        calendar_window = ctk.CTkToplevel(self)
        calendar_window.title("Select Date")
        calendar_window.geometry("300x320")
        calendar_window.resizable(False, False)
        calendar_window.transient(self)
        calendar_window.grab_set()

        # Center the window
        window_width = calendar_window.winfo_reqwidth()
        window_height = calendar_window.winfo_reqheight()
        position_right = int(calendar_window.winfo_screenwidth() / 2 - window_width / 2)
        position_down = int(calendar_window.winfo_screenheight() / 2 - window_height / 2)
        calendar_window.geometry(f"+{position_right}+{position_down}")

        cal = Calendar(
            calendar_window,
            selectmode='day',
            date_pattern='y-mm-dd',
            font=('Segoe UI', 12),
            background='white',
            foreground='black',
            selectforeground='white',
            selectbackground=self.primary_color,
            bordercolor='#ddd',
            headersbackground='#f0f0f0',
            normalbackground='white',
            weekendbackground='white'
        )
        cal.pack(pady=10, padx=10, fill="both", expand=True)

        btn_frame = ctk.CTkFrame(calendar_window, fg_color="transparent")
        btn_frame.pack(pady=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="Select",
            command=lambda: self._set_calendar_date(cal, target_entry, calendar_window),
            width=100,
            fg_color=self.primary_color
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=calendar_window.destroy,
            width=100,
            fg_color="#6c757d"
        ).pack(side="left", padx=5)

    def _set_calendar_date(self, calendar, entry, window):
        """Helper to set date from calendar"""
        entry.delete(0, "end")
        entry.insert(0, calendar.get_date())
        window.destroy()

    def set_quick_filter(self, filter_type):
        """Set quick date filters"""
        today = dt.date.today()
        self.search_entry.delete(0, "end")

        if filter_type == "today":
            date_str = today.strftime("%Y-%m-%d")
            self.from_date_entry.delete(0, "end")
            self.from_date_entry.insert(0, date_str)
            self.to_date_entry.delete(0, "end")
            self.to_date_entry.insert(0, date_str)
        elif filter_type == "week":
            start_of_week = today - dt.timedelta(days=today.weekday())
            end_of_week = start_of_week + dt.timedelta(days=6)
            self.from_date_entry.delete(0, "end")
            self.from_date_entry.insert(0, start_of_week.strftime("%Y-%m-%d"))
            self.to_date_entry.delete(0, "end")
            self.to_date_entry.insert(0, end_of_week.strftime("%Y-%m-%d"))
        elif filter_type == "month":
            start_of_month = dt.date(today.year, today.month, 1)
            end_of_month = dt.date(today.year, today.month + 1, 1) - dt.timedelta(days=1)
            self.from_date_entry.delete(0, "end")
            self.from_date_entry.insert(0, start_of_month.strftime("%Y-%m-%d"))
            self.to_date_entry.delete(0, "end")
            self.to_date_entry.insert(0, end_of_month.strftime("%Y-%m-%d"))
        elif filter_type == "last_month":
            # Handle year transition (if current month is January)
            if today.month == 1:
                last_month = 12
                year = today.year - 1
            else:
                last_month = today.month - 1
                year = today.year

            start_of_last_month = dt.date(year, last_month, 1)
            end_of_last_month = dt.date(year, last_month + 1, 1) - dt.timedelta(days=1)
            self.from_date_entry.delete(0, "end")
            self.from_date_entry.insert(0, start_of_last_month.strftime("%Y-%m-%d"))
            self.to_date_entry.delete(0, "end")
            self.to_date_entry.insert(0, end_of_last_month.strftime("%Y-%m-%d"))
        elif filter_type == "unpaid":
            self.from_date_entry.delete(0, "end")
            self.to_date_entry.delete(0, "end")
            self.filter_unpaid_bills()
            return
        elif filter_type == "paid":
            self.from_date_entry.delete(0, "end")
            self.to_date_entry.delete(0, "end")
            self.filter_paid_bills()
            return
        elif filter_type == "partial":
            self.from_date_entry.delete(0, "end")
            self.to_date_entry.delete(0, "end")
            self.filter_partial_bills()
            return

        self.filter_bills()

    def filter_paid_bills(self):
        """Filter for customers with no balance due (fully paid)"""
        for item in self.customer_tree.get_children():
            self.customer_tree.delete(item)

        for filename in os.listdir("data"):
            if filename.endswith(".json"):
                with open(f"data/{filename}", "r") as f:
                    data = json.load(f)
                    due_amount = self.calculate_customer_due_from_data(data)

                    if due_amount <= 0:
                        last_transaction = "None"
                        if "transactions" in data and data["transactions"]:
                            dates = [tx["date"] for tx in data["transactions"]]
                            last_transaction = max(dates)

                        cust_id = data.get("customer_id", "N/A")
                        self.customer_tree.insert("", "end", iid=filename, values=(
                            cust_id,
                            data["name"],
                            data["mobile"],
                            last_transaction,
                            f"₹{due_amount:,.2f}"
                        ))

    def filter_partial_bills(self):
        """Filter for customers who have made partial payments"""
        for item in self.customer_tree.get_children():
            self.customer_tree.delete(item)

        for filename in os.listdir("data"):
            if filename.endswith(".json"):
                with open(f"data/{filename}", "r") as f:
                    data = json.load(f)
                    due_amount = self.calculate_customer_due_from_data(data)
                    payment_received = data.get("payment_received", 0)

                    if due_amount > 0 and payment_received > 0:
                        last_transaction = "None"
                        if "transactions" in data and data["transactions"]:
                            dates = [tx["date"] for tx in data["transactions"]]
                            last_transaction = max(dates)

                        cust_id = data.get("customer_id", "N/A")
                        self.customer_tree.insert("", "end", iid=filename, values=(
                            cust_id,
                            data["name"],
                            data["mobile"],
                            last_transaction,
                            f"₹{due_amount:,.2f}"
                        ))

    def filter_bills(self):
        """Filter bills based on search criteria"""
        search_term = self.search_entry.get().strip().lower()
        from_date_str = self.from_date_entry.get().strip()
        to_date_str = self.to_date_entry.get().strip()

        from_date = None
        to_date = None

        try:
            if from_date_str:
                from_date = dt.datetime.strptime(from_date_str, "%Y-%m-%d").date()
            if to_date_str:
                to_date = dt.datetime.strptime(to_date_str, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD")
            return

        for item in self.customer_tree.get_children():
            self.customer_tree.delete(item)

        # Check if search is for receipt ID (starts with #)
        is_receipt_search = search_term.startswith('#')
        receipt_id_to_find = search_term[1:] if is_receipt_search else None

        for filename in os.listdir("data"):
            if filename.endswith(".json"):
                with open(f"data/{filename}", "r") as f:
                    data = json.load(f)

                    cust_id = data.get("customer_id", "")

                    # Regular search (name, mobile, customer ID)
                    matches_search = False
                    if not search_term:
                        matches_search = True
                    elif is_receipt_search:
                        # Search for receipt ID in payment history
                        for payment in data.get("payment_history", []):
                            if payment.get("id", "").lower() == receipt_id_to_find:
                                matches_search = True
                                break
                    else:
                        # Normal customer search
                        matches_search = (search_term in data["name"].lower() or
                                          search_term in data["mobile"].lower() or
                                          search_term in cust_id.lower())

                    matches_date = True
                    if from_date or to_date:
                        last_trans_date = None
                        if "transactions" in data and data["transactions"]:
                            dates = [tx["date"] for tx in data["transactions"]]
                            last_trans_date_str = max(dates)
                            last_trans_date = dt.datetime.strptime(last_trans_date_str, "%Y-%m-%d").date()

                        if from_date and last_trans_date and last_trans_date < from_date:
                            matches_date = False
                        if to_date and last_trans_date and last_trans_date > to_date:
                            matches_date = False

                    if matches_search and matches_date:
                        due_amount = self.calculate_customer_due_from_data(data)
                        last_transaction = "None"
                        if "transactions" in data and data["transactions"]:
                            dates = [tx["date"] for tx in data["transactions"]]
                            last_transaction = max(dates)

                        self.customer_tree.insert("", "end", iid=filename, values=(
                            cust_id,
                            data["name"],
                            data["mobile"],
                            last_transaction,
                            f"₹{due_amount:,.2f}"
                        ))

    def calculate_customer_due_from_data(self, customer_data):
        """Calculate due amount from customer data"""
        items = customer_data.get("items", [])
        transactions = []
        for tx in customer_data.get("transactions", []):
            try:
                date_obj = dt.datetime.strptime(tx["date"], "%Y-%m-%d").date()
                transactions.append((date_obj, tx["item"], tx["qty"], tx["rent"]))
            except (ValueError, TypeError):
                continue  # Skip malformed transaction dates

        if not transactions:
            previous_balance = customer_data.get("previous_balance", 0)
            payment_received = customer_data.get("payment_received", 0)
            return max(previous_balance - payment_received, 0)

        sorted_trans = sorted(transactions, key=lambda x: x[0])

        item_rents = {}
        current_items = {item[0]: 0 for item in items}

        for i in range(len(sorted_trans)):
            date, item_name, qty, rent = sorted_trans[i]
            if item_name not in current_items:
                continue
            current_items[item_name] += qty

            if i < len(sorted_trans) - 1:
                next_date = sorted_trans[i + 1][0]
                days = (next_date - date).days

                for item, count in current_items.items():
                    if count > 0:
                        item_rent_price = next((i[1] for i in items if i[0] == item), 0)
                        rent_amount = days * count * item_rent_price
                        item_rents[item] = item_rents.get(item, 0) + rent_amount

        total_rent = sum(item_rents.values())
        previous_balance = customer_data.get("previous_balance", 0)
        payment_received = customer_data.get("payment_received", 0)
        grand_total = total_rent + previous_balance - payment_received

        return max(grand_total, 0)

    def filter_unpaid_bills(self):
        """Filter for customers with unpaid balances"""
        for item in self.customer_tree.get_children():
            self.customer_tree.delete(item)

        for filename in os.listdir("data"):
            if filename.endswith(".json"):
                with open(f"data/{filename}", "r") as f:
                    data = json.load(f)
                    due_amount = self.calculate_customer_due_from_data(data)

                    if due_amount > 0:
                        last_transaction = "None"
                        if "transactions" in data and data["transactions"]:
                            dates = [tx["date"] for tx in data["transactions"]]
                            last_transaction = max(dates)

                        cust_id = data.get("customer_id", "N/A")
                        self.customer_tree.insert("", "end", iid=filename, values=(
                            cust_id,
                            data["name"],
                            data["mobile"],
                            last_transaction,
                            f"₹{due_amount:,.2f}"
                        ))

    def set_selected_date(self):
        """Set the selected date from the calendar"""
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, self.cal.get_date())

    def add_item(self):
        """Add a new rental item"""
        name = self.item_name_entry.get().strip()
        rent = self.rent_entry.get().strip()

        if not name:
            messagebox.showerror("Error", "Please enter item name")
            return

        if not rent:
            messagebox.showerror("Error", "Please enter rent amount")
            return

        try:
            rent = float(rent)
            if rent <= 0:
                raise ValueError("Rent must be positive")

            self.items.append((name, rent))
            self.item_tree.insert("", "end", values=(name, f"₹{rent:.2f}"))
            self.item_combo.configure(values=[item[0] for item in self.items])

            self.item_name_entry.delete(0, "end")
            self.rent_entry.delete(0, "end")
            self.item_name_entry.focus()

        except ValueError as e:
            messagebox.showerror("Error", f"Invalid rent amount: {str(e)}")

    def remove_item(self):
        """Remove the selected rental item"""
        selected = self.item_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an item to remove")
            return

        if not messagebox.askyesno("Confirm", "Delete selected item?"):
            return

        index = self.item_tree.index(selected[0])
        del self.items[index]
        self.item_tree.delete(selected[0])
        self.item_combo.configure(values=[item[0] for item in self.items])

    def add_transaction(self, action_type):
        """Add a new transaction (rent or return)"""
        try:
            date_str = self.date_entry.get().strip()
            if not date_str:
                raise ValueError("Please enter a date")

            try:
                year, month, day = map(int, date_str.split('-'))
                date = dt.date(year, month, day)
            except ValueError:
                raise ValueError("Invalid date format (YYYY-MM-DD)")

            item_name = self.item_combo.get()
            if not item_name:
                raise ValueError("Please select an item")

            qty_str = self.qty_entry.get().strip()
            if not qty_str:
                raise ValueError("Please enter quantity")

            try:
                qty = int(qty_str)
                if qty < 0:
                    raise ValueError("Quantity must be a positive integer")
            except ValueError:
                raise ValueError("Quantity must be a positive integer")

            if action_type == "Return":
                qty = -qty

            item_rent = next((item[1] for item in self.items if item[0] == item_name), None)

            self.transactions.append((date, item_name, qty, item_rent))
            self.transactions.sort(key=lambda x: x[0])  # Keep transactions sorted

            self.refresh_transaction_tree()

            self.date_entry.delete(0, "end")
            self.qty_entry.delete(0, "end")
            self.date_entry.focus()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def remove_transaction(self):
        """Remove the selected transaction"""
        selected = self.trans_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a transaction to remove")
            return

        if not messagebox.askyesno("Confirm", "Delete selected transaction?"):
            return

        index = self.trans_tree.index(selected[0])
        del self.transactions[index]
        self.refresh_transaction_tree()

    def refresh_transaction_tree(self):
        """Clears and re-populates the transaction treeview from self.transactions"""
        for i in self.trans_tree.get_children():
            self.trans_tree.delete(i)

        self.transactions.sort(key=lambda x: x[0])

        for date, item, qty, rent in self.transactions:
            action = "Rent" if qty > 0 else "Return"
            self.trans_tree.insert("", "end", values=(date, item, abs(qty), action))

    def clear_all(self, mess=True):
        """Clear all data and prepare for a new entry."""
        if mess and not messagebox.askyesno("Confirm", "Clear all data for a new customer? This cannot be undone."):
            return

        self.customer_id.set(self._generate_customer_id())
        self.customer_name.set("")
        self.customer_mobile.set("")
        self.customer_address.set("")
        self.previous_balance.set(0.0)
        self.payment_received.set(0.0)

        self.items.clear()
        for item in self.item_tree.get_children():
            self.item_tree.delete(item)

        self.transactions.clear()
        for item in self.trans_tree.get_children():
            self.trans_tree.delete(item)

        self.item_combo.configure(values=[])
        self.date_entry.focus()
        self.refresh_dashboard()

    def load_customer_data_dialog(self):
        """Load customer data from a JSON file using a file dialog."""
        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            title="Select Customer Data File",
            filetypes=[("JSON Files", "*.json")],
            initialdir="data"
        )
        if not file_path:
            return

        self.load_customer_data(file_path)

    def get_saved_customers(self):
        """Get list of saved customer data files"""
        return [f for f in os.listdir("data") if f.endswith(".json")]

    def update_in_hand_summary(self):
        """Refresh the In-Hand Quantity Summary"""
        summary = {}
        for date, item, qty, rent in self.transactions:
            if item not in summary:
                summary[item] = {"rented": 0, "returned": 0}
            if qty > 0:
                summary[item]["rented"] += qty
            else:
                summary[item]["returned"] += abs(qty)

        for item in self.in_hand_tree.get_children():
            self.in_hand_tree.delete(item)

        for item in self.items:
            item_name = item[0]
            rented = summary.get(item_name, {}).get("rented", 0)
            returned = summary.get(item_name, {}).get("returned", 0)
            in_hand = rented - returned
            self.in_hand_tree.insert("", "end", values=(item_name, rented, returned, in_hand))

    def create_metric_card(self, parent, title, value, color):
        """Helper method to create metric cards for dashboard"""
        card = ctk.CTkFrame(parent, border_width=1, border_color="#ddd", corner_radius=8)
        card.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(
            card,
            text=title,
            font=self.font_normal,
            text_color="#555"
        ).pack(pady=(10, 0))

        ctk.CTkLabel(
            card,
            text=str(value),
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=color
        ).pack(pady=(0, 10))
        return card

    def calculate_active_rentals(self):
        """Calculate number of currently rented items"""
        summary = {}
        for date, item, qty, rent in self.transactions:
            summary[item] = summary.get(item, 0) + qty
        return sum(1 for qty in summary.values() if qty > 0)

    def calculate_total_due(self):
        """Calculate total pending balance across all customers"""
        total = 0
        for filename in os.listdir("data"):
            if filename.endswith(".json"):
                with open(f"data/{filename}", "r") as f:
                    try:
                        data = json.load(f)
                        total += self.calculate_customer_due_from_data(data)
                    except json.JSONDecodeError:
                        continue
        return f"₹{total:,.2f}"

    def create_company_settings_tab(self, tab):
        """Create company settings tab"""
        self.company_name_var = ctk.StringVar(value=self.company_name)
        self.company_mobile_var = ctk.StringVar(value=self.company_mobile)
        self.company_address_var = ctk.StringVar(value=self.company_address)
        self.upi_id_var = ctk.StringVar(value=self.company_upi)

        fields = [
            ("Company Name:", self.company_name_var),
            ("Mobile Number:", self.company_mobile_var),
            ("Address:", self.company_address_var),
            ("UPI ID:", self.upi_id_var)
        ]

        for label, var in fields:
            frame = ctk.CTkFrame(tab, fg_color="transparent")
            frame.pack(fill="x", padx=10, pady=5)

            ctk.CTkLabel(frame, text=label, font=self.font_normal).pack(side="left", padx=5)
            entry = ctk.CTkEntry(frame, textvariable=var, font=self.font_normal)
            entry.pack(side="left", fill="x", expand=True)

    def load_selected_customer(self):
        """Load the selected customer from the dashboard treeview using their filename."""
        selected_items = self.customer_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select a customer first")
            return

        filename = selected_items[0]
        file_path = f"data/{filename}"

        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"Customer file not found: {file_path}")
            return

        self.load_customer_data(file_path)
        messagebox.showinfo("Loaded", f"Customer {self.customer_name.get()} loaded successfully.")
        self.tabview.set("Customer Info")

    def create_app_settings_tab(self, tab):
        """Create application settings tab"""
        self.theme_var = ctk.StringVar(value="light")
        self.color_theme_var = ctk.StringVar(value="blue")
        self.enable_qr_var = ctk.BooleanVar(value=True)

        # Theme selection
        frame = ctk.CTkFrame(tab, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(frame, text="Appearance Mode:", font=self.font_normal).pack(side="left", padx=5)
        ctk.CTkOptionMenu(
            frame,
            variable=self.theme_var,
            values=["light", "dark", "system"],
            font=self.font_normal
        ).pack(side="left", padx=5)

        # Color theme selection
        frame = ctk.CTkFrame(tab, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(frame, text="Color Theme:", font=self.font_normal).pack(side="left", padx=5)
        ctk.CTkOptionMenu(
            frame,
            variable=self.color_theme_var,
            values=["blue", "green", "dark-blue"],
            font=self.font_normal,

        ).pack(side="left", padx=5)

        # Enable QR in bills
        frame = ctk.CTkFrame(tab, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(frame, text="Include QR in Bills:", font=self.font_normal).pack(side="left", padx=5)
        ctk.CTkSwitch(
            frame,
            variable=self.enable_qr_var,
            text="",
            width=20
        ).pack(side="left", padx=5)


    def refresh_dashboard(self):
        """Refresh all dashboard widgets with current data"""
        for widget in self.dashboard_metrics_frame.winfo_children():
            widget.destroy()

        self.create_metric_card(
            self.dashboard_metrics_frame,
            "Total Customers",
            len(self.get_saved_customers()),
            "#2b579a"
        )
        self.create_metric_card(
            self.dashboard_metrics_frame,
            "Active Rentals",
            self.calculate_active_rentals(),
            "#5cb85c"
        )
        self.create_metric_card(
            self.dashboard_metrics_frame,
            "Total Due Amount",
            self.calculate_total_due(),
            "#f0ad4e"
        )
        self.create_metric_card(
            self.dashboard_metrics_frame,
            "Total Items",
            len(self.items) if self.items else 0,  # Handle case where items might not be loaded
            "#5bc0de"
        )

        self.filter_bills()
        self.update_in_hand_summary()

    def save_settings(self, settings_window):
        """Save settings and update the application"""
        self.company_name = self.company_name_var.get()
        self.company_mobile = self.company_mobile_var.get()
        self.company_address = self.company_address_var.get()
        self.company_upi = self.upi_id_var.get()

        settings = {
            "company": {
                "name": self.company_name,
                "mobile": self.company_mobile,
                "address": self.company_address,
                "upi_id": self.upi_id_var.get()
            },
            "appearance": {
                "theme": self.theme_var.get(),
                "color_theme": self.color_theme_var.get(),
            },
            "business": {
                "enable_qr": self.enable_qr_var.get(),
            }
        }

        with open("settings/config.json", "w") as f:
            json.dump(settings, f, indent=4)

        if messagebox.askyesno("Settings Saved", "Restart to apply all changes?"):
            settings_window.destroy()
            self.restart_application()
        else:
            ctk.set_appearance_mode(self.theme_var.get())
            ctk.set_default_color_theme(self.color_theme_var.get())
            self.update_header()
            settings_window.destroy()

    def restart_application(self):
        """Restart the application"""
        if getattr(sys, 'frozen', False):
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            subprocess.Popen([sys.executable] + sys.argv)
        self.quit()

    def open_settings(self):
        """Open the settings dialog"""
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("Settings")
        settings_window.resizable(False, False)
        settings_window.geometry("+650+200")
        settings_window.grab_set()

        tabview = ctk.CTkTabview(settings_window)
        tabview.pack(fill="both", expand=True, padx=10, pady=10)

        company_tab = tabview.add("Company")
        self.create_company_settings_tab(company_tab)

        app_tab = tabview.add("Application")
        self.create_app_settings_tab(app_tab)

        btn_frame = ctk.CTkFrame(settings_window, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        # In the btn_frame section of open_settings():
        ctk.CTkButton(
            btn_frame,
            text="📂 Load Data",
            command=self.load_customer_data_dialog,
            fg_color=self.primary_color,
            hover_color="#1e3f74",
            font=self.font_normal,
            corner_radius=8,
            height=40
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            command=settings_window.destroy,
            fg_color=self.danger_color,
            hover_color="#c9302c",
            width=120,
            height=35,
            font=self.font_normal
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Save Settings",
            command=lambda: self.save_settings(settings_window),
            fg_color=self.secondary_color,
            hover_color="#449d44",
            width=120,
            height=35,
            font=self.font_normal
        ).pack(side="right", padx=5)

    def update_header(self):
        """Update the header with current company info"""
        # This is a simplified update. A full update would require recreating the header.
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkFrame):
                        for label in child.winfo_children():
                            if isinstance(label, ctk.CTkLabel):
                                if self.company_name in label.cget("text"):
                                    label.configure(text=self.company_name)
                                elif "📱" in label.cget("text"):
                                    label.configure(text=f"📱 {self.company_mobile} | 📍 {self.company_address}")

    def load_settings(self):
        """Load settings from file if exists"""
        try:
            with open("settings/config.json", "r") as f:
                settings = json.load(f)

                company = settings.get("company", {})
                self.company_name = company.get("name", self.company_name)
                self.company_mobile = company.get("mobile", self.company_mobile)
                self.company_address = company.get("address", self.company_address)
                self.company_upi = company.get("upi_id", self.company_upi)

                appearance = settings.get("appearance", {})
                ctk.set_appearance_mode(appearance.get("theme", "light"))
                ctk.set_default_color_theme(appearance.get("color_theme", "blue"))

                business = settings.get("business", {})
                self.enable_qr = business.get("enable_qr", True)
        except (FileNotFoundError, json.JSONDecodeError):
            self.enable_qr = True

    def setup_keyboard_shortcuts(self):
        """Set up keyboard shortcuts for common actions"""
        self.bind('<Control-s>', lambda event: self.save_customer_data())
        self.bind('<Control-l>', lambda event: self.load_customer_data_dialog())
        self.bind('<Control-b>', lambda event: self.generate_bill())
        self.bind('<Control-n>', lambda event: self.clear_all())
        self.bind('<F1>', lambda event: self.open_settings())

        self.bind('<Alt-q>', lambda event: self.tabview.set("Dashboard"))
        self.bind('<Alt-w>', lambda event: self.tabview.set("Customer Info"))
        self.bind('<Alt-e>', lambda event: self.tabview.set("Rental Items"))
        self.bind('<Alt-t>', lambda event: self.tabview.set("Transactions"))

    def share_whatsapp(self):
        """Share bill via WhatsApp"""
        if not self.customer_name.get():
            messagebox.showerror("Error", "No customer loaded.")
            return

        total_rent, previous_balance, payment_received, amount = self.calculate_totals()
        pdf_path = self.create_pdf_bill(total_rent, previous_balance, payment_received, amount, self.enable_qr)

        try:
            image_path = self.convert_pdf_to_high_quality_image(pdf_path)
            if not image_path:
                raise Exception("Failed to convert bill to image.")

            upi_id = self.company_upi
            upi_url = f"upi://pay?pa={upi_id}&pn={self.company_name.replace(' ', '%20')}&am={amount:.2f}&cu=INR"
            note_text = f"""🧾 *{self.company_name} - Rental Payment Summary*

Hello *{self.customer_name.get()}*, 👋
Thank you for using our services. Below are your rental billing details:
🪪 *Customer ID:* {self.customer_id.get()}  
📅 *Bill Date:* {dt.date.today().strftime('%d-%b-%Y')}  
🗓️ *Rental Period:* {self.transactions[0][0].strftime('%d-%b-%Y')} to {self.transactions[-1][0].strftime('%d-%b-%Y')}

💰 *Total Amount:* ₹{payment_received + amount}  
💵 *Payment Received:* ₹{payment_received}  
💸 *Balance Due:* ₹{amount}  

🏦 *UPI ID:* `{upi_id}`  
🔗 *Pay Instantly:* {upi_url}

📌 *Note:* Please make the payment at your earliest convenience to avoid late charges.  
✅ Once paid, kindly confirm via WhatsApp.

If you've already settled the balance, please ignore this message.

Thanks again for choosing *{self.company_name}*. We truly appreciate your business! 🙏

Best regards,  
*{self.company_name}* 📍 {self.company_address}  
📞 {self.company_mobile}
"""

            phone = self.customer_mobile.get().strip()
            if not phone:
                raise ValueError("Customer phone number is required.")

            if not phone.startswith("+"):
                phone = "+91" + phone

            import pywhatkit
            messagebox.showinfo("Info", "Make sure WhatsApp Web is logged in. Sending in 120 seconds.")
            pywhatkit.sendwhats_image(receiver=phone, img_path=image_path, caption=note_text, wait_time=120)
            os.remove(image_path)

        except Exception as e:
            messagebox.showerror("WhatsApp Error", f"Failed to send via WhatsApp:\n{e}")

    def open_pop(self):
        selected = self.pdf_results_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select at least one file")
            return

        for item in selected:
            file_path = self.pdf_results_tree.item(item, "values")[4]
            try:
                # --- STEP 1: Open File Explorer and select the file ---
                abs_path = os.path.abspath(file_path)
                subprocess.Popen(f'explorer /select,"{abs_path}"')  # Focuses file
                time.sleep(0.5)  # Wait for Explorer
                # --- STEP 2: Simulate Shift+F10 (right-click) + S (Share) ---
                pyautogui.hotkey('shift', 'f10')  # Open context menu
                time.sleep(0.3)
                pyautogui.press('s')  # Press 'S' for Share
            except Exception as e:
                messagebox.showerror("Error", f"Could not open {file_path}:\n{str(e)}")


    def open_payment_ledger(self):
        """Open an enhanced payment ledger with improved UI/UX and functionality"""
        if not self.customer_id.get():
            messagebox.showwarning("Warning", "Please load or create a customer first")
            return

        # Create the ledger window
        self.ledger_window = ctk.CTkToplevel(self)
        self.ledger_window.title(f"💰 Payment Ledger - {self.customer_name.get()}")
        self.ledger_window.geometry("1400x800+100+30")
        self.ledger_window.minsize(1200, 750)
        self.ledger_window.transient(self)
        self.ledger_window.grab_set()

        # Configure main grid
        self.ledger_window.grid_columnconfigure(0, weight=1)
        self.ledger_window.grid_rowconfigure(1, weight=1)

        # ===== HEADER SECTION =====
        header_frame = ctk.CTkFrame(self.ledger_window, fg_color=self.primary_color, corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_columnconfigure(1, weight=1)

        # Customer Info Card
        cust_info_card = ctk.CTkFrame(header_frame, fg_color="#f8f9fa", corner_radius=8)
        cust_info_card.grid(row=0, column=0, padx=15, pady=10, sticky="w")

        ctk.CTkLabel(cust_info_card,
                     text=self.customer_name.get(),
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#2c3e50").pack(padx=10, pady=(5, 0), anchor="w")

        info_text = f"""
        ID: {self.customer_id.get()}
        Mobile: {self.customer_mobile.get()}
        Address: {self.customer_address.get()}
        """
        ctk.CTkLabel(cust_info_card,
                     text=info_text,
                     font=self.font_small,
                     text_color="#495057",
                     justify="left").pack(padx=10, pady=(0, 5), anchor="w")

        # Balance Summary Card
        balance_card = ctk.CTkFrame(header_frame, fg_color="#f8f9fa", corner_radius=8)
        balance_card.grid(row=0, column=1, padx=15, pady=10, sticky="e")

        # Calculate current balance
        total_rent, prev_bal, pay_recv, grand_total = self.calculate_totals()
        self.current_due_amount = grand_total

        balance_frame = ctk.CTkFrame(balance_card, fg_color="transparent")
        balance_frame.pack(padx=10, pady=5)

        ctk.CTkLabel(balance_frame,
                     text="BALANCE SUMMARY",
                     # font=self.font_small_bold,
                     text_color="#495057").grid(row=0, column=0, columnspan=2, sticky="w")

        # Current Balance
        ctk.CTkLabel(balance_frame,
                     text="Current Balance:",
                     font=self.font_small).grid(row=1, column=0, sticky="e", padx=5)

        self.balance_label = ctk.CTkLabel(balance_frame,
                                          text=f"₹{self.current_due_amount:,.2f}",
                                          font=ctk.CTkFont(size=16, weight="bold"),
                                          text_color="#d9534f" if self.current_due_amount > 0 else "#5cb85c")
        self.balance_label.grid(row=1, column=1, sticky="w", padx=5)

        # Total Paid
        ctk.CTkLabel(balance_frame,
                     text="Total Paid:",
                     font=self.font_small).grid(row=2, column=0, sticky="e", padx=5)

        self.paid_label = ctk.CTkLabel(balance_frame,
                                       text=f"₹{pay_recv:,.2f}",
                                       # font=self.font_small_bold,
                                       text_color="#5cb85c")
        self.paid_label.grid(row=2, column=1, sticky="w", padx=5)

        # ===== MAIN CONTENT AREA =====
        main_frame = ctk.CTkFrame(self.ledger_window)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        main_frame.grid_columnconfigure(0, weight=3)  # Transactions
        main_frame.grid_columnconfigure(1, weight=2)  # Summary/Charts
        main_frame.grid_rowconfigure(0, weight=1)

        # --- LEFT PANEL: Transactions ---
        left_panel = ctk.CTkFrame(main_frame, fg_color="transparent")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_panel.grid_rowconfigure(0, weight=1)  # Treeview
        left_panel.grid_rowconfigure(1, weight=0)  # Form
        left_panel.grid_columnconfigure(0, weight=1)

        # Transactions Treeview
        tree_frame = ctk.CTkFrame(left_panel, border_width=1, border_color="#dee2e6", corner_radius=8)
        tree_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Configure treeview style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Payment.Treeview",
                        background="#ffffff",
                        foreground="#2c3e50",
                        rowheight=35,
                        fieldbackground="#ffffff",
                        font=('Segoe UI', 11),
                        bordercolor="#dee2e6",
                        borderwidth=1)
        style.configure("Payment.Treeview.Heading",
                        background=self.primary_color,
                        foreground="white",
                        font=('Segoe UI', 11, 'bold'),
                        relief="flat")
        style.map("Payment.Treeview",
                  background=[('selected', '#3a6cb5')],
                  foreground=[('selected', 'white')])

        # Create treeview with simplified columns
        self.payment_tree = ttk.Treeview(
            tree_frame,
            columns=("ID", "Date", "Amount", "Method", "Reference", "Notes"),
            show="headings",
            style="Payment.Treeview",
            selectmode="extended"
        )

        # Configure columns
        columns = {
            "ID": {"width": 80, "anchor": "center"},
            "Date": {"width": 120, "anchor": "center"},
            "Amount": {"width": 120, "anchor": "e"},
            "Method": {"width": 120, "anchor": "center"},
            "Reference": {"width": 150, "anchor": "center"},
            "Notes": {"width": 250, "anchor": "w"}
        }

        for col, config in columns.items():
            self.payment_tree.heading(col, text=col)
            self.payment_tree.column(col, **config)

        # Add scrollbars
        y_scroll = ctk.CTkScrollbar(tree_frame, orientation="vertical", command=self.payment_tree.yview)
        x_scroll = ctk.CTkScrollbar(tree_frame, orientation="horizontal", command=self.payment_tree.xview)
        self.payment_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        # Grid the treeview and scrollbars
        self.payment_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        # Payment Entry Form (simplified)
        form_frame = ctk.CTkFrame(left_panel, border_width=1, border_color="#dee2e6", corner_radius=8)
        form_frame.grid(row=1, column=0, sticky="ew")
        form_frame.grid_columnconfigure(1, weight=1)
        form_frame.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(form_frame,
                     text="➕ Add New Payment",
                     font=self.font_normal_bold,
                     text_color=self.primary_color).grid(row=0, column=0, columnspan=4, sticky="w", padx=15,
                                                         pady=(10, 5))

        # Date Field
        ctk.CTkLabel(form_frame, text="Date:", font=self.font_normal).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        date_entry_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        date_entry_frame.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.payment_date_entry = ctk.CTkEntry(date_entry_frame, font=self.font_normal, height=36)
        self.payment_date_entry.pack(side="left", fill="x", expand=True)
        self.payment_date_entry.insert(0, dt.date.today().strftime("%Y-%m-%d"))

        ctk.CTkButton(date_entry_frame,
                      text="📅",
                      width=36,
                      height=36,
                      command=lambda: self.open_calendar(self.payment_date_entry)).pack(side="left", padx=5)

        # Amount Field
        ctk.CTkLabel(form_frame, text="Amount (₹):", font=self.font_normal).grid(row=1, column=2, padx=5, pady=5,
                                                                                 sticky="e")
        self.payment_amount_entry = ctk.CTkEntry(form_frame,
                                                 placeholder_text="0.00",
                                                 font=self.font_normal,
                                                 height=36)
        self.payment_amount_entry.grid(row=1, column=3, padx=5, pady=5, sticky="ew")

        # Method Field
        ctk.CTkLabel(form_frame, text="Method:", font=self.font_normal).grid(row=2, column=0, padx=5, pady=5,
                                                                             sticky="e")
        self.payment_method_combo = ctk.CTkComboBox(
            form_frame,
            values=["Cash", "UPI", "Bank Transfer", "Online Payment", "Other"],
            state="readonly",
            font=self.font_normal,
            height=36
        )
        self.payment_method_combo.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.payment_method_combo.set("Cash")

        # Reference Field
        ctk.CTkLabel(form_frame, text="Reference:", font=self.font_normal).grid(row=2, column=2, padx=5, pady=5,
                                                                                sticky="e")
        self.payment_reference_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Transaction ID/Check No.",
            font=self.font_normal,
            height=36
        )
        self.payment_reference_entry.grid(row=2, column=3, padx=5, pady=5, sticky="ew")

        # Notes Field
        ctk.CTkLabel(form_frame, text="Notes:", font=self.font_normal).grid(row=3, column=0, padx=5, pady=5,
                                                                            sticky="ne")
        self.payment_notes_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Additional payment details",
            font=self.font_normal,
            height=36
        )
        self.payment_notes_entry.grid(row=3, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        # --- RIGHT PANEL: Summary and Analytics ---
        right_panel = ctk.CTkFrame(main_frame, border_width=1, border_color="#dee2e6", corner_radius=8)
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        # Summary Header
        ctk.CTkLabel(right_panel,
                     text="📊 Payment Analytics",
                     font=self.font_subheading,
                     text_color=self.primary_color).grid(row=0, column=0, sticky="ew", padx=15, pady=10)

        # Metrics Cards
        metrics_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        metrics_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Create 4 metric cards in a 2x2 grid
        self.metric_cards = []
        metric_info = [
            {"title": "Total Payments", "color": self.primary_color, "icon": "💰"},
            {"title": "Payment Count", "color": self.secondary_color, "icon": "🔢"},
            {"title": "Avg. Payment", "color": self.accent_color, "icon": "📈"},
            {"title": "Last Payment", "color": self.info_color, "icon": "🔄"}
        ]

        for i, metric in enumerate(metric_info):
            row = i // 2
            col = i % 2
            metrics_frame.grid_columnconfigure(col, weight=1)

            card = ctk.CTkFrame(metrics_frame,
                                border_width=1,
                                border_color="#e0e0e0",
                                corner_radius=8)
            card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5, ipadx=5, ipady=5)

            # Card content
            ctk.CTkLabel(card,
                         text=f"{metric['icon']} {metric['title']}",
                         font=self.font_small,
                         text_color="#495057").pack(pady=(5, 0))

            value_label = ctk.CTkLabel(card,
                                       text="--",
                                       font=ctk.CTkFont(size=16, weight="bold"),
                                       text_color=metric['color'])
            value_label.pack(pady=(0, 5))

            self.metric_cards.append(value_label)

        # Payment Method Distribution
        method_frame = ctk.CTkFrame(right_panel, border_width=1, border_color="#e0e0e6", corner_radius=8)
        method_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        method_frame.grid_columnconfigure(0, weight=1)
        method_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(method_frame,
                     text="Payment Method Distribution",
                     font=self.font_normal_bold,
                     text_color=self.primary_color).grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))

        self.method_chart_frame = ctk.CTkFrame(method_frame, fg_color="white", corner_radius=6)
        self.method_chart_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10), ipady=10)

        # ===== ACTION BUTTONS =====
        btn_frame = ctk.CTkFrame(self.ledger_window, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        # Left-side buttons
        left_btn_frame = ctk.CTkFrame(btn_frame, fg_color="transparent")
        left_btn_frame.pack(side="left", fill="x", expand=True)

        btn_style = {"height": 40, "font": self.font_normal, "corner_radius": 8}

        ctk.CTkButton(left_btn_frame,
                      text="💰 Pay Full Balance",
                      command=self._pay_full_balance,
                      fg_color="#28a745",
                      hover_color="#218838",
                      **btn_style).pack(side="left", padx=5)

        self.add_payment_btn = ctk.CTkButton(left_btn_frame,
                                             text="➕ Add Payment",
                                             command=self._add_payment_entry,
                                             fg_color=self.secondary_color,
                                             hover_color="#449d44",
                                             **btn_style)
        self.add_payment_btn.pack(side="left", padx=5)

        ctk.CTkButton(left_btn_frame,
                      text="✏️ Edit Selected",
                      command=self._edit_payment_entry,
                      fg_color=self.accent_color,
                      hover_color="#ec971f",
                      **btn_style).pack(side="left", padx=5)

        ctk.CTkButton(left_btn_frame,
                      text="🗑️ Delete Selected",
                      command=self._delete_payment_entry,
                      fg_color=self.danger_color,
                      hover_color="#c9302c",
                      **btn_style).pack(side="left", padx=5)

        # Right-side buttons
        right_btn_frame = ctk.CTkFrame(btn_frame, fg_color="transparent")
        right_btn_frame.pack(side="right")

        ctk.CTkButton(right_btn_frame,
                      text="🖨️ Print Receipt",
                      command=self._print_payment_receipt,
                      fg_color="#6c757d",
                      hover_color="#5a6268",
                      **btn_style).pack(side="left", padx=5)

        ctk.CTkButton(right_btn_frame,
                      text="💾 Save & Close",
                      command=lambda: self._save_payment_ledger(self.ledger_window),
                      fg_color=self.primary_color,
                      hover_color="#1e3f74",
                      width=140,
                      **btn_style).pack(side="left", padx=5)

        # ===== STATUS BAR =====
        status_bar = ctk.CTkFrame(self.ledger_window, height=30, corner_radius=0, fg_color="#f8f9fa")
        status_bar.grid(row=3, column=0, sticky="ew")

        self.payment_status_var = ctk.StringVar(value="🟢 Ready")
        ctk.CTkLabel(status_bar,
                     textvariable=self.payment_status_var,
                     font=self.font_small,
                     text_color="#666",
                     anchor="w").pack(side="left", padx=15)

        # ===== INITIALIZE DATA =====
        self.ledger_window.bind("<Return>", lambda e: self._add_payment_entry())
        self._refresh_ledger_data(self.ledger_window)
        self.payment_amount_entry.focus()

    def _refresh_ledger_data(self, ledger_window):
        """Refresh all data in the payment ledger"""
        self.payment_status_var.set("⏳ Loading payment data...")
        ledger_window.update_idletasks()

        try:
            # Clear existing data
            for item in self.payment_tree.get_children():
                self.payment_tree.delete(item)

            # Load customer data
            cust_id = self.customer_id.get()
            if not cust_id:
                return

            file_path = f"data/{cust_id}.json"
            if not os.path.exists(file_path):
                return

            with open(file_path, "r") as f:
                data = json.load(f)

            # Update payment received and balance
            payment_received = data.get("payment_received", 0)
            self.payment_received.set(payment_received)

            # Calculate current due
            total_rent, prev_bal, pay_recv, grand_total = self.calculate_totals()
            self.current_due_amount = grand_total

            # Update balance display
            self.balance_label.configure(text=f"₹{self.current_due_amount:,.2f}")
            self.balance_label.configure(text_color="#d9534f" if self.current_due_amount > 0 else "#5cb85c")
            self.paid_label.configure(text=f"₹{pay_recv:,.2f}")

            # Load payment history
            payments = data.get("payment_history", [])
            total_amount = 0
            method_counts = {}
            payment_dates = []

            for payment in payments:
                try:
                    # Generate a unique ID for each payment if not exists
                    payment_id = payment.get("id", str(uuid.uuid4())[:8])
                    date = payment.get("date", "")
                    amount = float(payment.get("amount", 0))
                    method = payment.get("method", "Cash")
                    reference = payment.get("reference", "")
                    notes = payment.get("notes", "")

                    # Add to treeview
                    self.payment_tree.insert("", "end",
                                             values=(payment_id,
                                                     date,
                                                     f"₹{amount:,.2f}",
                                                     method,
                                                     reference,
                                                     notes))

                    # Update totals
                    total_amount += amount

                    # Track method counts
                    method_counts[method] = method_counts.get(method, 0) + 1

                    # Track dates
                    try:
                        payment_dates.append(dt.datetime.strptime(date, "%Y-%m-%d").date())
                    except:
                        pass

                except Exception as e:
                    print(f"Error loading payment: {e}")
                    continue

            # Update metrics
            payment_count = len(payments)
            avg_payment = total_amount / payment_count if payment_count > 0 else 0
            last_payment = max(payment_dates).strftime("%d-%b-%Y") if payment_dates else "N/A"

            # Update the metric cards
            if hasattr(self, 'metric_cards') and len(self.metric_cards) >= 4:
                self.metric_cards[0].configure(text=f"₹{total_amount:,.2f}")
                self.metric_cards[1].configure(text=str(payment_count))
                self.metric_cards[2].configure(text=f"₹{avg_payment:,.2f}")
                self.metric_cards[3].configure(text=last_payment)

            # Update method distribution chart
            self._update_method_chart(method_counts)

            self.payment_status_var.set("🟢 Data loaded successfully")

        except Exception as e:
            self.payment_status_var.set(f"🔴 Error loading data: {str(e)}")
            messagebox.showerror("Error", f"Failed to load payment data:\n{str(e)}", parent=ledger_window)

    def _update_method_chart(self, method_counts):
        """Update the payment method distribution visualization with amounts"""
        # Clear previous chart content
        for widget in self.method_chart_frame.winfo_children():
            widget.destroy()

        if not method_counts:
            ctk.CTkLabel(
                self.method_chart_frame,
                text="No payment data to display.",
                font=self.font_normal,
                text_color="#888"
            ).pack(expand=True, pady=20)
            return

        # Calculate total amount and amounts by method
        total_amount = 0
        method_amounts = {}

        # Get all payments from the treeview
        for item in self.payment_tree.get_children():
            values = self.payment_tree.item(item, "values")
            try:
                method = values[3]  # Method is in column 3
                amount_str = values[2].replace("₹", "").replace(",", "")  # Amount is in column 2
                amount = float(amount_str)

                method_amounts[method] = method_amounts.get(method, 0) + amount
                total_amount += amount
            except (ValueError, IndexError):
                continue

        if total_amount == 0:
            ctk.CTkLabel(
                self.method_chart_frame,
                text="No payment data to display.",
                font=self.font_normal,
                text_color="#888"
            ).pack(expand=True, pady=20)
            return

        # Use a grid layout inside the chart frame for better alignment
        self.method_chart_frame.grid_columnconfigure(1, weight=1)

        # Create a bar for each method, sorted by amount
        for i, (method, amount) in enumerate(sorted(method_amounts.items(), key=lambda x: x[1], reverse=True)):
            # Calculate percentage
            percentage = amount / total_amount
            count = method_counts.get(method, 0)

            # Method Label with count
            method_label = ctk.CTkLabel(
                self.method_chart_frame,
                text=f"{method} ({count})",  # Show method name and count
                font=self.font_small,
                anchor="w"
            )
            method_label.grid(row=i, column=0, sticky="w", padx=(5, 10), pady=4)

            # Progress Bar
            progress_bar = ctk.CTkProgressBar(
                self.method_chart_frame,
                height=12,
                corner_radius=6,
                progress_color=self._get_method_color(method)
            )
            progress_bar.set(percentage)
            progress_bar.grid(row=i, column=1, sticky="ew", padx=5, pady=4)

            # Value Label (Amount and Percentage)
            value_label = ctk.CTkLabel(
                self.method_chart_frame,
                text=f"₹{amount:,.2f} ({percentage:.1%})",  # Format as currency and percentage
                font=self.font_small,
                anchor="e"
            )
            value_label.grid(row=i, column=2, sticky="e", padx=(10, 5), pady=4)
    def _get_method_color(self, method):
        """Get consistent color for each payment method"""
        colors = {
            "Cash": "#51cf66",
            "UPI": "#339af0",
            "Bank Transfer": "#9775fa",
            "Cheque": "#fcc419",
            "Credit Card": "#e64980",
            "Online Payment": "#f76707",
            "Other": "#adb5bd"
        }
        return colors.get(method, "#adb5bd")

    def _add_payment_entry(self):
        """Add a new payment entry with validation"""
        try:
            # Validate date
            date_str = self.payment_date_entry.get().strip()
            if not date_str:
                raise ValueError("Payment date is required")

            try:
                payment_date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
                if payment_date > dt.date.today():
                    raise ValueError("Future dates are not allowed")
            except ValueError:
                raise ValueError("Invalid date format (YYYY-MM-DD)")

            # Validate amount
            amount_str = self.payment_amount_entry.get().strip()
            if not amount_str:
                raise ValueError("Payment amount is required")

            try:
                amount = float(amount_str)
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except ValueError:
                raise ValueError("Invalid amount format")

            # Check if payment exceeds balance
            if hasattr(self, 'current_due_amount') and amount > self.current_due_amount:
                if not messagebox.askyesno("Confirm Overpayment",
                                           f"Payment amount (₹{amount:,.2f}) exceeds current balance (₹{self.current_due_amount:,.2f}).\n"
                                           "Do you want to proceed anyway?",
                                           parent=self.payment_tree.winfo_toplevel()):
                    return

            # Get other fields
            method = self.payment_method_combo.get()
            if not method:
                raise ValueError("Payment method is required")


            reference = self.payment_reference_entry.get().strip()
            notes = self.payment_notes_entry.get().strip()

            # Generate unique payment ID
            payment_id = str(uuid.uuid4())[:8]

            # Add to treeview
            self.payment_tree.insert("", "end",
                                     values=(payment_id,
                                             date_str,
                                             f"₹{amount:,.2f}",
                                             method,
                                             reference,
                                             notes))

            # Scroll to new entry
            self.payment_tree.see(self.payment_tree.get_children()[-1])

            # Clear form fields
            self.payment_amount_entry.delete(0, "end")
            self.payment_reference_entry.delete(0, "end")
            self.payment_notes_entry.delete(0, "end")

            # Update status
            self.payment_status_var.set(f"Added payment of ₹{amount:,.2f}")

            # Update summary

            # Focus back to amount field
            self.payment_amount_entry.focus()

        except Exception as e:
            self.payment_status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Payment Error", str(e), parent=self.payment_tree.winfo_toplevel())

    def _pay_full_balance(self):
        """Pre-fill form with full balance payment"""
        if not hasattr(self, 'current_due_amount') or self.current_due_amount <= 0:
            messagebox.showinfo("Info", "No outstanding balance to pay",
                                parent=self.payment_tree.winfo_toplevel())
            return

        self.payment_amount_entry.delete(0, "end")
        self.payment_amount_entry.insert(0, f"{self.current_due_amount:.2f}")
        self.payment_date_entry.delete(0, "end")
        self.payment_date_entry.insert(0, dt.date.today().strftime("%Y-%m-%d"))
        self.payment_method_combo.set("Cash")
        self.payment_notes_entry.delete(0, "end")
        self.payment_notes_entry.insert(0, "Full payment of outstanding balance")

        self.payment_status_var.set(f"Ready to pay full balance of ₹{self.current_due_amount:,.2f}")
        self.payment_reference_entry.focus()

    def _edit_payment_entry(self):
        """Edit the selected payment entry directly in the ledger"""
        selected = self.payment_tree.selection()
        if not selected or len(selected) > 1:
            messagebox.showwarning("Warning", "Please select a single payment to edit",
                                   parent=self.payment_tree.winfo_toplevel())
            return

        item = selected[0]
        values = self.payment_tree.item(item, "values")

        # Store the original values for reference
        self._editing_payment_item = item
        self._original_payment_values = values

        # Pre-fill the form with selected payment's values
        self.payment_date_entry.delete(0, "end")
        self.payment_date_entry.insert(0, values[1])  # Date

        self.payment_amount_entry.delete(0, "end")
        self.payment_amount_entry.insert(0, values[2].replace("₹", "").replace(",", ""))  # Amount

        self.payment_method_combo.set(values[3])  # Method

        self.payment_reference_entry.delete(0, "end")
        self.payment_reference_entry.insert(0, values[4])  # Reference

        self.payment_notes_entry.delete(0, "end")
        self.payment_notes_entry.insert(0, values[5])  # Notes

        # Change the Add button to Update temporarily
        for widget in self.ledger_window.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkFrame):
                        for btn in child.winfo_children():
                            if isinstance(btn, ctk.CTkButton) and btn.cget("text") == "➕ Add Payment":
                                btn.configure(text="🔄 Update",
                                              command=self._update_payment_entry,
                                              fg_color=self.accent_color,
                                              hover_color="#ec971f")
                                self._add_payment_btn = btn  # Store reference to restore later

        self.payment_status_var.set(f"Editing payment {values[0]} - Click Update to save changes")
        self.payment_amount_entry.focus()

    def _update_payment_entry(self):
        """Update the payment entry with form values"""
        try:
            if not hasattr(self, '_editing_payment_item'):
                raise ValueError("No payment selected for editing")

            item = self._editing_payment_item
            original_values = self._original_payment_values

            # Get values from form
            date_str = self.payment_date_entry.get().strip()
            if not date_str:
                raise ValueError("Payment date is required")

            try:
                payment_date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
                if payment_date > dt.date.today():
                    raise ValueError("Future dates are not allowed")
            except ValueError:
                raise ValueError("Invalid date format (YYYY-MM-DD)")

            amount_str = self.payment_amount_entry.get().strip()
            if not amount_str:
                raise ValueError("Payment amount is required")

            try:
                amount = float(amount_str)
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except ValueError:
                raise ValueError("Invalid amount format")

            method = self.payment_method_combo.get()
            if not method:
                raise ValueError("Payment method is required")

            reference = self.payment_reference_entry.get().strip()
            notes = self.payment_notes_entry.get().strip()

            # Keep the original payment ID
            payment_id = original_values[0]

            # Update treeview
            self.payment_tree.item(item, values=(
                payment_id,
                date_str,
                f"₹{amount:,.2f}",
                method,
                reference,
                notes
            ))

            # Clear form and reset button
            self._reset_payment_form()

            self.payment_status_var.set(f"Payment {payment_id} updated successfully")

        except Exception as e:
            self.payment_status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Update Error", str(e), parent=self.payment_tree.winfo_toplevel())

    def _reset_payment_form(self):
        """Reset the payment form to its default state"""
        self.payment_date_entry.delete(0, "end")
        self.payment_date_entry.insert(0, dt.date.today().strftime("%Y-%m-%d"))
        self.payment_amount_entry.delete(0, "end")
        self.payment_method_combo.set("Cash")
        self.payment_reference_entry.delete(0, "end")
        self.payment_notes_entry.delete(0, "end")

        # Restore the Add button if it was changed
        if hasattr(self, '_add_payment_btn'):
            self._add_payment_btn.configure(text="➕ Add Payment",
                                            command=self._add_payment_entry,
                                            fg_color=self.secondary_color,
                                            hover_color="#449d44")

        # Clear editing references
        if hasattr(self, '_editing_payment_item'):
            del self._editing_payment_item
        if hasattr(self, '_original_payment_values'):
            del self._original_payment_values

        self.payment_status_var.set("🟢 Ready")
        self.payment_amount_entry.focus()

    def _delete_payment_entry(self):
        """Delete selected payment entries"""
        selected = self.payment_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select payment(s) to delete",
                                   parent=self.payment_tree.winfo_toplevel())
            return

        # Calculate total amount being deleted
        total_amount = 0
        for item in selected:
            amount_str = self.payment_tree.item(item, "values")[2].replace("₹", "").replace(",", "")
            total_amount += float(amount_str)

        if messagebox.askyesno("Confirm Deletion",
                               f"Delete {len(selected)} payment(s) totaling ₹{total_amount:,.2f}?\n"
                               "This action cannot be undone.",
                               parent=self.payment_tree.winfo_toplevel()):
            for item in selected:
                self.payment_tree.delete(item)

            self.payment_status_var.set(f"Deleted {len(selected)} payment(s)")

    def _print_payment_receipt(self):
        """Generate a professional thermal printer style receipt"""
        selected = self.payment_tree.selection()
        if not selected or len(selected) > 1:
            messagebox.showwarning("Warning", "Please select a single payment to print receipt",
                                   parent=self.payment_tree.winfo_toplevel())
            return

        item = selected[0]
        values = self.payment_tree.item(item, "values")

        # Create PDF with thermal printer dimensions (80mm wide)
        pdf = FPDF(orientation='P', unit='mm', format=(80, 297))  # 80mm wide, length as needed
        pdf.add_page()

        # Configure fonts - prioritize monospace for thermal look
        try:
            # Try to load actual thermal printer fonts if available
            pdf.add_font("Thermal", "", "thermal-regular.ttf")
            pdf.add_font("Thermal", "B", "thermal-bold.ttf")
            font_name = "Thermal"
        except:
            try:
                # Fallback to Courier if thermal fonts not available
                pdf.add_font("Courier", "", "cour.ttf")
                pdf.add_font("Courier", "B", "courbd.ttf")
                font_name = "Courier"
            except:
                # Final fallback to built-in font
                font_name = "Courier"

        # Set narrow margins (5mm left/right, 5mm top)
        pdf.set_margins(left=5, top=5, right=5)
        pdf.set_auto_page_break(False)

        # --- HEADER SECTION ---
        # Company logo (if available)
        try:
            logo_path = "logo.png"
            if os.path.exists(logo_path):
                pdf.image(logo_path, x=20, y=5, w=40)  # Center 40mm wide logo
                pdf.set_y(20)  # Position after logo
        except:
            pass

        # Company info (centered)
        pdf.set_font(font_name, "B", 10)
        pdf.cell(0, 5, self.company_name.upper(), 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        pdf.set_font(font_name, "", 8)
        pdf.cell(0, 4, self.company_address, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        pdf.cell(0, 4, f"Tel: {self.company_mobile}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        pdf.cell(0, 4, "GSTIN: XXXXXXXX" if hasattr(self, 'company_gst') else "",
                 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

        # Double divider line
        pdf.set_draw_color(0, 0, 0)
        pdf.set_line_width(0.4)
        pdf.line(5, pdf.get_y(), 75, pdf.get_y())
        pdf.ln(2)
        pdf.line(5, pdf.get_y(), 75, pdf.get_y())
        pdf.ln(5)

        # --- RECEIPT TITLE ---
        pdf.set_font(font_name, "B", 12)
        pdf.cell(0, 6, "PAYMENT RECEIPT", 0, 1, "C")
        pdf.set_font(font_name, "", 8)
        pdf.cell(0, 4, "ORIGINAL COPY", 0, 1, "C")
        pdf.ln(3)

        # --- RECEIPT INFO ---
        col1_width = 25
        col2_width = 45

        # Receipt metadata
        pdf.set_font(font_name, "B", 9)
        pdf.cell(col1_width, 5, "Receipt No:", 0, 0)
        pdf.set_font(font_name, "", 9)
        pdf.cell(col2_width, 5, f"#{values[0]}", 0, 1)

        pdf.set_font(font_name, "B", 9)
        pdf.cell(col1_width, 5, "Date/Time:", 0, 0)
        pdf.set_font(font_name, "", 9)
        pdf.cell(col2_width, 5, dt.datetime.now().strftime("%d-%m-%Y %H:%M:%S"), 0, 1)

        # Customer info
        pdf.ln(3)
        pdf.set_font(font_name, "B", 10)
        pdf.cell(0, 6, "CUSTOMER DETAILS", 0, 1)
        pdf.set_font(font_name, "", 9)

        pdf.cell(col1_width, 5, "Name:", 0, 0)
        pdf.cell(col2_width, 5, self.customer_name.get(), 0, 1)

        pdf.cell(col1_width, 5, "Mobile:", 0, 0)
        pdf.cell(col2_width, 5, self.customer_mobile.get(), 0, 1)

        pdf.cell(col1_width, 5, "Address:", 0, 0)
        pdf.multi_cell(col2_width, 5, self.customer_address.get())

        # Divider
        pdf.ln(3)
        pdf.line(5, pdf.get_y(), 75, pdf.get_y())
        pdf.ln(5)

        # --- PAYMENT DETAILS ---
        pdf.set_font(font_name, "B", 10)
        pdf.cell(0, 6, "PAYMENT INFORMATION", 0, 1)
        pdf.set_font(font_name, "", 9)

        # Payment details table
        table_col1 = 30
        table_col2 = 40

        pdf.cell(table_col1, 5, "Payment Date:", 0, 0)
        pdf.cell(table_col2, 5, values[1], 0, 1)

        pdf.cell(table_col1, 5, "Amount Paid:", 0, 0)
        pdf.set_font(font_name, "B", 10)
        pdf.cell(table_col2, 5, values[2].replace("₹",''), 0, 1)
        pdf.set_font(font_name, "", 9)

        pdf.cell(table_col1, 5, "Payment Method:", 0, 0)
        pdf.cell(table_col2, 5, values[3].upper(), 0, 1)

        pdf.cell(table_col1, 5, "Reference:", 0, 0)
        pdf.cell(table_col2, 5, values[4], 0, 1)

        # Notes if available
        if values[5]:
            pdf.ln(3)
            pdf.cell(table_col1, 5, "Notes:", 0, 0)
            pdf.multi_cell(table_col2, 5, values[5])

        # Double divider
        pdf.ln(5)
        pdf.line(5, pdf.get_y(), 75, pdf.get_y())
        pdf.ln(2)
        pdf.line(5, pdf.get_y(), 75, pdf.get_y())
        pdf.ln(5)

        # --- FOOTER ---
        pdf.set_font(font_name, "I", 8)
        pdf.cell(0, 4, "Thank you for your business!", 0, 1, "C")
        pdf.cell(0, 4, "Please retain this receipt for your records", 0, 1, "C")

        # Terms and conditions
        pdf.ln(3)
        pdf.set_font(font_name, "", 7)
        pdf.multi_cell(0, 3, "Terms: Goods sold are not returnable. Warranty as per manufacturer policy.")

        # Barcode with receipt number (optional)
        try:
            pdf.ln(5)
            # Generate Code 39 barcode
            pdf.code39(f"*{values[0]}*", x=20, y=pdf.get_y(), w=0.5, h=12)
            pdf.set_y(pdf.get_y() + 15)
        except:
            pass

        # Final print timestamp
        pdf.set_font(font_name, "", 7)
        pdf.cell(0, 3, f"Printed: {dt.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}", 0, 1, "C")

        # --- CUTTING LINE FOR THERMAL PRINTERS ---
        pdf.set_draw_color(0, 0, 0)
        pdf.set_line_width(0.2)
        pdf.set_dash_pattern(dash=1, gap=1)  # Dashed line for cutting guide
        pdf.line(5, pdf.get_y(), 75, pdf.get_y())

        # Save PDF
        receipt_dir = "receipts"
        os.makedirs(receipt_dir, exist_ok=True)
        receipt_path = f"{receipt_dir}/Receipt_{values[0]}.pdf"
        pdf.output(receipt_path)

        # Open the PDF automatically
        receipt_dir = "receipts"
        try:
            # Create receipts directory if it doesn't exist
            os.makedirs(receipt_dir, exist_ok=True)

            receipt_path = os.path.join(receipt_dir, f"Receipt_{values[0]}.pdf")
            pdf.output(receipt_path)

            # Verify file was created before trying to open it
            if os.path.exists(receipt_path):
                try:
                    os.startfile(receipt_path)
                except Exception as e:
                    messagebox.showinfo("Receipt Generated",
                                        f"Professional receipt saved as:\n{receipt_path}\n"
                                        f"Could not open automatically: {str(e)}",
                                        parent=self.payment_tree.winfo_toplevel())
            else:
                messagebox.showerror("Error", "Failed to create receipt file",
                                     parent=self.payment_tree.winfo_toplevel())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save receipt: {str(e)}",
                                 parent=self.payment_tree.winfo_toplevel())

    def _save_payment_ledger(self, window):
        """Save payment data with simplified structure"""
        try:
            cust_id = self.customer_id.get()
            cust_name = self.customer_name.get()
            if not cust_name:
                raise ValueError("No customer selected")

            file_path = f"data/{cust_id}.json"
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = {}

            # Prepare payment history (simplified without type/status)
            payments = []
            total_received = 0.0

            for item in self.payment_tree.get_children():
                values = self.payment_tree.item(item, "values")
                try:
                    amount = float(values[2].replace("₹", "").replace(",", ""))
                    payment = {
                        "id": values[0],
                        "date": values[1],
                        "amount": amount,
                        "method": values[3],
                        "reference": values[4],
                        "notes": values[5]
                    }

                    payments.append(payment)
                    total_received += amount

                except Exception as e:
                    print(f"Error processing payment: {e}")
                    continue

            # Update customer data
            data["payment_history"] = payments
            data["payment_received"] = total_received

            # Save to file
            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)

            # Update main application
            self.payment_received.set(total_received)

            messagebox.showinfo("Saved",
                                f"Payment ledger saved successfully for {self.customer_name.get()}",
                                parent=window)
            window.destroy()

        except Exception as e:
            messagebox.showerror("Save Error",
                                 f"Failed to save payment ledger:\n{str(e)}",
                                 parent=window)

    def load_customer_data(self, file_path):
        """Loads customer data from a specific JSON file path."""
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            self.clear_all(mess=False)

            self.customer_id.set(data.get("customer_id", self._generate_customer_id()))
            self.customer_name.set(data.get("name", ""))
            self.customer_mobile.set(data.get("mobile", ""))
            self.customer_address.set(data.get("address", ""))
            self.previous_balance.set(data.get("previous_balance", 0.0))
            self.payment_received.set(data.get("payment_received", 0.0))

            self.items = data.get("items", [])
            for item in self.items:
                self.item_tree.insert("", "end", values=(item[0], f"₹{item[1]:.2f}"))
            self.item_combo.configure(values=[item[0] for item in self.items])

            self.transactions = []
            for tx in data.get("transactions", []):
                date_obj = dt.datetime.strptime(tx["date"], "%Y-%m-%d").date()
                self.transactions.append((date_obj, tx["item"], tx["qty"], tx["rent"]))

            self.refresh_transaction_tree()
            self.update_in_hand_summary()

        except FileNotFoundError:
            messagebox.showerror("Error", f"Could not find the file: {file_path}")
        except json.JSONDecodeError:
            messagebox.showerror("Error", f"File is not a valid JSON file: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def save_customer_data(self):
        """Save customer data to a JSON file named after the customer ID."""
        cust_id = self.customer_id.get().strip()
        name = self.customer_name.get().strip()

        if not cust_id:
            messagebox.showerror("Error", "Customer ID is missing. Cannot save.")
            return

        if not name:
            messagebox.showerror("Error", "Customer name is required to save data.")
            return

        # Try to load existing payment history if file exists
        payment_history = []
        file_path = f"data/{cust_id}.json"
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    existing_data = json.load(f)
                    payment_history = existing_data.get("payment_history", [])
            except:
                pass

        data = {
            "customer_id": cust_id,
            "name": name,
            "mobile": self.customer_mobile.get(),
            "address": self.customer_address.get(),
            "previous_balance": self.previous_balance.get(),
            "payment_received": self.payment_received.get(),
            "payment_history": payment_history,  # Include existing payment history
            "items": self.items,
            "transactions": [
                {"date": str(date), "item": item, "qty": qty, "rent": rent}
                for (date, item, qty, rent) in self.transactions
            ]
        }

        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)

        messagebox.showinfo("Saved", f"Customer data saved successfully to '{cust_id}.json'")
        self.refresh_dashboard()


    def open_pdf_search(self):
        """Open enhanced PDF search dialog with preview and batch operations"""
        search_window = ctk.CTkToplevel(self)
        search_window.title("🔍 Advanced PDF Search")
        search_window.geometry("1200x800+250+35")
        search_window.minsize(1000, 700)
        search_window.transient(self)
        search_window.grab_set()

        # Configure grid layout
        search_window.grid_columnconfigure(0, weight=1)
        search_window.grid_rowconfigure(1, weight=1)

        # ===== SEARCH FILTERS PANEL =====
        filter_frame = ctk.CTkFrame(search_window, border_width=1, border_color="#ddd", corner_radius=8)
        filter_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        filter_frame.grid_columnconfigure(1, weight=1)

        # Search term with icon
        search_row = ctk.CTkFrame(filter_frame, fg_color="transparent")
        search_row.grid(row=0, column=0, columnspan=3, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(search_row, text="🔍", font=self.font_normal).pack(side="left", padx=(5, 0))
        self.pdf_search_entry = ctk.CTkEntry(
            search_row,
            placeholder_text="Search by filename or customer name...",
            font=self.font_normal
        )
        self.pdf_search_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.pdf_search_entry.bind("<Return>", lambda e: self._perform_pdf_search())
        # Advanced filters
        adv_filter_frame = ctk.CTkFrame(filter_frame, fg_color="transparent")
        adv_filter_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        # Date range
        date_frame = ctk.CTkFrame(adv_filter_frame, fg_color="transparent")
        date_frame.pack(side="left", padx=5)
        ctk.CTkLabel(date_frame, text="📅 Date Range:").pack(side="left")
        self.pdf_from_date = ctk.CTkEntry(date_frame, placeholder_text="From", width=100)
        self.pdf_from_date.pack(side="left", padx=5)
        ctk.CTkButton(date_frame, text="▼", width=30,
                      command=lambda: self.open_calendar(self.pdf_from_date)).pack(side="left", padx=2)

        self.pdf_to_date = ctk.CTkEntry(date_frame, placeholder_text="To", width=100)
        self.pdf_to_date.pack(side="left", padx=5)
        ctk.CTkButton(date_frame, text="▼", width=30,
                      command=lambda: self.open_calendar(self.pdf_to_date)).pack(side="left", padx=2)

        # File type filter
        type_frame = ctk.CTkFrame(adv_filter_frame, fg_color="transparent")
        type_frame.pack(side="left", padx=10)

        ctk.CTkLabel(type_frame, text="📄 Type:").pack(side="left")
        self.pdf_type_combo = ctk.CTkComboBox(
            type_frame,
            values=["All", "Bills", "Receipts"],
            state="readonly",
            width=100
        )
        self.pdf_type_combo.set("All")
        self.pdf_type_combo.pack(side="left", padx=5)
        # Size filter
        size_frame = ctk.CTkFrame(adv_filter_frame, fg_color="transparent")
        size_frame.pack(side="left", padx=10)

        ctk.CTkLabel(size_frame, text="📏 Size:").pack(side="left")
        self.pdf_size_combo = ctk.CTkComboBox(
            size_frame,
            values=["Any", "Small (<1MB)", "Medium (1-5MB)", "Large (>5MB)"],
            state="readonly",
            width=120)
        self.pdf_size_combo.set("Any")
        self.pdf_size_combo.pack(side="left", padx=5)
        # Search button
        ctk.CTkButton(
            adv_filter_frame,
            text="Search",
            command=self._perform_pdf_search,
            fg_color=self.primary_color,
            width=100
        ).pack(side="left", padx=10)
        # ===== MAIN CONTENT AREA =====
        main_frame = ctk.CTkFrame(search_window, fg_color="transparent")
        main_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        main_frame.grid_columnconfigure(0, weight=3)
        main_frame.grid_columnconfigure(1, weight=2)
        main_frame.grid_rowconfigure(0, weight=1)
        # Results table
        results_card = ctk.CTkFrame(main_frame, border_width=1, border_color="#ddd", corner_radius=8)
        results_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)
        results_card.grid_columnconfigure(0, weight=1)
        results_card.grid_rowconfigure(0, weight=1)

        # Treeview with sortable columns
        self.pdf_results_tree = ttk.Treeview(
            results_card,
            columns=("name", "type", "date", "size", "path", "customer"),
            show="headings",
            selectmode="extended",  # Allow multiple selection
            height=2)
        # Configure style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("PDF.Treeview",
                        background="#ffffff",
                        foreground="#333333",
                        rowheight=32,
                        fieldbackground="#ffffff",
                        font=('Segoe UI', 11),
                        bordercolor="#e0e0e0")
        style.configure("PDF.Treeview.Heading",
                        background=self.primary_color,
                        foreground="white",
                        font=('Segoe UI', 11, 'bold'),
                        relief="flat")
        style.map("PDF.Treeview",
                  background=[('selected', '#3a6cb5')],
                  foreground=[('selected', 'white')])
        # Configure columns
        columns = [
            {"id": "name", "text": "Filename", "width": 250, "anchor": "w"},
            {"id": "type", "text": "Type", "width": 100, "anchor": "center"},
            {"id": "date", "text": "Date", "width": 120, "anchor": "center"},
            {"id": "size", "text": "Size", "width": 100, "anchor": "center"},
            {"id": "customer", "text": "Customer", "width": 200, "anchor": "w"},
            {"id": "path", "text": "Path", "width": 0, "anchor": "w"}  # Hidden column
        ]

        for col in columns:
            self.pdf_results_tree.heading(col["id"], text=col["text"],
                                          command=lambda c=col["id"]: self._sort_pdf_results(c))
            self.pdf_results_tree.column(col["id"], width=col["width"], anchor=col["anchor"],
                                         stretch=col["id"] in ["name", "customer"])

        # Add scrollbars
        y_scroll = ctk.CTkScrollbar(results_card, orientation="vertical", command=self.pdf_results_tree.yview)
        x_scroll = ctk.CTkScrollbar(results_card, orientation="horizontal", command=self.pdf_results_tree.xview)
        self.pdf_results_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.pdf_results_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        # Preview panel
        preview_card = ctk.CTkFrame(main_frame, border_width=1, border_color="#ddd", corner_radius=8)
        preview_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=5)
        preview_card.grid_columnconfigure(0, weight=1)
        preview_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            preview_card,
            text="📄 Document Preview",
            font=self.font_normal_bold,
            text_color=self.primary_color
        ).grid(row=0, column=0, sticky="w", padx=10, pady=10)

        self.pdf_preview_frame = ctk.CTkFrame(preview_card, fg_color="white")
        self.pdf_preview_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.pdf_preview_label = ctk.CTkLabel(
            self.pdf_preview_frame,
            text="Select a file to preview",
            text_color="#666666",
            font=self.font_normal
        )
        self.pdf_preview_label.pack(expand=True)

        # Bind selection change event
        self.pdf_results_tree.bind("<<TreeviewSelect>>", self._update_pdf_preview)

        # ===== ACTION BUTTONS =====
        btn_frame = ctk.CTkFrame(search_window, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

        # Left side buttons
        left_btn_frame = ctk.CTkFrame(btn_frame, fg_color="transparent")
        left_btn_frame.pack(side="left", fill="x", expand=True)

        btn_style = {"width": 120, "height": 36, "font": self.font_normal, "corner_radius": 8}

        ctk.CTkButton(
            left_btn_frame,
            text="📂 Open",
            command=self._open_selected_pdf,
            fg_color=self.secondary_color,
            hover_color="#449d44",
            **btn_style
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            left_btn_frame,
            text="📱 Share",
            command=self.open_pop,
            fg_color="#17a2b8",
            hover_color="#138496",
            **btn_style
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            left_btn_frame,
            text="🗑️ Delete",
            command=self._delete_selected_pdf,
            fg_color=self.danger_color,
            hover_color="#c9302c",
            **btn_style
        ).pack(side="left", padx=5)

        # Right side buttons
        right_btn_frame = ctk.CTkFrame(btn_frame, fg_color="transparent")
        right_btn_frame.pack(side="right")

        ctk.CTkButton(
            right_btn_frame,
            text="🖨️ Print",
            command=self._print_selected_pdf,
            fg_color="#6c757d",
            hover_color="#5a6268",
            **btn_style
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            right_btn_frame,
            text="Close",
            command=search_window.destroy,
            fg_color="#6c757d",
            hover_color="#5a6268",
            **btn_style
        ).pack(side="left", padx=5)

        # Add window protocol handler
        self.pdf_search_window = search_window
        self.pdf_preview_frame = preview_card

        # Set close handler
        search_window.protocol("WM_DELETE_WINDOW", self._cleanup_pdf_search)

        # ... inside open_pdf_search, before performing the initial search ...
        # Initialize preview state variables
        # Initialize preview state variables
        self._preview_doc = None
        self._preview_page_num = 0
        self._preview_zoom_level = 0.3  # User-controlled zoom factor
        self._preview_base_zoom = 0.3  # The calculated "fit-to-screen" zoom
        self._image_label = None  # Reference to the image label for pan/zoom
        self._pan_start_x = 0  # Pan starting coordinates
        self._pan_start_y = 0
        self._pan_start_widget_x = 0  # The image's position when panning starts
        self._pan_start_widget_y = 0

        # Perform initial search
        self._perform_pdf_search()

    def _on_mouse_wheel(self, event):
        """Handle zooming in and out with the mouse wheel."""
        if not self._preview_doc:
            return

        # Zoom in on scroll up, out on scroll down
        zoom_factor = 1.1 if event.delta > 0 else 1 / 1.1
        self._preview_zoom_level *= zoom_factor

        # Clamp the zoom level to reasonable limits
        self._preview_zoom_level = max(0.2, min(self._preview_zoom_level, 10.0))

        # Re-render the page at the new zoom level
        self._render_and_display_page(self._preview_page_num)

    def _on_pan_start(self, event):
        """Record starting position for panning the image."""
        if not self._image_label:
            return

        # Record the starting mouse and widget positions
        self._pan_start_x = event.x_root
        self._pan_start_y = event.y_root
        place_info = self._image_label.place_info()
        self._pan_start_widget_x = int(place_info.get('x', 0))
        self._pan_start_widget_y = int(place_info.get('y', 0))
        self._image_label.configure(cursor="fleur")

    def _on_pan_move(self, event):
        """Move the image as the mouse is dragged."""
        if not self._image_label:
            return

        # Calculate the distance moved
        delta_x = event.x_root - self._pan_start_x
        delta_y = event.y_root - self._pan_start_y

        # Calculate the new position and move the widget
        new_x = self._pan_start_widget_x + delta_x
        new_y = self._pan_start_widget_y + delta_y
        self._image_label.place(x=new_x, y=new_y)

    def _on_pan_end(self, event):
        """Reset the cursor when panning is complete."""
        if not self._image_label:
            return
        self._image_label.configure(cursor="")

    def _cleanup_pdf_search(self):
        """Clean up resources when the search window closes."""
        # Close the currently open PDF document to release the file handle
        if hasattr(self, '_preview_doc') and self._preview_doc:
            self._preview_doc.close()
            self._preview_doc = None

        if hasattr(self, 'pdf_search_window'):
            try:
                self.pdf_search_window.destroy()
            except:
                pass
        # Clear object references
        if hasattr(self, 'pdf_preview_frame'):
            del self.pdf_preview_frame
        if hasattr(self, 'pdf_search_window'):
            del self.pdf_search_window

    def _update_pdf_preview(self, event=None):
        """Loads the selected PDF, handles errors, and displays the first page."""
        try:
            # Clear any existing preview document
            if hasattr(self, '_preview_doc') and self._preview_doc:
                self._preview_doc.close()
            self._preview_doc = None
            self._image_label = None  # Clear image reference

            selected = self.pdf_results_tree.selection()
            if not selected:
                self._clear_pdf_preview()
                return

            file_path = self.pdf_results_tree.item(selected[0], "values")[4]
            self._clear_pdf_preview("Loading preview...")
            self.pdf_preview_frame.update_idletasks()

            if not os.path.exists(file_path):
                self._clear_pdf_preview("File not found.", self.danger_color)
                return

            try:
                self._preview_doc = fitz.open(file_path)
                if len(self._preview_doc) == 0:
                    self._clear_pdf_preview("PDF is empty (no pages).", self.danger_color)
                    self._preview_doc.close()
                    self._preview_doc = None
                    return

                # Render the first page with the view reset
                self._render_and_display_page(0, reset_view=True)

            except fitz.FileDataError:
                self._clear_pdf_preview("Selected file is not a valid PDF.", self.danger_color)
                if hasattr(self, '_preview_doc') and self._preview_doc:
                    self._preview_doc.close()
                    self._preview_doc = None

        except Exception as e:
            error_msg = f"Could not load preview:\n{str(e)}"
            self._clear_pdf_preview(error_msg, self.danger_color)
            if hasattr(self, '_preview_doc') and self._preview_doc:
                self._preview_doc.close()
                self._preview_doc = None
            print(f"Error in _update_pdf_preview: {e}")

    def _render_and_display_page(self, page_num, reset_view=False):
        """Renders a specific PDF page with support for zoom and pan."""
        try:
            if not self._preview_doc:
                return

            # Reset zoom level and position if a new file is loaded or reset is clicked
            if reset_view:
                self._preview_zoom_level = 0.65

            self._preview_page_num = page_num
            page = self._preview_doc.load_page(page_num)

            for widget in self.pdf_preview_frame.winfo_children():
                widget.destroy()

            # --- Base Zoom Calculation (Fit to Screen) ---
            canvas_frame_width = self.pdf_preview_frame.winfo_width() - 30
            canvas_frame_height = self.pdf_preview_frame.winfo_height() - 90

            if page.rect.width > 0 and page.rect.height > 0:
                zoom_x = canvas_frame_width / page.rect.width
                zoom_y = canvas_frame_height / page.rect.height
                self._preview_base_zoom = min(zoom_x, zoom_y)
            else:
                self._preview_base_zoom = 0.5

            # --- Rendering with Combined Zoom ---
            final_zoom = self._preview_base_zoom * self._preview_zoom_level
            matrix = fitz.Matrix(final_zoom, final_zoom).prescale(2, 2)
            pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            from PIL import ImageFilter
            img = img.filter(ImageFilter.SHARPEN)
            pdf_img = ctk.CTkImage(img, size=(img.width, img.height))

            # --- UI Layout ---
            container = ctk.CTkFrame(self.pdf_preview_frame, fg_color="white")
            container.pack(expand=True, fill="both", padx=5, pady=5)
            container.grid_columnconfigure(0, weight=1)
            container.grid_rowconfigure(1, weight=1)

            ctk.CTkLabel(
                container, text=os.path.basename(self._preview_doc.name),
                font=self.font_normal_bold, text_color=self.primary_color, anchor="w"
            ).grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 2))

            # Canvas for clipping and panning
            canvas_frame = ctk.CTkFrame(container, fg_color="gray70", corner_radius=0)
            canvas_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

            self._image_label = ctk.CTkLabel(canvas_frame, image=pdf_img, text="")
            self._image_label.place(x=0, y=0)
            self._image_label.image = pdf_img

            # --- Bind Events ---
            self._image_label.bind("<ButtonPress-1>", self._on_pan_start)
            self._image_label.bind("<B1-Motion>", self._on_pan_move)
            self._image_label.bind("<ButtonRelease-1>", self._on_pan_end)
            self._image_label.bind("<MouseWheel>", self._on_mouse_wheel)
            canvas_frame.bind("<MouseWheel>", self._on_mouse_wheel)

            # --- Footer with Navigation and Zoom Controls ---
            footer = ctk.CTkFrame(container, fg_color="transparent")
            footer.grid(row=2, column=0, sticky="ew", padx=10, pady=(2, 5))
            footer.grid_columnconfigure(1, weight=1)

            ctk.CTkButton(
                footer, text="◀ Prev", width=70, state="disabled" if page_num == 0 else "normal",
                command=lambda: self._render_and_display_page(self._preview_page_num - 1, reset_view=True)
            ).grid(row=0, column=0, sticky="w")

            ctk.CTkLabel(
                footer, text=f"Page {page_num + 1} of {len(self._preview_doc)}", font=self.font_small
            ).grid(row=0, column=1, sticky="ew")

            ctk.CTkButton(
                footer, text="Next ▶", width=70,
                state="disabled" if page_num == len(self._preview_doc) - 1 else "normal",
                command=lambda: self._render_and_display_page(self._preview_page_num + 1, reset_view=True)
            ).grid(row=0, column=2, sticky="e", padx=(0, 35))

            # Zoom Controls
            ctk.CTkButton(
                footer, text="Reset", width=60,
                command=lambda: self._render_and_display_page(self._preview_page_num, reset_view=True)
            ).grid(row=0, column=4, padx=5)

            ctk.CTkButton(
                footer, text="-", width=30,
                command=lambda: self._on_mouse_wheel(type('Event', (), {'delta': -120})())
            ).grid(row=0, column=3, sticky="e")

            ctk.CTkButton(
                footer, text="+", width=30,
                command=lambda: self._on_mouse_wheel(type('Event', (), {'delta': 120})())
            ).grid(row=0, column=5, sticky="e")


        except Exception as e:
            self._clear_pdf_preview(f"Error rendering page {page_num}:\n{e}", self.danger_color)
            print(f"Error rendering page: {e}")

    def _clear_pdf_preview(self, message="Select a file to preview", color="#666666"):
        """Clears the preview panel and displays a message."""
        if not hasattr(self, 'pdf_preview_frame') or not self.pdf_preview_frame.winfo_exists():
            return

        for widget in self.pdf_preview_frame.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.pdf_preview_frame,
            text=message,
            text_color=color,
            font=self.font_normal,
            wraplength=self.pdf_preview_frame.winfo_width() - 20,
            justify="center"
        ).pack(expand=True, padx=10, pady=10)

    def _perform_pdf_search(self):
        """Perform search with all filters"""
        search_term = self.pdf_search_entry.get().strip().lower()

        # Date range filter
        date_range = None
        from_date = self.pdf_from_date.get().strip()
        to_date = self.pdf_to_date.get().strip()

        if from_date or to_date:
            try:
                start_date = (dt.datetime.strptime(from_date, "%Y-%m-%d").date()
                              if from_date else dt.date(1900, 1, 1))
                end_date = (dt.datetime.strptime(to_date, "%Y-%m-%d").date()
                            if to_date else dt.date.today())
                date_range = (start_date, end_date)
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
                return
        # File type filter
        file_type = self.pdf_type_combo.get()

        # Size filter
        size_filter = self.pdf_size_combo.get()
        size_ranges = {
            "Small (<1MB)": (0, 1024 * 1024),
            "Medium (1-5MB)": (1024 * 1024, 5 * 1024 * 1024),
            "Large (>5MB)": (5 * 1024 * 1024, float('inf'))
        }
        min_size, max_size = size_ranges.get(size_filter, (0, float('inf')))

        # Clear previous results
        for item in self.pdf_results_tree.get_children():
            self.pdf_results_tree.delete(item)

        # Search in both directories
        search_dirs = []
        if file_type in ["All", "Bills"]:
            search_dirs.append("bills")
        if file_type in ["All", "Receipts"]:
            search_dirs.append("receipts")

        results = []
        for dir_name in search_dirs:
            if not os.path.exists(dir_name):
                continue

            for filename in os.listdir(dir_name):
                if not filename.lower().endswith(".pdf"):
                    continue

                file_path = os.path.join(dir_name, filename)
                file_time = os.path.getmtime(file_path)
                file_date = dt.datetime.fromtimestamp(file_time).date()
                file_size = os.path.getsize(file_path)

                # Apply filters
                if date_range and not (date_range[0] <= file_date <= date_range[1]):
                    continue

                if not (min_size <= file_size <= max_size):
                    continue

                # Extract customer name from filename if possible
                customer_name = "Unknown"
                if "_" in filename:
                    try:
                        customer_part = filename.split("_")[1]
                        customer_name = " ".join(
                            [word.capitalize() for word in customer_part.replace(".pdf", "").split()]
                        )
                    except:
                        pass

                # Apply search term filter
                if search_term:
                    if (search_term not in filename.lower() and
                            search_term not in customer_name.lower()):
                        continue

                results.append({
                    "path": file_path,
                    "name": filename,
                    "type": "Bill" if dir_name == "bills" else "Receipt",
                    "date": file_date,
                    "size": file_size,
                    "customer": customer_name
                })

        # Sort by date (newest first)
        results.sort(key=lambda x: x["date"], reverse=True)

        # Add to treeview
        for pdf in results:
            size_str = self._format_file_size(pdf["size"])
            self.pdf_results_tree.insert("", "end", values=(
                pdf["name"],
                pdf["type"],
                pdf["date"].strftime("%Y-%m-%d"),
                size_str,
                pdf["path"],
                pdf["customer"]
            ))

    def _format_file_size(self, size_bytes):
        """Convert file size to human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _sort_pdf_results(self, column):
        """Sort results by selected column"""
        items = [(self.pdf_results_tree.set(child, column), child)
                 for child in self.pdf_results_tree.get_children("")]
        items.sort()

        # Reverse if already sorted
        if self.pdf_results_tree.heading(column, "text").endswith("↑"):
            items.reverse()
            self.pdf_results_tree.heading(column, text=column + " ↓")
        else:
            self.pdf_results_tree.heading(column, text=column + " ↑")

        # Rearrange items in sorted order
        for index, (val, child) in enumerate(items):
            self.pdf_results_tree.move(child, "", index)

    def _open_selected_pdf(self):
        """Open selected PDF file(s)"""
        selected = self.pdf_results_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select at least one file")
            return

        for item in selected:
            file_path = self.pdf_results_tree.item(item, "values")[4]
            try:
                os.startfile(file_path)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open {file_path}:\n{str(e)}")


    def _delete_selected_pdf(self):
        """Delete selected PDF file(s) with confirmation"""
        selected = self.pdf_results_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select at least one file")
            return

        file_list = "\n".join(self.pdf_results_tree.item(item, "values")[0] for item in selected)

        if messagebox.askyesno(
                "Confirm Deletion",
                f"Delete {len(selected)} selected file(s)?\n\n{file_list}",
                icon="warning"
        ):
            failed_deletions = []

            for item in selected:
                file_path = self.pdf_results_tree.item(item, "values")[4]
                try:
                    os.remove(file_path)
                    self.pdf_results_tree.delete(item)
                except Exception as e:
                    failed_deletions.append(f"{os.path.basename(file_path)}: {str(e)}")

            if failed_deletions:
                messagebox.showerror(
                    "Partial Success",
                    f"Could not delete some files:\n\n{'\n'.join(failed_deletions)}"
                )
            else:
                messagebox.showinfo("Success", "Selected files deleted successfully")

            # Refresh preview
            self._update_pdf_preview()

    def _print_selected_pdf(self):
        """Print selected PDF file(s)"""
        selected = self.pdf_results_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select at least one file")
            return

        for item in selected:
            file_path = self.pdf_results_tree.item(item, "values")[4]
            try:
                # This requires the system to have a PDF reader with print command line support
                os.startfile(file_path, "print")
            except Exception as e:
                messagebox.showerror("Error", f"Could not print {file_path}:\n{str(e)}")

    def convert_pdf_to_high_quality_image(self, pdf_path, output_image_path="full_bill_image.png", dpi=350):
        """Convert PDF to high quality image for WhatsApp sharing with improved quality"""
        try:
            doc = fitz.open(pdf_path)
            images = []

            for page_num, page in enumerate(doc):
                # Increase DPI and use anti-aliasing for better quality
                matrix = fitz.Matrix(dpi / 72, dpi / 72).prescale(2, 2)  # 2x supersampling for anti-aliasing
                pix = page.get_pixmap(matrix=matrix,
                                      colorspace=fitz.csRGB,
                                      alpha=False)

                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # Apply slight sharpening to enhance text clarity
                from PIL import ImageFilter
                img = img.filter(ImageFilter.SHARPEN)

                images.append(img)

            # Calculate total height and max width
            total_height = sum(img.height for img in images)
            max_width = max(img.width for img in images)

            # Create final image with white background
            final_image = Image.new("RGB", (max_width, total_height), color=(255, 255, 255))

            # Paste images with proper alignment
            y_offset = 0
            for img in images:
                # Center each page horizontally if they have different widths
                x_offset = (max_width - img.width) // 2
                final_image.paste(img, (x_offset, y_offset))
                y_offset += img.height

            # Save with maximum quality
            final_image.save(output_image_path,
                             format="PNG",
                             optimize=True,
                             quality=95,  # Maximum quality for PNG
                             dpi=(dpi, dpi))  # Set DPI metadata

            return output_image_path

        except Exception as e:
            print(f"Error generating high-quality image: {e}")
            return None

    def calculate_totals(self):
        """Calculate rental totals including payment received"""
        if not self.transactions:
            previous_balance = self.previous_balance.get()
            payment_received = self.payment_received.get()
            grand_total = previous_balance - payment_received
            return 0, previous_balance, payment_received, grand_total

        sorted_trans = sorted(self.transactions, key=lambda x: x[0])

        item_rents = {}
        current_items = {item[0]: 0 for item in self.items}

        for i in range(len(sorted_trans)):
            date, item_name, qty, rent = sorted_trans[i]
            if item_name not in current_items: continue
            current_items[item_name] += qty

            if i < len(sorted_trans) - 1:
                next_date = sorted_trans[i + 1][0]
                days = (next_date - date).days

                for item, count in current_items.items():
                    if count > 0:
                        item_rent_price = next((i[1] for i in self.items if i[0] == item), 0)
                        rent_amount = days * count * item_rent_price
                        item_rents[item] = item_rents.get(item, 0) + rent_amount

        total_rent = sum(item_rents.values())
        previous_balance = self.previous_balance.get()
        payment_received = self.payment_received.get()
        grand_total = total_rent + previous_balance - payment_received

        return total_rent, previous_balance, payment_received, grand_total

    def generate_bill(self):
        """Generate a rental bill PDF"""
        if not self.customer_name.get().strip():
            messagebox.showerror("Error", "Please enter customer name")
            return

        if not self.items:
            messagebox.showerror("Error", "Please add at least one rental item")
            return

        if not self.transactions:
            if not messagebox.askyesno("Confirm",
                                       "No transactions found. Generate a bill with only the previous balance?"):
                return

        total_rent, previous_balance, payment_received, grand_total = self.calculate_totals()

        filename = self.create_pdf_bill(total_rent, previous_balance, payment_received, grand_total, self.enable_qr)
        messagebox.showinfo("Success", "Bill generated successfully!")

        try:
            os.startfile(filename)
        except OSError:
            messagebox.showinfo("PDF Generated", f"Bill saved as:\n{filename}")

    def create_pdf_bill(self, total_rent, previous_balance, payment_received, grand_total, include_qr=True):
        pdf = FPDF()
        pdf.add_page()

        # Custom colors
        primary_color = (43, 87, 154)  # Dark blue
        secondary_color = (92, 184, 92)  # Green
        accent_color = (240, 173, 78)  # Orange
        light_gray = (240, 240, 240)
        dark_gray = (100, 100, 100)

        # Try to use Arial if available, otherwise use standard core fonts
        try:
            pdf.add_font("Arial", style="", fname="arial.ttf")
            pdf.add_font("Arial", style="B", fname="arialbd.ttf")
            use_arial = True
        except:
            use_arial = False

        def set_font(style='', size=12):
            if use_arial:
                pdf.set_font("Arial", style=style, size=size)
            else:
                pdf.set_font("helvetica", style='B' if 'B' in style else '', size=size)

        def format_date(date_obj):
            return date_obj.strftime("%d-%b-%Y")  # e.g., "29-Jun-2025"

        def format_currency(amount):
            return locale.currency(amount, grouping=True, symbol=False)

        # --- Header with Logo ---
        pdf.set_fill_color(*primary_color)
        pdf.rect(0, 0, pdf.w, 30, style='F')

        set_font('B', 20)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, self.company_name, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

        set_font('', 12)
        pdf.cell(0, 6, f"Mobile : {self.company_mobile} | Address : {self.company_address}",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

        pdf.ln(15)

        # --- Customer Details Card ---
        pdf.set_fill_color(*light_gray)
        pdf.rect(10, pdf.get_y(), 190, 35, style='F', round_corners=True, corner_radius=5)

        set_font('B', 14)
        pdf.set_text_color(*primary_color)
        pdf.cell(0, 8, "CUSTOMER DETAILS", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

        pdf.set_draw_color(200, 200, 200)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(5)

        set_font('', 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(40, 6, "    Name:", new_x=XPos.RIGHT, new_y=YPos.TOP)
        set_font('B', 12)
        pdf.cell(0, 6, self.customer_name.get(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        set_font('', 12)
        pdf.cell(40, 6, "    Mobile:", new_x=XPos.RIGHT, new_y=YPos.TOP)
        set_font('B', 12)
        pdf.cell(0, 6, self.customer_mobile.get(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        set_font('', 12)
        pdf.cell(40, 6, "    Address:", new_x=XPos.RIGHT, new_y=YPos.TOP)
        set_font('B', 12)
        pdf.multi_cell(0, 6, self.customer_address.get(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.ln(10)

        # --- Bill Info ---
        start_date = self.transactions[0][0]
        end_date = self.transactions[-1][0]
        bill_date = dt.date.today()
        serial_no = self.customer_id.get() if self.customer_id else None
        pdf.set_fill_color(*light_gray)
        pdf.rect(10, pdf.get_y(), 190, 35, style='F', round_corners=True, corner_radius=5)

        set_font('B', 12)
        pdf.set_text_color(*primary_color)
        pdf.ln(2)
        pdf.cell(0, 6, f"    Customer ID: {serial_no}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='l')
        pdf.ln(2)
        pdf.cell(0, 6, f"    Bill Date: {format_date(bill_date)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='l')
        pdf.ln(2)
        pdf.cell(0, 6, f"    Period: {format_date(start_date)} to {format_date(end_date)}",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='l')
        pdf.ln(2)
        pdf.cell(0, 6, f"    Previous Balance and Transport fees: {format_currency(previous_balance)}",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='l')

        pdf.ln(10)
        item_balances = {}

        # --- Transaction Tables ---
        def create_transaction_table(title, transactions):
            pdf.set_fill_color(*light_gray)
            pdf.rect(10, pdf.get_y(), 190, 15, style='F', round_corners=True, corner_radius=5)
            set_font('B', 12)
            pdf.set_text_color(*primary_color)
            pdf.cell(0, 8, f"{title.upper()}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

            # Table header
            pdf.set_fill_color(*primary_color)
            pdf.set_text_color(255, 255, 255)
            set_font('B', 10)

            col_widths = [10, 30, 50, 20, 30, 50]
            headers = ["#", "Date", "Item", "Qty", "In Hand", "Remarks"]

            for w, h in zip(col_widths, headers):
                pdf.cell(w, 8, h, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
            pdf.ln(8)

            # Table rows
            pdf.set_text_color(0, 0, 0)
            set_font('', 10)
            fill = False

            for idx, (date, item, qty, rent) in enumerate(transactions, start=1):
                if item not in item_balances:
                    item_balances[item] = 0

                item_balances[item] += qty  # qty could be positive (rent) or negative (return)

                if fill:
                    pdf.set_fill_color(*light_gray)
                else:
                    pdf.set_fill_color(255, 255, 255)

                pdf.cell(col_widths[0], 8, str(idx), border=1, align='C', fill=fill)
                pdf.cell(col_widths[1], 8, date.strftime("%d-%b-%Y"), border=1, align='C', fill=fill)
                pdf.cell(col_widths[2], 8, item, border=1, align='L', fill=fill)
                pdf.cell(col_widths[3], 8, str(abs(qty)), border=1, align='C', fill=fill)
                pdf.cell(col_widths[4], 8, str(item_balances[item]), border=1, align='C', fill=fill)
                pdf.cell(col_widths[5], 8, "Returned items" if qty <= 0 else "Rented items", border=1, align='C',
                         fill=fill)
                pdf.ln(8)

                fill = not fill

            pdf.ln(5)

        # Sort transactions by date
        sorted_transactions = sorted(self.transactions, key=lambda x: x[0])

        # Create rented and returned tables
        rented = [t for t in sorted_transactions if t[2] > 0]
        returned = [t for t in sorted_transactions if t[2] <= 0]

        create_transaction_table("ITEMS RENTED", rented)
        create_transaction_table("ITEMS RETURNED", returned)
        if pdf.get_y() > 240:
            pdf.add_page()

        # --- Rent Summary ---
        pdf.set_fill_color(*light_gray)
        pdf.rect(10, pdf.get_y(), 190, 15, style='F', round_corners=True, corner_radius=5)

        set_font('B', 12)
        pdf.set_text_color(*primary_color)
        pdf.cell(0, 8, "RENT SUMMARY", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

        # Calculate item days and rents
        item_rents = {}
        current_items = {item[0]: 0 for item in self.items}
        item_days = {item[0]: 0 for item in self.items}

        for i in range(len(sorted_transactions)):
            date, item_name, qty, rent = sorted_transactions[i]
            current_items[item_name] += qty

            if i < len(sorted_transactions) - 1:
                next_date = sorted_transactions[i + 1][0]
                days = (next_date - date).days

                for item, count in current_items.items():
                    if count > 0:
                        item_rent = next((i[1] for i in self.items if i[0] == item), 0)
                        rent_amount = days * count * item_rent
                        item_rents[item] = item_rents.get(item, [item_rent, 0, 0])
                        item_rents[item][1] += rent_amount
                        item_rents[item][2] += days
                        item_days[item] += days

        # Summary table
        col_widths = [80, 30, 30, 50]
        headers = ["Item", "Daily Rent", "Days", "Total Rent"]

        # Table header
        pdf.set_fill_color(*primary_color)
        pdf.set_text_color(255, 255, 255)
        set_font('B', 10)

        for w, h in zip(col_widths, headers):
            pdf.cell(w, 8, h, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=True)
        pdf.ln(8)

        # Table rows
        pdf.set_text_color(0, 0, 0)
        set_font('', 10)
        fill = False

        for item, (rent_price, total_rent_item, days) in item_rents.items():
            if fill:
                pdf.set_fill_color(*light_gray)
            else:
                pdf.set_fill_color(255, 255, 255)

            pdf.cell(col_widths[0], 8, item, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='L', fill=fill)
            pdf.cell(col_widths[1], 8, f"{rent_price:.2f}", border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='R',
                     fill=fill)
            pdf.cell(col_widths[2], 8, str(days), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C', fill=fill)
            pdf.cell(col_widths[3], 8, f"{total_rent_item:,.2f}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT,
                     align='R', fill=fill)
            fill = not fill

        pdf.ln(5)

        if pdf.get_y() > 220:
            pdf.add_page()

        # --- Totals Section ---
        pdf.set_fill_color(*light_gray)
        pdf.rect(10, pdf.get_y(), 190, 60, style='F', round_corners=True, corner_radius=5)

        set_font('B', 12)
        pdf.set_text_color(*primary_color)
        pdf.cell(0, 8, "PAYMENT SUMMARY", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

        pdf.set_draw_color(200, 200, 200)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(5)

        # Summary rows
        pdf.set_text_color(0, 0, 0)
        set_font('B', 11)
        pdf.cell(140, 8, "Current Rental Charges:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='R')
        set_font('', 11)
        pdf.cell(50, 8, f"{format_currency(total_rent)}    ", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')

        set_font('B', 11)
        pdf.cell(140, 8, "Previous Balance, Transport Fee and Additional charge : :", new_x=XPos.RIGHT, new_y=YPos.TOP,
                 align='R')
        set_font('', 11)
        pdf.cell(50, 8, f"{format_currency(previous_balance)}    ", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')

        set_font('B', 11)
        pdf.cell(140, 8, "Payment Received :", new_x=XPos.RIGHT, new_y=YPos.TOP, align='R')
        set_font('', 11)
        pdf.cell(50, 8, f"-{format_currency(payment_received)}    ", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')

        pdf.set_draw_color(*primary_color)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(3)

        set_font('B', 15)
        pdf.set_text_color(*primary_color)
        pdf.cell(140, 10, "TOTAL AMOUNT DUE:", new_x=XPos.RIGHT, new_y=YPos.TOP, align='R')
        pdf.cell(50, 10, f"{format_currency(grand_total)}   ", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')
        pdf.ln(1)
        pdf.set_draw_color(*primary_color)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(3)

        pdf.ln(15)

        # Only add QR code if enabled in settings
        if include_qr:
            if pdf.get_y() > 220:
                pdf.add_page()
            pdf.line(15, pdf.get_y(), 195, pdf.get_y())
            pdf.ln(10)
            # --- Payment QR Code ---
            pdf.set_fill_color(*light_gray)
            pdf.rect(10, pdf.get_y(), 190, 120, style='F', round_corners=True, corner_radius=5)

            set_font('B', 14)
            pdf.set_text_color(*primary_color)
            pdf.cell(0, 10, "PAYMENT OPTIONS", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

            upi_id = self.company_upi
            upi_amount = grand_total
            upi_payload = f"upi://pay?pa={upi_id}&pn={self.company_name}&am={upi_amount:.2f}&cu=INR"

            qr = qrcode.make(upi_payload)
            qr_path = "upi_qr.png"
            qr.save(qr_path)

            # Center the QR code
            qr_size = 90
            qr_x = (pdf.w - qr_size) / 2
            pdf.image(qr_path, x=qr_x, y=pdf.get_y() + 10, w=qr_size, h=qr_size)

            pdf.ln(qr_size + 20)

            set_font('B', 12)
            pdf.set_text_color(*primary_color)
            pdf.cell(0, 8, "Scan to Pay", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

            set_font('', 10)
            pdf.set_text_color(*dark_gray)
            pdf.cell(0, 6, f"Amount: {format_currency(upi_amount)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

            # Fix the hyperlink by using a proper URL format
            set_font('U', 12)
            pdf.set_text_color(0, 102, 204)
            pdf.cell(0, 8, "Click here to Pay via UPI App",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C', link=upi_payload)

            set_font('I', 10)
            pdf.set_text_color(*dark_gray)
            pdf.cell(0, 6, "Scan the QR code above to make payment securely",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

            os.remove(qr_path)
        # --- Footer ---
        pdf.ln(15)
        pdf.set_draw_color(*primary_color)
        pdf.set_line_width(0.5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())

        set_font('I', 10)
        pdf.set_text_color(*dark_gray)
        pdf.cell(0, 8, "Thank you for your business!", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
        pdf.cell(0, 6, "For any queries, please contact: " + self.company_mobile,
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')

        # Save PDF
        filename = rf"bills\Rental_Bill_{self.customer_name.get()}_{dt.date.today()}.pdf"
        pdf.output(filename)
        return filename

if __name__ == "__main__":
    app = RentalBillApp()
    app.mainloop()