import streamlit as st
import pandas as pd
import json
import os
import datetime as dt
import locale
from fpdf import FPDF
# from fpdf.enums import XPos, YPos
import qrcode
import base64
from PIL import Image
import io
import hashlib
import uuid
import time
import logging
from typing import Dict, List, Optional, Any
import plotly.express as px
import plotly.graph_objects as go

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set locale for currency formatting
try:
    locale.setlocale(locale.LC_ALL, 'en_IN')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')


# --- Directory and Settings Management ---

def initialize_directories():
    """Initialize required directories with robust error handling."""
    directories = ["data", "settings", "sessions", "logs"]
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Directory '{directory}' ensured.")
        except PermissionError:
            st.error(f"Permission denied: Cannot create directory '{directory}'. Please check your system permissions.")
            logger.critical(f"PermissionError creating directory: {directory}")
            return False
        except Exception as e:
            st.error(f"Error creating directory '{directory}': {str(e)}")
            logger.critical(f"Error creating directory {directory}: {e}")
            return False
    return True


def hash_password(password: str) -> str:
    """Hashes a password using SHA256 for secure storage."""
    return hashlib.sha256(password.encode()).hexdigest()


@st.cache_resource
def load_company_settings() -> Dict[str, Any]:
    """Load company settings with enhanced error handling and default password hashing."""
    default_settings = {
        "name": "Jammu Shuttering Store",
        "mobile": "9876543210",
        "address": "Jammu, Jammu and Kashmir",
        "email": "info@jammushuttering.com",
        "website": "www.jammushuttering.com",
        "upi_id": "jammushuttering@okhdfcbank",
        "admin_password_hash": hash_password("admin123"),
        "currency_symbol": "₹",
        "date_format": "%d-%b-%Y",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/PlaceholderLC.png/768px-PlaceholderLC.png",
        "business_hours": "9:00 AM - 6:00 PM",
        "established_year": "2020",
        "tagline": "Quality Shuttering Solutions for Your Construction Needs"
    }
    settings_file = "settings/config.json"

    try:
        if os.path.exists(settings_file):
            with open(settings_file, "r", encoding='utf-8') as f:
                settings_from_file = json.load(f)
                company = settings_from_file.get("company", {})

                if "admin_password" in company and "admin_password_hash" not in company:
                    company["admin_password_hash"] = hash_password(company["admin_password"])
                    del company["admin_password"]
                    logger.warning("Converted 'admin_password' to 'admin_password_hash'. Please resave settings.")

                for key, value in default_settings.items():
                    if key not in company:
                        company[key] = value
                logger.info("Company settings loaded successfully.")
                return company
        else:
            config = {"company": default_settings}
            with open(settings_file, "w", encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            logger.info("Default company settings created.")
            return default_settings
    except (json.JSONDecodeError, PermissionError) as e:
        logger.error(f"Error loading company settings from {settings_file}: {str(e)}")
        st.error(f"Error loading settings: {str(e)}. Using default settings.")
        return default_settings
    except Exception as e:
        logger.error(f"Unexpected error loading company settings: {str(e)}")
        st.error(f"Unexpected error loading settings: {str(e)}. Using default settings.")
        return default_settings


def save_company_settings(settings: Dict[str, Any]) -> bool:
    """Save company settings with error handling. Ensures password hash is used."""
    try:
        if "admin_password" in settings:
            settings["admin_password_hash"] = hash_password(settings["admin_password"])
            del settings["admin_password"]

        config = {"company": settings}
        with open("settings/config.json", "w", encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logger.info("Company settings saved successfully.")
        load_company_settings.clear()
        return True
    except (PermissionError, json.JSONEncodeError) as e:
        logger.error(f"Error saving company settings: {str(e)}")
        st.error(f"Error saving settings: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving company settings: {str(e)}")
        st.error(f"An unexpected error occurred while saving settings: {str(e)}")
        return False


# --- Session Management ---

SESSION_EXPIRY_SECONDS = 86400  # 24 hours


def create_session(user_id: str, user_type: str = "customer", user_data: Optional[Dict] = None) -> Optional[str]:
    """Create a new session with robust error handling."""
    try:
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "user_type": user_type,
            "user_data": user_data or {},
            "created_at": time.time(),
            "last_accessed": time.time()
        }
        session_file = f"sessions/{session_id}.json"
        with open(session_file, "w", encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Session created for user {user_id} ({user_type}) with ID {session_id[:8]}...")
        return session_id
    except Exception as e:
        logger.error(f"Error creating session for user {user_id}: {str(e)}")
        return None


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session data with validation and last accessed update."""
    if not session_id or not isinstance(session_id, str):
        return None

    session_file = f"sessions/{session_id}.json"
    if not os.path.exists(session_file):
        return None

    try:
        with open(session_file, "r", encoding='utf-8') as f:
            session_data = json.load(f)

        current_time = time.time()
        if current_time - session_data.get("last_accessed", 0) > SESSION_EXPIRY_SECONDS:
            delete_session(session_id)
            logger.info(f"Expired session {session_id[:8]}... deleted.")
            return None

        if current_time - session_data.get("last_accessed", 0) > 300:
            session_data["last_accessed"] = current_time
            with open(session_file, "w", encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Session {session_id[:8]}... last accessed time updated.")

        return session_data
    except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
        logger.error(f"Error getting session {session_id[:8]}...: {str(e)}")
        delete_session(session_id)
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting session {session_id[:8]}...: {str(e)}")
        return None


def delete_session(session_id: str) -> bool:
    """Delete session with error handling."""
    try:
        session_file = f"sessions/{session_id}.json"
        if os.path.exists(session_file):
            os.remove(session_file)
            logger.info(f"Session {session_id[:8]}... deleted.")
            return True
        return False
    except (FileNotFoundError, PermissionError) as e:
        logger.error(f"Error deleting session {session_id[:8]}...: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting session: {str(e)}")
        return False


def cleanup_expired_sessions() -> int:
    """Clean up expired and corrupted sessions."""
    sessions_dir = "sessions"
    if not os.path.exists(sessions_dir):
        logger.info(f"Session directory '{sessions_dir}' not found. No cleanup needed.")
        return 0

    current_time = time.time()
    deleted_count = 0

    try:
        session_files = [f for f in os.listdir(sessions_dir) if f.endswith(".json")]
        for filename in session_files:
            file_path = os.path.join(sessions_dir, filename)
            try:
                with open(file_path, "r", encoding='utf-8') as f:
                    session_data = json.load(f)
                if current_time - session_data.get("last_accessed", 0) > SESSION_EXPIRY_SECONDS:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"Cleaned up expired session: {filename[:8]}...")
            except (json.JSONDecodeError, PermissionError) as e:
                logger.warning(f"Corrupted or unreadable session file '{filename}': {str(e)}. Deleting.")
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as del_e:
                    logger.error(f"Failed to delete corrupted session file '{filename}': {str(del_e)}")
            except Exception as e:
                logger.error(f"Error processing session file '{filename}' during cleanup: {str(e)}")
                continue

        if deleted_count > 0:
            logger.info(f"Finished session cleanup. {deleted_count} sessions deleted.")
        return deleted_count
    except Exception as e:
        logger.error(f"Major error during session cleanup: {str(e)}")
        return 0


# --- Helper Functions ---

def format_date(date_input: Any, format_str: str = "%d-%b-%Y") -> str:
    """Format date string or datetime object with error handling."""
    global company
    format_str = company.get('date_format', "%d-%b-%Y")

    if not date_input:
        return "N/A"

    if isinstance(date_input, (dt.date, dt.datetime)):
        return date_input.strftime(format_str)
    elif isinstance(date_input, str):
        try:
            date_obj = dt.datetime.strptime(date_input, "%Y-%m-%d").date()
            return date_obj.strftime(format_str)
        except ValueError:
            try:
                for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d-%b-%Y"]:
                    try:
                        date_obj = dt.datetime.strptime(date_input, fmt).date()
                        return date_obj.strftime(format_str)
                    except ValueError:
                        pass
                logger.warning(f"Could not parse date string: {date_input}. Returning original.")
                return str(date_input)
            except Exception as e:
                logger.warning(f"Error formatting date '{date_input}': {str(e)}. Returning original.")
                return str(date_input)
    else:
        logger.warning(f"Unsupported date format type: {type(date_input)}. Returning original.")
        return str(date_input)


def format_currency(amount: Optional[float], symbol: str = "₹") -> str:
    """Format currency with error handling and proper locale."""
    global company
    symbol = company.get('currency_symbol', '₹')

    try:
        if amount is None:
            amount = 0.0
        amount_float = safe_float(amount)
        formatted_amount = locale.format_string("%.2f", amount_float, grouping=True)
        return f"{symbol}{formatted_amount}"
    except (ValueError, TypeError) as e:
        logger.error(f"Error formatting currency amount '{amount}': {str(e)}")
        return f"{symbol}0.00"
    except Exception as e:
        logger.error(f"Unexpected error in format_currency: {str(e)}")
        return f"{symbol}0.00"


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float, handling None and non-numeric types."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        logger.debug(f"Could not convert '{value}' to float. Returning default {default}.")
        return default


def generate_qr_code(upi_id: str, amount: Optional[float] = None, company_name: str = "") -> io.BytesIO:
    """Generate UPI QR code with error handling."""
    img_bytes = io.BytesIO()
    try:
        if not upi_id:
            logger.warning("UPI ID is empty, cannot generate QR code.")
            return img_bytes

        safe_company_name = company_name.replace(' ', '%20').replace('&', '%26')
        upi_url = f"upi://pay?pa={upi_id}&pn={safe_company_name}"

        if amount is not None and safe_float(amount) > 0:
            upi_url += f"&am={safe_float(amount):.2f}"
        upi_url += "&cu=INR"

        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(upi_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        logger.info(f"QR code generated for UPI ID: {upi_id} with amount: {amount}")
        return img_bytes
    except Exception as e:
        logger.error(f"Error generating QR code for UPI ID '{upi_id}': {str(e)}")
        return img_bytes


# --- Customer Data Management ---

def authenticate_customer(identifier: str) -> Optional[Dict[str, Any]]:
    """Authenticate customer by mobile number or customer ID."""
    if not identifier or not identifier.strip():
        return None

    identifier = identifier.strip()
    customer_data_dir = "data"

    try:
        if not os.path.exists(customer_data_dir):
            logger.warning(f"Customer data directory '{customer_data_dir}' does not exist.")
            return None

        customer_files = [f for f in os.listdir(customer_data_dir) if f.endswith(".json")]

        for filename in customer_files:
            file_path = os.path.join(customer_data_dir, filename)
            try:
                with open(file_path, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    if (str(data.get("mobile", "")).strip() == identifier or
                            str(data.get("customer_id", "")).strip() == identifier):
                        logger.info(f"Customer '{identifier}' authenticated.")
                        return data
            except (json.JSONDecodeError, PermissionError) as e:
                logger.warning(f"Could not read/parse customer file {filename}: {str(e)}. Skipping.")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error reading customer file {filename}: {str(e)}. Skipping.")
                continue
        logger.info(f"Customer '{identifier}' not found during authentication.")
        return None
    except Exception as e:
        logger.error(f"Error during customer authentication process: {str(e)}")
        return None


@st.cache_data(ttl=300)
def get_all_customers() -> List[Dict[str, Any]]:
    """Get all customer data for admin panel with robust error handling."""
    customers = []
    customer_data_dir = "data"

    try:
        if not os.path.exists(customer_data_dir):
            logger.warning(f"Customer data directory '{customer_data_dir}' does not exist. Returning empty list.")
            return customers

        customer_files = [f for f in os.listdir(customer_data_dir) if f.endswith(".json")]

        for filename in customer_files:
            file_path = os.path.join(customer_data_dir, filename)
            try:
                with open(file_path, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    if all(key in data and data[key] is not None for key in ["customer_id", "name", "mobile"]):
                        customers.append(data)
                    else:
                        logger.warning(f"Skipping customer file {filename} due to missing required fields.")
            except (json.JSONDecodeError, PermissionError) as e:
                logger.warning(f"Could not read/parse customer file {filename}: {str(e)}. Skipping.")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error reading customer file {filename}: {str(e)}. Skipping.")
                continue
        logger.info(f"Loaded {len(customers)} customer records.")
        return customers
    except Exception as e:
        logger.error(f"Error getting all customers: {str(e)}")
        return []


def save_customer_data(customer_data: Dict[str, Any]) -> bool:
    """Save customer data to file with comprehensive validation."""
    try:
        required_fields = ["customer_id", "name", "mobile"]
        if not all(field in customer_data and customer_data[field] for field in required_fields):
            logger.error(f"Missing or empty required customer fields for save: {customer_data}")
            st.error("Missing required customer information (ID, Name, Mobile).")
            return False

        customer_data.setdefault("transactions", [])
        customer_data.setdefault("payment_history", [])
        customer_data.setdefault("items", [])
        customer_data["previous_balance"] = safe_float(customer_data.get("previous_balance", 0.0))

        filename = f"data/{customer_data['customer_id']}.json"
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(customer_data, f, indent=4, ensure_ascii=False)
        logger.info(f"Customer data saved for {customer_data['customer_id']}.")

        get_all_customers.clear()
        calculate_customer_balance.clear()
        return True
    except (PermissionError, json.JSONEncodeError) as e:
        logger.error(f"Error saving customer data for {customer_data.get('customer_id', 'N/A')}: {str(e)}")
        st.error(f"Permission or serialization error saving data: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving customer data for {customer_data.get('customer_id', 'N/A')}: {str(e)}")
        st.error(f"An unexpected error occurred while saving data: {str(e)}")
        return False


@st.cache_data(ttl=60)
def calculate_customer_balance(customer: Dict[str, Any]) -> float:
    """Calculate current balance for a customer."""
    total_rent_accrued = 0.0
    previous_balance_initial = safe_float(customer.get("previous_balance", 0))

    transactions_raw = customer.get("transactions", [])
    parsed_transactions = []
    for tx in transactions_raw:
        try:
            tx_date = dt.datetime.strptime(tx["date"], "%Y-%m-%d").date()
            parsed_transactions.append((tx_date, tx.get("item", ""), safe_float(tx.get("qty", 0))))
        except (ValueError, KeyError) as e:
            logger.warning(
                f"Skipping malformed transaction for customer {customer.get('customer_id', 'N/A')}: {tx}. Error: {e}")
            continue

    parsed_transactions.sort(key=lambda x: x[0])

    item_daily_rents = {item_info[0]: safe_float(item_info[1])
                        for item_info in customer.get("items", [])
                        if isinstance(item_info, (list, tuple)) and len(item_info) >= 2}

    current_item_quantities = {}

    if not parsed_transactions:
        approved_payments_sum = sum(safe_float(p.get("amount", 0)) for p in customer.get("payment_history", []) if
                                    p.get("status") == "approved")
        return previous_balance_initial - approved_payments_sum

    last_processed_date = None

    for item_name in item_daily_rents:
        current_item_quantities[item_name] = 0

    for i, (current_date, item_name, qty_change) in enumerate(parsed_transactions):
        if last_processed_date is not None:
            days_diff = (current_date - last_processed_date).days
            if days_diff > 0:
                for item, count in current_item_quantities.items():
                    if count > 0 and item in item_daily_rents:
                        total_rent_accrued += days_diff * count * item_daily_rents[item]

        if item_name in item_daily_rents:
            current_item_quantities[item_name] = current_item_quantities.get(item_name, 0) + qty_change

        last_processed_date = current_date

    if last_processed_date is not None:
        today = dt.date.today()
        days_since_last_tx = (today - last_processed_date).days
        if days_since_last_tx > 0:
            for item, count in current_item_quantities.items():
                if count > 0 and item in item_daily_rents:
                    total_rent_accrued += days_since_last_tx * count * item_daily_rents[item]

    approved_payments_sum = sum(
        safe_float(p.get("amount", 0)) for p in customer.get("payment_history", []) if p.get("status") == "approved")

    final_balance = previous_balance_initial + total_rent_accrued - approved_payments_sum
    return final_balance


# --- Enhanced Landing Page Components ---
def display_hero_section():
    """Display a clean, attractive hero section without images"""
    st.markdown("""
    <style>
        .hero-title {
            font-size: 2.5rem !important;
            color: #2E4053 !important;
            margin-bottom: 0.5rem !important;
            font-weight: 700 !important;
            text-align: center;
        }
        .hero-tagline {
            font-size: 1.25rem !important;
            color: #5D6D7E !important;
            text-align: center;
            margin-top: 0 !important;
            padding-bottom: 1rem;
        }
        .hero-divider {
            border-top: 3px solid #3498db;
            width: 80px;
            margin: 0 auto 1.5rem auto;
            opacity: 0.7;
        }
    </style>
    """, unsafe_allow_html=True)

    # Main hero content
    st.markdown("""
    <div style="padding: 2rem 1rem; margin-bottom: 2rem;">
        <div style="text-align: center; font-size: 4rem; margin-bottom: 1rem;">
            🏗️🔧🛠️
        </div>
        <h1 class="hero-title">{}</h1>
        <div class="hero-divider"></div>
        <p class="hero-tagline">{}</p>
    </div>
    """.format(
        company.get('name', 'Equipment Rental Portal'),
        company.get('tagline', 'Professional Tools & Shuttering Solutions')
    ), unsafe_allow_html=True)




# Usage


def display_features_section():
    """Display key features of the rental system."""
    st.markdown("### 🌟 Why Choose Us?")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        **🏗️ Quality Equipment**
        - Premium shuttering materials
        - Well-maintained inventory
        - Regular quality checks
        - Reliable performance
        """)

    with col2:
        st.markdown("""
        **📱 Digital Management**
        - Real-time balance tracking
        - Online payment system
        - Digital receipts
        - 24/7 account access
        """)

    with col3:
        st.markdown("""
        **🤝 Customer Support**
        - Dedicated support team
        - Flexible rental terms
        - Quick response time
        - Professional service
        """)


def display_contact_info():
    """Display contact information."""
    st.markdown("### 📞 Contact Information")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        **📍 Address:**  
        {company.get('address', 'N/A')}

        **📱 Mobile:**  
        {company.get('mobile', 'N/A')}

        **⏰ Business Hours:**  
        {company.get('business_hours', '9:00 AM - 6:00 PM')}
        """)

    with col2:
        if company.get('email'):
            st.markdown(f"**📧 Email:** {company.get('email')}")
        if company.get('website'):
            st.markdown(f"**🌐 Website:** {company.get('website')}")
        if company.get('established_year'):
            st.markdown(f"**📅 Established:** {company.get('established_year')}")

        # UPI QR Code for quick payments
        if company.get('upi_id'):
            st.markdown("**💳 Quick Payment via UPI:**")
            try:
                qr_img_bytes = generate_qr_code(company.get('upi_id', ''), None, company.get('name', ''))
                if qr_img_bytes and qr_img_bytes.getvalue():
                    st.image(qr_img_bytes, width=150, caption=f"Pay via UPI: {company.get('upi_id')}")
            except:
                st.write(f"UPI ID: `{company.get('upi_id')}`")


def display_statistics():
    """Display business statistics if available."""
    customers = get_all_customers()
    if customers:
        st.markdown("### 📊 Our Track Record")

        total_customers = len(customers)
        active_customers = sum(1 for c in customers if any(tx.get('qty', 0) > 0 for tx in c.get('transactions', [])))
        total_transactions = sum(len(c.get('transactions', [])) for c in customers)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("👥 Total Customers", total_customers)
        with col2:
            st.metric("🔄 Active Rentals", active_customers)
        with col3:
            st.metric("📋 Total Transactions", total_transactions)
        with col4:
            st.metric("🏆 Years of Service",
                      dt.date.today().year - int(company.get('established_year', dt.date.today().year)))


# --- PDF Generation (Enhanced) ---

def generate_comprehensive_bill(customer: Dict[str, Any]) -> io.BytesIO:
    """Generate a comprehensive rental bill with enhanced formatting."""
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Header with logo space
        pdf.set_font("helvetica", "B", 24)
        pdf.set_text_color(44, 62, 80)  # Dark blue
        pdf.cell(0, 15, company.get("name", "Company Name"), 0, 1, "C")

        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(100, 100, 100)
        contact_info = f"📱 {company.get('mobile', 'N/A')} | 📧 {company.get('email', 'N/A')} | 📍 {company.get('address', '')}"
        pdf.cell(0, 6, contact_info, 0, 1, "C")

        # Add line separator
        pdf.set_draw_color(52, 152, 219)
        pdf.set_line_width(0.5)
        pdf.line(10, pdf.get_y() + 5, 200, pdf.get_y() + 5)
        pdf.ln(10)

        # Bill title
        pdf.set_font("helvetica", "B", 18)
        pdf.set_text_color(231, 76, 60)  # Red
        pdf.cell(0, 12, "RENTAL BILL", 0, 1, "C")
        pdf.ln(8)

        # Customer details in a box
        pdf.set_fill_color(248, 249, 250)
        pdf.set_draw_color(200, 200, 200)
        pdf.rect(10, pdf.get_y(), 190, 30, 'DF')

        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, "CUSTOMER DETAILS", 0, 1, "C")

        pdf.set_font("helvetica", "", 10)
        pdf.cell(95, 6, f"Name: {customer.get('name', 'N/A')}", 0, 0)
        pdf.cell(95, 6, f"Customer ID: {customer.get('customer_id', 'N/A')}", 0, 1)
        pdf.cell(95, 6, f"Mobile: {customer.get('mobile', 'N/A')}", 0, 0)
        pdf.cell(95, 6, f"Bill Date: {format_date(dt.date.today())}", 0, 1)
        pdf.ln(8)

        # Transaction history with enhanced table
        pdf.set_font("helvetica", "B", 14)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 10, "TRANSACTION HISTORY", 0, 1)

        # Table header with colors
        pdf.set_fill_color(52, 152, 219)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("helvetica", "B", 10)

        pdf.cell(35, 8, "Date", 1, 0, 'C', True)
        pdf.cell(60, 8, "Item", 1, 0, 'C', True)
        pdf.cell(25, 8, "Quantity", 1, 0, 'C', True)
        pdf.cell(35, 8, "Rate/Day", 1, 0, 'C', True)
        pdf.cell(35, 8, "Action", 1, 1, 'C', True)

        # Table rows
        pdf.set_fill_color(245, 245, 245)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("helvetica", "", 9)

        transactions = customer.get("transactions", [])
        item_rates = {item[0]: safe_float(item[1]) for item in customer.get("items", [])}

        for i, tx in enumerate(sorted(transactions, key=lambda x: x.get("date", ""))):
            fill = i % 2 == 0
            action = "Returned" if safe_float(tx.get("qty", 0)) < 0 else "Rented"
            rate = item_rates.get(tx.get("item", ""), 0)

            pdf.cell(35, 7, format_date(tx.get("date")), 1, 0, 'C', fill)
            pdf.cell(60, 7, tx.get("item", "")[:25], 1, 0, 'L', fill)
            pdf.cell(25, 7, str(abs(int(safe_float(tx.get("qty", 0))))), 1, 0, 'C', fill)
            pdf.cell(35, 7, f"₹{rate:.2f}", 1, 0, 'C', fill)
            pdf.cell(35, 7, action, 1, 1, 'C', fill)

        pdf.ln(5)

        # Financial summary
        current_balance = calculate_customer_balance(customer)
        previous_balance = safe_float(customer.get("previous_balance", 0))
        payments_received = sum(safe_float(p.get("amount", 0)) for p in customer.get("payment_history", []) if
                                p.get("status") == "approved")
        total_rent = current_balance - previous_balance + payments_received

        # Summary box
        pdf.set_fill_color(248, 249, 250)
        pdf.rect(120, pdf.get_y(), 70, 40, 'DF')

        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 8, "PAYMENT SUMMARY", 0, 1, "R")

        pdf.set_font("helvetica", "", 10)
        pdf.cell(120, 6, "", 0, 0)
        pdf.cell(70, 6, f"Previous Balance: ₹{previous_balance:.2f}", 0, 1, "R")
        pdf.cell(120, 6, "", 0, 0)
        pdf.cell(70, 6, f"Rental Charges: ₹{total_rent:.2f}", 0, 1, "R")
        pdf.cell(120, 6, "", 0, 0)
        pdf.cell(70, 6, f"Payments Received: ₹{payments_received:.2f}", 0, 1, "R")

        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(231, 76, 60)
        pdf.cell(120, 8, "", 0, 0)
        pdf.cell(70, 8, f"Amount Due: ₹{current_balance:.2f}", 1, 1, "R")

        pdf.ln(10)

        # UPI QR Code section
        if company.get('upi_id') and current_balance > 0:
            pdf.set_font("helvetica", "B", 12)
            pdf.set_text_color(44, 62, 80)
            pdf.cell(0, 8, "QUICK PAYMENT", 0, 1, "C")

            qr_img_bytes = generate_qr_code(company.get('upi_id', ''), current_balance, company.get('name', ''))
            if qr_img_bytes and qr_img_bytes.getvalue():
                qr_img = Image.open(qr_img_bytes)
                qr_path = "temp_qr.png"
                qr_img.save(qr_path)
                pdf.image(qr_path, x=pdf.w / 2 - 25, w=50)
                os.remove(qr_path)

            pdf.ln(35)
            pdf.set_font("helvetica", "", 10)
            pdf.cell(0, 5, f"Scan QR code to pay ₹{current_balance:.2f}", 0, 1, 'C')
            pdf.cell(0, 5, f"UPI ID: {company.get('upi_id', '')}", 0, 1, 'C')

        # Footer
        pdf.set_y(-25)
        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, "This is a computer-generated bill. No signature required.", 0, 1, "C")
        pdf.cell(0, 5, f"Generated on: {dt.datetime.now().strftime('%d-%b-%Y %H:%M:%S')}", 0, 1, "C")

        # Save to bytes buffer
        pdf_bytes = io.BytesIO()
        pdf.output(pdf_bytes)
        pdf_bytes.seek(0)
        return pdf_bytes

    except Exception as e:
        logger.error(f"Error generating comprehensive bill: {str(e)}")
        return io.BytesIO()


# --- Streamlit App Initialization ---

if not initialize_directories():
    st.stop()

company = load_company_settings()

st.set_page_config(
    page_title=f"{company['name']} - Portal",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .feature-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 1rem 0;
    }
    .contact-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        margin: 0.5rem 0;
    }
    .login-form {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

if 'session_cleanup_done' not in st.session_state:
    cleanup_count = cleanup_expired_sessions()
    if cleanup_count > 0:
        st.toast(f"Cleaned up {cleanup_count} expired sessions.", icon="🧹")
    st.session_state.session_cleanup_done = True


def initialize_streamlit_session_state():
    """Initialize Streamlit session state variables."""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = None
    if 'user_type' not in st.session_state:
        st.session_state.user_type = None
    if 'user_data' not in st.session_state:
        st.session_state.user_data = None
    if 'initial_load_done' not in st.session_state:
        st.session_state.initial_load_done = False


initialize_streamlit_session_state()

if not st.session_state.initial_load_done:
    if st.session_state.session_id:
        session_data_refreshed = get_session(st.session_state.session_id)
        if session_data_refreshed:
            st.session_state.user_data = session_data_refreshed["user_data"]
            if st.session_state.user_type == "customer":
                latest_customer_data = authenticate_customer(st.session_state.user_data.get("customer_id"))
                if latest_customer_data:
                    st.session_state.user_data = latest_customer_data
                else:
                    st.session_state.session_id = None
                    st.session_state.user_type = None
                    st.session_state.user_data = None
                    st.warning("Your customer data could not be loaded. Please log in again.")
                    time.sleep(0.5)
                    st.rerun()
            logger.info(f"Session {st.session_state.session_id[:8]}... re-established.")
        else:
            st.session_state.session_id = None
            st.session_state.user_type = None
            st.session_state.user_data = None
            st.warning("Your session has expired or is invalid. Please log in again.")
            time.sleep(0.5)
            st.rerun()
    st.session_state.initial_load_done = True

# --- Enhanced Sidebar ---
with st.sidebar:
    st.markdown("---")

    
        
    st.title("🔐 Login")
    login_type = "Admin"

   
    if login_type == "Admin":
        st.subheader("Admin Login")
        with st.form("admin_login_form"):
            admin_password_input = st.text_input("Password", type="password").strip()
            admin_login_button = st.form_submit_button("🔑 Admin Login", use_container_width=True, type="primary")

        if admin_login_button:
            if not admin_password_input:
                st.error("Please enter the admin password.")
            elif hash_password(admin_password_input) == company["admin_password_hash"]:
                session_id = create_session("admin", "admin")
                if session_id:
                    st.session_state.session_id = session_id
                    st.session_state.user_type = "admin"
                    st.session_state.user_data = {"username": "admin"}
                    st.success("Admin login successful!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Failed to create admin session.")
            else:
                st.error("Invalid admin password.")

        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.title("👋 Welcome!")
        if st.session_state.user_type == "customer":
            st.markdown(f"**👤 {st.session_state.user_data.get('name', 'Customer')}**")
            st.caption(f"ID: `{st.session_state.user_data.get('customer_id', 'N/A')}`")

            # Quick balance display
            try:
                balance = calculate_customer_balance(st.session_state.user_data)
                if balance > 0:
                    st.error(f"💰 Due: {format_currency(balance)}")
                elif balance < 0:
                    st.success(f"💰 Advance: {format_currency(abs(balance))}")
                else:
                    st.info("💰 Balance: Clear")
            except:
                pass
        else:
            st.markdown("**👨‍💼 Administrator**")

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True, type="secondary",key=123):
            if st.session_state.session_id and delete_session(st.session_state.session_id):
                st.session_state.session_id = None
                st.session_state.user_type = None
                st.session_state.user_data = None
                st.success("Logged out successfully!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Error logging out.")

    
# --- Main Content Area ---

if st.session_state.user_type == "customer":
    customer_id_in_session = st.session_state.user_data.get("customer_id")
    customer = authenticate_customer(customer_id_in_session)
    if not customer:
        st.error("Your data could not be loaded. Please log in again.")
        st.session_state.session_id = None
        st.session_state.user_type = None
        st.session_state.user_data = None
        time.sleep(0.5)
        st.rerun()

    st.markdown(f"# 👋 Welcome, {customer.get('name', 'Customer')}")
    st.markdown(f"**Customer ID:** `{customer.get('customer_id', 'N/A')}`")
    st.markdown("---")
    hide_st_style = """
                    <style>
                    MainMenu {visibility: hidden;}
                    headerNoPadding {visibility: hidden;}
                    _terminalButton_rix23_138 {visibility: hidden;}
                    header {visibility: hidden;}
                    </style>
                    """
    st.markdown(hide_st_style, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📋 Rental History", "💳 Payments", "💰 Make Payment"])

    with tab1:
        st.subheader("Account Summary")
        try:
            current_balance = calculate_customer_balance(customer)
            payment_received = sum(safe_float(p.get("amount", 0)) for p in customer.get("payment_history", []) if
                                   p.get("status") == "approved")
            
            if current_balance > 0:
                # Enhanced balance display
                col1, col2 = st.columns(2)
                with col1:
                    if current_balance > 0:
                        st.error(f"💰 Outstanding Balance: {format_currency(current_balance)}")
                        st.caption("⚠️ Payment required to clear dues")
                    elif current_balance == 0:
                        st.success("✅ No Outstanding Dues")
                        st.caption("🎉 Your account is clear!")
                    else:
                        st.info(f"💰 Advance Balance: {format_currency(abs(current_balance))}")
                        st.caption("💎 You have credit in your account")



                st.markdown("---")

                # Enhanced UPI Payment Section
                st.subheader("📱 Quick UPI Payment")
                
                # Generate UPI payment link
                upi_id = company.get('upi_id', '')
                company_name = company.get('name', 'Jammu Shuttering Store')
                amount = max(0.0, current_balance) if current_balance > 0 else None
                tn = f"Payment for {customer.get('customer_id', '')}"
                
                upi_url = f"upi://pay?pa={upi_id}&pn={company_name.replace(' ', '%20')}"
                if amount:
                    upi_url += f"&am={amount:.2f}"
                upi_url += "&cu=INR"
                if tn:
                    upi_url += f"&tn={tn.replace(' ', '%20')}"

                col1, col2 = st.columns([3, 2])

                with col1:
                    st.markdown(f"""
                    **🚀 Fast UPI Payment Steps:**
                    1. Open any UPI app (Google Pay, PhonePe, Paytm, etc.)
                    2. Scan the QR code or click the payment button below
                    3. Verify amount: **{format_currency(amount) if amount else 'Enter Manually'}**
                    4. Complete payment and note the transaction ID
                    5. Submit payment details using the form above

                    💡 **Pro Tip:** Screenshot the payment confirmation for reference
                    """)

                    if current_balance > 0:
                        st.info(f"💰 **Recommended Payment:** {format_currency(current_balance)} (clears all dues)")
                        
                        # Add UPI payment button
                        st.markdown(f"""
                        <a href="{upi_url}" style="text-decoration: none;">
                            <button style="
                                background-color: #4CAF50;
                                color: white;
                                padding: 12px 24px;
                                border: none;
                                border-radius: 8px;
                                font-size: 16px;
                                cursor: pointer;
                                width: 100%;
                                margin-top: 10px;
                            ">
                                Pay Now via UPI
                            </button>
                        </a>
                        """, unsafe_allow_html=True)

                with col2:
                    if company.get('upi_id'):
                        try:
                            qr_img_bytes = generate_qr_code(upi_id, amount, company_name)
                            if qr_img_bytes and qr_img_bytes.getvalue():
                                st.image(qr_img_bytes, width=200,
                                        caption=f"Scan to pay via UPI")
                                st.code(f"UPI ID: {upi_id}", language=None)
                                
                                # Display UPI payment details
                                st.markdown("**Payment Details:**")
                                st.markdown(f"""
                                - **UPI ID:** `{upi_id}`
                                - **Payee Name:** {company_name}
                                - **Amount:** {format_currency(amount) if amount else 'Variable'}
                                - **Note:** {tn}
                                """)
                            else:
                                st.warning("⚠️ QR code generation failed")
                        except Exception as e:
                            st.error(f"Error displaying QR code: {str(e)}")
                    else:
                        st.info("🔧 UPI ID not configured. Contact admin.")


            col1, col2, col3 = st.columns(3)
            with col1:
                balance_color = "normal"
                if current_balance > 0:
                    balance_color = "inverse"
                elif current_balance < 0:
                    balance_color = "off"
                st.metric("Current Balance", format_currency(current_balance),
                          delta_color=balance_color)
            with col2:
                st.metric("Total Paid (Approved)", format_currency(payment_received))
            with col3:
                approved_payments = [p for p in customer.get("payment_history", []) if p.get("status") == "approved"]
                last_payment_date_display = "Never"
                if approved_payments:
                    latest_payment = max(approved_payments, key=lambda p: p.get("date", "1900-01-01"))
                    last_payment_date_display = format_date(latest_payment.get("date", ""))
                st.metric("Last Approved Payment", last_payment_date_display)

            # Balance trend chart
            if len(customer.get("payment_history", [])) > 1:
                st.subheader("Payment History Trend")
                payments_df = pd.DataFrame([
                    {"Date": p.get("date"), "Amount": safe_float(p.get("amount", 0))}
                    for p in customer.get("payment_history", []) if p.get("status") == "approved"
                ])
                if not payments_df.empty:
                    payments_df["Date"] = pd.to_datetime(payments_df["Date"])
                    fig = px.line(payments_df, x="Date", y="Amount",
                                  title="Payment History", markers=True)
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)

            st.subheader("Currently Rented Items")
            in_hand_quantities = {}
            for tx in customer.get("transactions", []):
                in_hand_quantities[tx.get("item")] = in_hand_quantities.get(tx.get("item"), 0) + safe_float(
                    tx.get("qty", 0))

            rented_items = [(item, qty) for item, qty in in_hand_quantities.items() if qty > 0]
            if not rented_items:
                st.info("📋 No rental items currently in your possession.")
            else:
                df_data = []
                item_daily_rents = {item[0]: safe_float(item[1]) for item in customer.get("items", [])}
                for item, qty in rented_items:
                    daily_rent = item_daily_rents.get(item, 0.0)
                    df_data.append({
                        "Item": item,
                        "Quantity": int(qty),
                        "Daily Rent": format_currency(daily_rent),
                        "Total/Day": format_currency(qty * daily_rent)
                    })
                st.dataframe(pd.DataFrame(df_data), hide_index=True, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading dashboard: {str(e)}")

    with tab2:  # Rental History
        st.subheader("Your Rental Transaction History")
        transactions = customer.get("transactions", [])
        if not transactions:
            st.info("📋 No rental history found.")
        else:
            # Enhanced transaction display with filters 
            col1, col2 = st.columns(2)
            with col1:
                item_filter = st.selectbox(
                    "Filter by Item",
                    ["All Items"] + list(set(tx.get("item", "") for tx in transactions)),
                    key="item_filter"
                )
            with col2:
                date_range = st.date_input(
                    "Date Range",
                    value=(dt.date.today() - dt.timedelta(days=30), dt.date.today()),
                    key="date_range"
                )

            # Filter transactions
            filtered_transactions = transactions
            if item_filter != "All Items":
                filtered_transactions = [tx for tx in transactions if tx.get("item") == item_filter]

            if len(date_range) == 2:
                start_date, end_date = date_range
                filtered_transactions = [
                    tx for tx in filtered_transactions
                    if start_date <= dt.datetime.strptime(tx.get("date", "1900-01-01"), "%Y-%m-%d").date() <= end_date
                ]

            tx_df_data = []
            sorted_transactions = sorted(filtered_transactions, key=lambda x: x.get("date", "1900-01-01"), reverse=True)
            for tx in sorted_transactions:
                action = "🔴 Returned" if safe_float(tx.get("qty")) < 0 else "🟢 Rented"
                tx_df_data.append({
                    "Date": format_date(tx.get("date")),
                    "Item": tx.get("item"),
                    "Action": action,
                    "Quantity": abs(int(safe_float(tx.get("qty"))))
                })

            if tx_df_data:
                df = pd.DataFrame(tx_df_data)
                st.dataframe(df, hide_index=True, use_container_width=True)
            else:
                st.info("No transactions found for the selected filters.")

            # Enhanced Bill Generation
            if st.button("📄 Generate Comprehensive Rental Bill PDF", use_container_width=True, type="primary"):
                try:
                    with st.spinner("Generating comprehensive bill..."):
                        pdf_bytes = generate_comprehensive_bill(customer)
                        if pdf_bytes and pdf_bytes.getvalue():
                            st.download_button(
                                "📥 Download Comprehensive Bill",
                                pdf_bytes,
                                f"Comprehensive_Bill_{customer.get('customer_id', '')}_{dt.date.today().strftime('%Y%m%d')}.pdf",
                                "application/pdf",
                                use_container_width=True
                            )
                            st.success("✅ Bill generated successfully!")
                        else:
                            st.error("Failed to generate bill.")
                except Exception as e:
                    st.error(f"Error generating bill: {str(e)}")

    with tab3:  # Payments
        st.subheader("Payment History & Status")

        # Payment status overview
        all_payments = customer.get("payment_history", [])
        pending_payments = [p for p in all_payments if p.get("status") == "pending"]
        approved_payments = [p for p in all_payments if p.get("status") == "approved"]
        rejected_payments = [p for p in all_payments if p.get("status") == "rejected"]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("✅ Approved", len(approved_payments))
        with col2:
            st.metric("⏳ Pending", len(pending_payments))
        with col3:
            st.metric("❌ Rejected", len(rejected_payments))

        if pending_payments:
            st.warning("⏳ You have payments awaiting admin approval.")
            st.subheader("Pending Payments")
            pending_df_data = [
                {
                    "Date": format_date(p.get("date")),
                    "Amount": format_currency(safe_float(p.get('amount'))),
                    "Method": p.get("method"),
                    "Reference": p.get("reference", "N/A"),
                    "Status": "⏳ Pending"
                } for p in pending_payments
            ]
            st.dataframe(pd.DataFrame(pending_df_data), hide_index=True, use_container_width=True)

        if rejected_payments:
            st.error("❌ Some payments were rejected.")
            with st.expander("View Rejected Payments"):
                rejected_df_data = [
                    {
                        "Date": format_date(p.get("date")),
                        "Amount": format_currency(safe_float(p.get('amount'))),
                        "Method": p.get("method"),
                        "Reference": p.get("reference", "N/A"),
                        "Status": "❌ Rejected"
                    } for p in rejected_payments
                ]
                st.dataframe(pd.DataFrame(rejected_df_data), hide_index=True, use_container_width=True)

        if approved_payments:
            st.success("✅ Approved Payment History")
            payment_df_data = []
            sorted_payments = sorted(approved_payments, key=lambda p: p.get("date", "1900-01-01"), reverse=True)
            for p in sorted_payments:
                payment_df_data.append({
                    "Date": format_date(p.get("date")),
                    "Amount": format_currency(safe_float(p.get('amount'))),
                    "Method": p.get("method"),
                    "Reference": p.get("reference", "N/A"),
                    "Receipt No": p.get("id", "N/A")
                })
            df_payments = pd.DataFrame(payment_df_data)
            st.dataframe(df_payments, hide_index=True, use_container_width=True)
        else:
            st.info("💳 No approved payment history found.")

    with tab4:  # Make Payment
        st.subheader("💰 Make a Payment")

        try:
            current_balance = calculate_customer_balance(customer)

            # Enhanced balance display
            col1, col2 = st.columns(2)
            with col1:
                if current_balance > 0:
                    st.error(f"💰 Outstanding Balance: {format_currency(current_balance)}")
                    st.caption("⚠️ Payment required to clear dues")
                elif current_balance == 0:
                    st.success("✅ No Outstanding Dues")
                    st.caption("🎉 Your account is clear!")
                else:
                    st.info(f"💰 Advance Balance: {format_currency(abs(current_balance))}")
                    st.caption("💎 You have credit in your account")

            with col2:
                # Payment suggestions
                if current_balance > 0:
                    suggested_amounts = [
                        current_balance,
                        round(current_balance * 1.1, 2),  # 10% extra 🔐 Login
                        max(500, round(current_balance / 2, 2))  # Half payment
                    ]
                    st.write("💡 **Suggested Amounts:**")
                    for amount in suggested_amounts[:2]:
                        if st.button(f"Pay {format_currency(amount)}", key=f"suggest_{amount}"):
                            st.session_state.suggested_amount = amount

            st.markdown("---")

            with st.form("enhanced_payment_form", clear_on_submit=True):
                st.markdown("### 💳 Payment Details")

                col1, col2 = st.columns(2)

                with col1:
                    default_amount = getattr(st.session_state, 'suggested_amount',
                                             max(0.01, current_balance if current_balance > 0 else 0.01))
                    amount = st.number_input(
                        "💰 Amount to Pay",
                        min_value=0.01,
                        max_value=1000000.0,
                        value=float(default_amount),
                        step=100.0,
                        format="%.2f"
                    )

                    method = st.selectbox(
                        "💳 Payment Method",
                        ["UPI", "Bank Transfer", "Cash", "Cheque", "Online Banking", "Card Payment", "Other"],
                        help="Select your preferred payment method"
                    )

                with col2:
                    reference = st.text_input(
                        "🔖 Transaction Reference",
                        placeholder="UPI Ref: 1234567890 or Cheque No: 123456",
                        help="Required for digital payments"
                    ).strip()

                    payment_date = st.date_input(
                        "📅 Payment Date",
                        value=dt.date.today(),
                        max_value=dt.date.today()
                    )

                notes = st.text_area(
                    "📝 Additional Notes (Optional)",
                    placeholder="Any special instructions or notes about this payment...",
                    height=80
                ).strip()

                st.markdown("---")
                st.markdown("### 📋 Payment Review")

                # Payment impact calculation
                balance_after = current_balance - amount

                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"💰 **Payment Amount:** {format_currency(amount)}")
                    st.info(f"💳 **Method:** {method}")
                    if reference:
                        st.info(f"🔖 **Reference:** {reference}")

                with col2:
                    if balance_after > 0:
                        st.warning(f"📊 **Remaining Balance:** {format_currency(balance_after)}")
                    elif balance_after < 0:
                        st.success(f"📊 **Credit Balance:** {format_currency(abs(balance_after))}")
                    else:
                        st.success("📊 **Account will be cleared** ✅")

                st.warning("⏳ **Note:** Payment will be marked as 'Pending' until admin approval.")

                submitted = st.form_submit_button(
                    "🚀 Submit Payment for Approval",
                    use_container_width=True,
                    type="primary"
                )

                if submitted:
                    # Enhanced validation
                    errors = []
                    if amount <= 0:
                        errors.append("Amount must be greater than zero")
                    if method in ["UPI", "Bank Transfer", "Online Banking", "Card Payment"] and not reference:
                        errors.append("Transaction reference is required for digital payments")
                    if len(reference) > 100:
                        errors.append("Reference text is too long (max 100 characters)")

                    if errors:
                        for error in errors:
                            st.error(f"❌ {error}")
                    else:
                        try:
                            with st.spinner("Processing your payment..."):
                                payment_id = f"PAY-{dt.datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"
                                new_payment = {
                                    "id": payment_id,
                                    "date": payment_date.strftime("%Y-%m-%d"),
                                    "amount": amount,
                                    "method": method,
                                    "reference": reference,
                                    "notes": notes,
                                    "created_at": dt.datetime.now().isoformat(),
                                    "status": "pending",
                                    "approved_by": None,
                                    "approved_at": None
                                }

                                customer.setdefault("payment_history", []).append(new_payment)

                                if save_customer_data(customer):
                                    st.session_state.user_data = customer
                                    st.success(f"🎉 Payment of {format_currency(amount)} submitted successfully!")
                                    st.info(f"📋 Payment ID: `{payment_id}`")
                                    st.info(
                                        "⏳ Your payment is awaiting admin approval. Balance will update once approved.")
                                    st.balloons()

                                    # Clear suggested amount
                                    if hasattr(st.session_state, 'suggested_amount'):
                                        delattr(st.session_state, 'suggested_amount')

                                    time.sleep(1.5)
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to save payment. Please try again.")

                        except Exception as e:
                            st.error(f"❌ Error processing payment: {str(e)}")
                            logger.error(f"Payment processing error: {str(e)}")

            # Enhanced UPI Payment Section
            st.markdown("---")
            st.subheader("📱 Quick UPI Payment")

            col1, col2 = st.columns([3, 2])

            with col1:
                st.markdown(f"""
                **🚀 Fast UPI Payment Steps:**
                1. Open any UPI app (Google Pay, PhonePe, Paytm, etc.)
                2. Scan the QR code or use UPI ID: `{company.get('upi_id', 'N/A')}`
                3. Enter amount: **{format_currency(max(0.0, current_balance))}**
                4. Complete payment and note the transaction ID
                5. Submit payment details using the form above

                💡 **Pro Tip:** Screenshot the payment confirmation for reference
                """)
                upi_id = company.get('upi_id', '')
                company_name = company.get('name', 'Jammu Shuttering Store')
                amount = max(0.0, current_balance) if current_balance > 0 else None
                tn = f"Payment for {customer.get('customer_id', '')}"
                
                upi_url = f"upi://pay?pa={upi_id}&pn={company_name.replace(' ', '%20')}"
                if amount:
                    upi_url += f"&am={amount:.2f}"
                upi_url += "&cu=INR"
                if tn:
                    upi_url += f"&tn={tn.replace(' ', '%20')}"
                


                if current_balance > 0:
                    st.info(f"💰 **Recommended Payment:** {format_currency(current_balance)} (clears all dues)")

            with col2:
                if company.get('upi_id'):
                    try:
                        qr_amount = max(0.0, current_balance) if current_balance > 0 else None
                        qr_img_bytes = generate_qr_code(company.get('upi_id', ''), qr_amount, company.get('name', ''))
                        if qr_img_bytes and qr_img_bytes.getvalue():
                            st.image(qr_img_bytes, width=200,
                                     caption=f"Scan to pay via UPI")
                            st.markdown(f"""
                        <a href="{upi_url}" style="text-decoration: none;">
                            <button style="
                                background-color: #4CAF50;
                                color: white;
                                padding: 12px 24px;
                                border: none;
                                border-radius: 8px;
                                font-size: 16px;
                                cursor: pointer;
                                width: 100%;
                                margin-top: 10px;
                            ">
                                Pay Now via UPI
                            </button>
                        </a>
                        """, unsafe_allow_html=True)
                        else:
                            st.warning("⚠️ QR code generation failed")
                    except Exception as e:
                        st.error(f"Error displaying QR code: {str(e)}")
                else:
                    st.info("🔧 UPI ID not configured. Contact admin.")


        except Exception as e:
            st.error(f"Error in payment section: {str(e)}")
            logger.error(f"Payment tab error: {str(e)}")
    if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            if st.session_state.session_id and delete_session(st.session_state.session_id):
                st.session_state.session_id = None
                st.session_state.user_type = None
                st.session_state.user_data = None
                st.success("Logged out successfully!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Error logging out.")

elif st.session_state.user_type == "admin":
    st.title("🛠️ Admin Control Panel")

    # Admin stats overview
    customers = get_all_customers()
    total_customers = len(customers)
    total_dues = sum(max(0, calculate_customer_balance(c)) for c in customers)
    pending_payments = sum(
        len([p for p in c.get("payment_history", []) if p.get("status") == "pending"]) for c in customers)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Total Customers", total_customers)
    with col2:
        st.metric("💰 Total Outstanding", format_currency(total_dues))
    with col3:
        st.metric("⏳ Pending Approvals", pending_payments)
    with col4:
        active_rentals = sum(1 for c in customers if any(
            sum(safe_float(tx.get("qty", 0)) for tx in c.get("transactions", []) if tx.get("item") == item) > 0
            for item in set(tx.get("item") for tx in c.get("transactions", []))
        ))
        st.metric("🔄 Active Rentals", active_rentals)

    admin_tabs = st.tabs(["📊 Dashboard", "👥 Customers", "✅ Payment Approvals", "📈 Reports", "⚙️ Settings", "🔧 System"])

    with admin_tabs[0]:  # Enhanced Dashboard
        st.subheader("📊 Business Analytics")

        if customers:
            # Revenue analytics
            col1, col2 = st.columns(2)

            with col1:
                # Top customers by outstanding balance
                customer_balances = [(c.get('name'), calculate_customer_balance(c)) for c in customers]
                customer_balances = [(name, balance) for name, balance in customer_balances if balance > 0]
                customer_balances.sort(key=lambda x: x[1], reverse=True)

                if customer_balances:
                    st.subheader("🔝 Top Outstanding Balances")
                    top_customers_df = pd.DataFrame(customer_balances[:10], columns=["Customer", "Balance"])
                    top_customers_df["Balance"] = top_customers_df["Balance"].apply(format_currency)
                    st.dataframe(top_customers_df, hide_index=True, use_container_width=True)

            with col2:
                # Payment methods distribution
                all_payments = []
                for c in customers:
                    all_payments.extend([p for p in c.get("payment_history", []) if p.get("status") == "approved"])

                if all_payments:
                    method_counts = {}
                    for p in all_payments:
                        method = p.get("method", "Unknown")
                        method_counts[method] = method_counts.get(method, 0) + 1

                    st.subheader("💳 Payment Methods Distribution")
                    fig = px.pie(values=list(method_counts.values()), names=list(method_counts.keys()))
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)

            # Monthly revenue trend
            if all_payments:
                st.subheader("📈 Monthly Revenue Trend")
                payments_df = pd.DataFrame([
                    {"Date": p.get("date"), "Amount": safe_float(p.get("amount", 0))}
                    for p in all_payments
                ])
                payments_df["Date"] = pd.to_datetime(payments_df["Date"])
                payments_df["Month"] = payments_df["Date"].dt.to_period("M")
                monthly_revenue = payments_df.groupby("Month")["Amount"].sum().reset_index()
                monthly_revenue["Month"] = monthly_revenue["Month"].astype(str)

                fig = px.bar(monthly_revenue, x="Month", y="Amount", title="Monthly Revenue")
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

    with admin_tabs[1]:  # Enhanced Customers Management
        st.subheader("👥 Customer Management")

        # Customer overview metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            customers_with_dues = sum(1 for c in customers if calculate_customer_balance(c) > 0)
            st.metric("Customers with Dues", customers_with_dues)
        with col2:
            avg_balance = sum(calculate_customer_balance(c) for c in customers) / len(customers) if customers else 0
            st.metric("Average Balance", format_currency(avg_balance))
        with col3:
            customers_with_advance = sum(1 for c in customers if calculate_customer_balance(c) < 0)
            st.metric("Customers with Advance", customers_with_advance)

        # Enhanced Add Customer
        with st.expander("✨ Add New Customer", expanded=False):
            with st.form("enhanced_new_customer_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Full Name*").strip()
                    mobile = st.text_input("Mobile Number*").strip()
                    cust_id = st.text_input("Customer ID (auto-generated if empty)").strip()
                with col2:
                    address = st.text_area("Address (Optional)", height=100).strip()
                    previous_balance = st.number_input("Previous Balance", value=0.0, format="%.2f")
                    email = st.text_input("Email (Optional)").strip()

                add_button = st.form_submit_button("➕ Add Customer", type="primary", use_container_width=True)

                if add_button:
                    if not name or not mobile:
                        st.error("❌ Name and Mobile are required.")
                    elif len(mobile) != 10 or not mobile.isdigit():
                        st.error("❌ Please enter a valid 10-digit mobile number.")
                    else:
                        if not cust_id:
                            cust_id = f"CUST-{dt.date.today().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"

                        # Check for duplicates
                        if any(c.get('customer_id') == cust_id for c in customers):
                            st.error("❌ Customer ID already exists.")
                        elif any(c.get('mobile') == mobile for c in customers):
                            st.error("❌ Mobile number already registered.")
                        else:
                            new_customer = {
                                "customer_id": cust_id,
                                "name": name,
                                "mobile": mobile,
                                "address": address,
                                "email": email,
                                "previous_balance": previous_balance,
                                "payment_history": [],
                                "transactions": [],
                                "items": [],
                                "created_at": dt.datetime.now().isoformat()
                            }
                            if save_customer_data(new_customer):
                                st.success(f"✅ Customer '{name}' added successfully with ID '{cust_id}'.")
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Failed to add customer.")

        # Enhanced Bulk Upload
        with st.expander("📂 Bulk Customer Import (JSON)", expanded=False):
            st.info("""
            📋 **Upload Format:** JSON array with customer objects
            📝 **Required fields:** `name`, `mobile`
            🔧 **Optional fields:** `customer_id`, `address`, `email`, `previous_balance`, `items`, `transactions`, `payment_history`
            """)

            uploaded_file = st.file_uploader("Choose JSON file", type="json", key="bulk_upload_enhanced")

            if uploaded_file is not None:
                try:
                    content = uploaded_file.getvalue().decode("utf-8").strip()
                    if content.startswith("[") and content.endswith("]"):
                        new_customers = json.loads(content)
                    else:
                        new_customers = json.loads("[" + content.rstrip(",") + "]")

                    if not isinstance(new_customers, list):
                        st.error("❌ JSON must be an array of customer objects")
                    else:
                        existing_customers = get_all_customers()
                        existing_mobiles = {c['mobile'] for c in existing_customers}
                        existing_ids = {c['customer_id'] for c in existing_customers}

                        results = {"added": 0, "skipped": 0, "errors": []}

                        progress_bar = st.progress(0)
                        status_text = st.empty()

                        for i, customer in enumerate(new_customers):
                            progress_bar.progress((i + 1) / len(new_customers))
                            status_text.text(f"Processing customer {i + 1}/{len(new_customers)}")

                            try:
                                if not all(key in customer for key in ['name', 'mobile']):
                                    results["errors"].append(f"Missing required fields in customer {i + 1}")
                                    continue

                                mobile = customer['mobile'].strip()
                                name = customer['name'].strip()

                                if mobile in existing_mobiles:
                                    results["skipped"] += 1
                                    results["errors"].append(f"Duplicate mobile: {mobile}")
                                    continue

                                customer_id = customer.get('customer_id')
                                if not customer_id:
                                    customer_id = f"CUST-{dt.date.today().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
                                elif customer_id in existing_ids:
                                    results["skipped"] += 1
                                    results["errors"].append(f"Duplicate ID: {customer_id}")
                                    continue

                                new_customer_data = {
                                    "customer_id": customer_id,
                                    "name": name,
                                    "mobile": mobile,
                                    "address": customer.get("address", ""),
                                    "email": customer.get("email", ""),
                                    "previous_balance": safe_float(customer.get("previous_balance", 0.0)),
                                    "payment_history": customer.get("payment_history", []),
                                    "transactions": customer.get("transactions", []),
                                    "items": customer.get("items", []),
                                    "created_at": dt.datetime.now().isoformat()
                                }

                                if save_customer_data(new_customer_data):
                                    results["added"] += 1
                                    existing_mobiles.add(mobile)
                                    existing_ids.add(customer_id)
                                else:
                                    results["errors"].append(f"Failed to save: {customer_id}")

                            except Exception as e:
                                results["errors"].append(f"Error processing customer {i + 1}: {str(e)}")

                        progress_bar.empty()
                        status_text.empty()

                        # Show results
                        if results["added"] > 0:
                            st.success(f"✅ Successfully added {results['added']} customers")
                        if results["skipped"] > 0:
                            st.warning(f"⏩ Skipped {results['skipped']} duplicates")
                        if results["errors"]:
                            with st.expander(f"⚠️ {len(results['errors'])} Issues Found", expanded=False):
                                for error in results["errors"][:10]:  # Show first 10 errors
                                    st.write(f"• {error}")
                                if len(results["errors"]) > 10:
                                    st.write(f"... and {len(results['errors']) - 10} more errors")

                        if results["added"] > 0:
                            st.rerun()

                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON format: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Unexpected error: {str(e)}")

        # Enhanced Customer List with Search and Filters
        st.markdown("### 📋 Customer Directory")

        col1, col2, col3 = st.columns(3)
        with col1:
            search_term = st.text_input("🔍 Search Customers", placeholder="Name, ID, or Mobile")
        with col2:
            balance_filter = st.selectbox("💰 Balance Filter", ["All", "Has Dues", "Has Advance", "Zero Balance"])
        with col3:
            sort_by = st.selectbox("📊 Sort By", ["Name", "Balance", "Recent Activity"])

        # Filter and sort customers
        filtered_customers = customers
        if search_term:
            filtered_customers = [
                c for c in customers
                if search_term.lower() in c.get('name', '').lower()
                   or search_term.lower() in c.get('customer_id', '').lower()
                   or search_term in c.get('mobile', '')
            ]

        if balance_filter != "All":
            if balance_filter == "Has Dues":
                filtered_customers = [c for c in filtered_customers if calculate_customer_balance(c) > 0]
            elif balance_filter == "Has Advance":
                filtered_customers = [c for c in filtered_customers if calculate_customer_balance(c) < 0]
            elif balance_filter == "Zero Balance":
                filtered_customers = [c for c in filtered_customers if calculate_customer_balance(c) == 0]

        # Sort customers
        if sort_by == "Balance":
            filtered_customers.sort(key=lambda c: calculate_customer_balance(c), reverse=True)
        elif sort_by == "Recent Activity":
            filtered_customers.sort(key=lambda c: max(
                [p.get('date', '1900-01-01') for p in c.get('payment_history', [])] or ['1900-01-01']), reverse=True)
        else:  # Name
            filtered_customers.sort(key=lambda c: c.get('name', '').lower())

        # Display customers
        if filtered_customers:
            customer_display_data = []
            for cust in filtered_customers:
                balance = calculate_customer_balance(cust)
                last_payment = "Never"
                payments = [p for p in cust.get("payment_history", []) if p.get("status") == "approved"]
                if payments:
                    latest = max(payments, key=lambda p: p.get("date", "1900-01-01"))
                    last_payment = format_date(latest.get("date"))

                customer_display_data.append({
                    "ID": cust.get('customer_id'),
                    "Name": cust.get('name'),
                    "Mobile": cust.get('mobile'),
                    "Balance": format_currency(balance),
                    "Last Payment": last_payment,
                    "Balance_raw": balance  # For sorting
                })

            df_customers = pd.DataFrame(customer_display_data)
            st.dataframe(df_customers[["ID", "Name", "Mobile", "Balance", "Last Payment"]],
                         use_container_width=True, hide_index=True, height=400)
        else:
            st.info("📋 No customers found matching your criteria.")

        # Enhanced Customer Details
        if filtered_customers:
            st.markdown("### 🔍 Customer Details & Management")
            cust_options = {
                f"{c.get('name')} ({c.get('customer_id')}) - {format_currency(calculate_customer_balance(c))}": c.get(
                    'customer_id') for c in filtered_customers}
            selected_cust_display = st.selectbox("Select Customer for Detailed View", cust_options.keys(), index=None)

            if selected_cust_display:
                selected_id = cust_options[selected_cust_display]
                customer_data = next((c for c in customers if c.get("customer_id") == selected_id), None)

                if customer_data:
                    st.markdown(f"#### 👤 Managing: {customer_data['name']}")

                    # Customer info tabs
                    info_tabs = st.tabs(["📝 Basic Info", "🏗️ Items & Rates", "📋 Transactions", "💳 Payment History"])

                    with info_tabs[0]:  # Basic Info
                        with st.form(key=f"edit_info_{selected_id}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                customer_data['name'] = st.text_input("Name", value=customer_data.get('name', ''))
                                customer_data['mobile'] = st.text_input("Mobile", value=customer_data.get('mobile', ''))
                                customer_data['email'] = st.text_input("Email", value=customer_data.get('email', ''))
                            with col2:
                                customer_data['address'] = st.text_area("Address",
                                                                        value=customer_data.get('address', ''),
                                                                        height=100)
                                customer_data['previous_balance'] = st.number_input(
                                    "Previous Balance Adjustment",
                                    value=safe_float(customer_data.get('previous_balance', 0.0)),
                                    format="%.2f"
                                )

                            if st.form_submit_button("💾 Save Changes", type="primary"):
                                if save_customer_data(customer_data):
                                    st.success("✅ Customer information updated successfully!")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to update customer information.")

                    with info_tabs[1]:  # Items & Rates
                        st.markdown("##### 🏗️ Rental Items & Daily Rates")

                        current_items = customer_data.get("items", [])
                        if current_items:
                            items_df = pd.DataFrame(current_items, columns=["Item Name", "Daily Rate (₹)"])
                            st.dataframe(items_df, use_container_width=True, hide_index=True)
                        else:
                            st.info("📋 No items configured for this customer.")

                        # Add new item
                        with st.form(key=f"add_item_{selected_id}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                item_name = st.text_input("🏗️ Item Name").strip()
                            with col2:
                                item_rent = st.number_input("💰 Daily Rent (₹)", min_value=0.0, format="%.2f")

                            if st.form_submit_button("➕ Add Item", type="primary"):
                                if item_name and item_rent >= 0:
                                    if not any(item[0] == item_name for item in customer_data.get('items', [])):
                                        customer_data.setdefault('items', []).append([item_name, item_rent])
                                        if save_customer_data(customer_data):
                                            st.success(f"✅ Item '{item_name}' added successfully!")
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to add item.")
                                    else:
                                        st.warning("⚠️ Item already exists for this customer.")
                                else:
                                    st.error("❌ Please provide valid item name and rent.")

                    with info_tabs[2]:  # Transactions
                        st.markdown("##### 📋 Transaction Management")

                        transactions = customer_data.get("transactions", [])
                        if transactions:
                            tx_display = []
                            for tx in sorted(transactions, key=lambda x: x.get("date", ""), reverse=True):
                                action = "🔴 Return" if safe_float(tx.get("qty", 0)) < 0 else "🟢 Rent"
                                tx_display.append({
                                    "Date": format_date(tx.get("date")),
                                    "Item": tx.get("item"),
                                    "Action": action,
                                    "Quantity": abs(int(safe_float(tx.get("qty", 0))))
                                })
                            st.dataframe(pd.DataFrame(tx_display), use_container_width=True, hide_index=True,
                                         height=300)
                        else:
                            st.info("📋 No transactions recorded.")

                        # Add new transaction
                        with st.form(key=f"add_tx_{selected_id}"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                item_options = [item[0] for item in customer_data.get("items", [])]
                                if item_options:
                                    tx_item = st.selectbox("🏗️ Item", item_options)
                                else:
                                    st.warning("⚠️ Please add items first")
                                    tx_item = None
                            with col2:
                                tx_qty = st.number_input("📦 Quantity", step=1, help="Positive: Rent, Negative: Return")
                            with col3:
                                tx_date = st.date_input("📅 Date", dt.date.today())

                            if st.form_submit_button("📝 Record Transaction", type="primary"):
                                if tx_item and tx_qty != 0:
                                    new_tx = {
                                        "date": tx_date.strftime("%Y-%m-%d"),
                                        "item": tx_item,
                                        "qty": tx_qty,
                                        "recorded_at": dt.datetime.now().isoformat()
                                    }
                                    customer_data.setdefault("transactions", []).append(new_tx)
                                    if save_customer_data(customer_data):
                                        action = "returned" if tx_qty < 0 else "rented"
                                        st.success(f"✅ Transaction recorded: {abs(tx_qty)} {tx_item} {action}")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to record transaction.")
                                else:
                                    st.error("❌ Please select an item and enter a non-zero quantity.")

                    with info_tabs[3]:  # Payment History
                        st.markdown("##### 💳 Payment History")

                        payment_history = customer_data.get("payment_history", [])
                        if payment_history:
                            payment_display = []
                            for p in sorted(payment_history, key=lambda x: x.get("date", ""), reverse=True):
                                status_icon = {"approved": "✅", "pending": "⏳", "rejected": "❌"}.get(p.get("status"),
                                                                                                     "❓")
                                payment_display.append({
                                    "Date": format_date(p.get("date")),
                                    "Amount": format_currency(safe_float(p.get("amount", 0))),
                                    "Method": p.get("method", "N/A"),
                                    "Reference": p.get("reference", "N/A"),
                                    "Status": f"{status_icon} {p.get('status', 'Unknown').title()}"
                                })
                            st.dataframe(pd.DataFrame(payment_display), use_container_width=True, hide_index=True,
                                         height=300)
                        else:
                            st.info("💳 No payment history found.")

    with admin_tabs[2]:  # Enhanced Payment Approvals
        st.subheader("✅ Payment Approval Center")

        # Get all pending payments
        all_pending = []
        for cust in customers:
            for p in cust.get("payment_history", []):
                if p.get("status") == "pending":
                    all_pending.append({
                        "customer": cust,
                        "payment": p,
                        "customer_balance": calculate_customer_balance(cust)
                    })

        if not all_pending:
            st.success("🎉 No payments awaiting approval!")
            st.info("All payment requests have been processed.")
        else:
            st.warning(f"⏳ {len(all_pending)} payments require your attention")

            # Bulk actions
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Approve All Payments", type="primary", use_container_width=True):
                    approved_count = 0
                    for item in all_pending:
                        payment = item['payment']
                        customer = item['customer']
                        payment['status'] = 'approved'
                        payment['approved_by'] = 'admin'
                        payment['approved_at'] = dt.datetime.now().isoformat()
                        if save_customer_data(customer):
                            approved_count += 1

                    if approved_count > 0:
                        st.success(f"✅ Approved {approved_count} payments successfully!")
                        st.rerun()

            with col2:
                if st.button("❌ Reject All Payments", use_container_width=True):
                    if st.session_state.get('confirm_reject_all', False):
                        rejected_count = 0
                        for item in all_pending:
                            payment = item['payment']
                            customer = item['customer']
                            payment['status'] = 'rejected'
                            payment['rejected_by'] = 'admin'
                            payment['rejected_at'] = dt.datetime.now().isoformat()
                            if save_customer_data(customer):
                                rejected_count += 1

                        if rejected_count > 0:
                            st.warning(f"❌ Rejected {rejected_count} payments")
                            st.rerun()
                        st.session_state.confirm_reject_all = False
                    else:
                        st.session_state.confirm_reject_all = True
                        st.warning("Click again to confirm rejection of all payments")

            st.markdown("---")

            # Individual payment approvals
            for i, item in enumerate(all_pending):
                customer = item['customer']
                payment = item['payment']
                balance = item['customer_balance']

                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 2])

                    with col1:
                        st.markdown(f"**👤 {customer['name']}** (`{customer['customer_id']}`)")
                        st.markdown(f"**💰 Amount:** {format_currency(safe_float(payment['amount']))}")
                        st.markdown(f"**📅 Date:** {format_date(payment['date'])}")

                    with col2:
                        st.markdown(f"**💳 Method:** {payment.get('method', 'N/A')}")
                        if payment.get('reference'):
                            st.markdown(f"**🔖 Ref:** `{payment['reference']}`")
                        st.markdown(f"**⚖️ Current Balance:** {format_currency(balance)}")

                    with col3:
                        # Calculate balance after payment
                        balance_after = balance - safe_float(payment['amount'])
                        if balance_after <= 0:
                            st.success(f"✅ Will clear dues")
                        else:
                            st.info(f"📊 Remaining: {format_currency(balance_after)}")

                        col3a, col3b = st.columns(2)
                        with col3a:
                            if st.button("✅", key=f"approve_{payment['id']}", use_container_width=True, type="primary"):
                                payment['status'] = 'approved'
                                payment['approved_by'] = 'admin'
                                payment['approved_at'] = dt.datetime.now().isoformat()
                                if save_customer_data(customer):
                                    st.success(f"✅ Payment approved for {customer['name']}")
                                    st.rerun()

                        with col3b:
                            if st.button("❌", key=f"reject_{payment['id']}", use_container_width=True):
                                payment['status'] = 'rejected'
                                payment['rejected_by'] = 'admin'
                                payment['rejected_at'] = dt.datetime.now().isoformat()
                                if save_customer_data(customer):
                                    st.warning(f"❌ Payment rejected for {customer['name']}")
                                    st.rerun()

                    # Show notes if any
                    if payment.get('notes'):
                        st.markdown(f"**📝 Notes:** {payment['notes']}")

    with admin_tabs[3]:  # Enhanced Reports
        st.subheader("📈 Business Reports & Analytics")

        report_tabs = st.tabs(["💰 Financial", "👥 Customer Analytics", "📊 Transaction Reports", "📈 Trends"])

        with report_tabs[0]:  # Financial Reports
            st.markdown("#### 💰 Financial Overview")

            # Financial metrics
            total_outstanding = sum(max(0, calculate_customer_balance(c)) for c in customers)
            total_advances = sum(abs(min(0, calculate_customer_balance(c))) for c in customers)
            total_received = sum(
                sum(safe_float(p.get("amount", 0)) for p in c.get("payment_history", []) if
                    p.get("status") == "approved")
                for c in customers
            )

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💰 Total Outstanding", format_currency(total_outstanding))
            with col2:
                st.metric("💎 Total Advances", format_currency(total_advances))
            with col3:
                st.metric("📈 Total Received", format_currency(total_received))
            with col4:
                net_position = total_received - total_outstanding + total_advances
                st.metric("🏦 Net Position", format_currency(net_position))

            # Outstanding balances report
            st.markdown("#### 📋 Outstanding Balances Report")
            outstanding_customers = []
            for c in customers:
                balance = calculate_customer_balance(c)
                if balance > 0:
                    outstanding_customers.append({
                        "Customer": c.get('name'),
                        "ID": c.get('customer_id'),
                        "Mobile": c.get('mobile'),
                        "Outstanding": balance,
                        "Days_Since_Last_Payment": (
                                dt.date.today() -
                                dt.datetime.strptime(
                                    max([p.get('date', '1900-01-01') for p in c.get('payment_history', []) if
                                         p.get('status') == 'approved'], default='1900-01-01'),
                                    '%Y-%m-%d'
                                ).date()
                        ).days if any(p.get('status') == 'approved' for p in c.get('payment_history', [])) else 9999
                    })

            if outstanding_customers:
                outstanding_df = pd.DataFrame(outstanding_customers)
                outstanding_df['Outstanding_Formatted'] = outstanding_df['Outstanding'].apply(format_currency)
                outstanding_df_display = outstanding_df[
                    ['Customer', 'ID', 'Mobile', 'Outstanding_Formatted', 'Days_Since_Last_Payment']].copy()
                outstanding_df_display.columns = ['Customer', 'ID', 'Mobile', 'Outstanding', 'Days Since Last Payment']

                st.dataframe(outstanding_df_display, use_container_width=True, hide_index=True)

                # Export option
                csv_data = outstanding_df_display.to_csv(index=False)
                st.download_button(
                    "📥 Download Outstanding Report (CSV)",
                    csv_data,
                    f"outstanding_report_{dt.date.today().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )
            else:
                st.success("🎉 No outstanding balances! All customers are up to date.")

        with report_tabs[1]:  # Customer Analytics
            st.markdown("#### 👥 Customer Analytics")

            if customers:
                # Customer distribution charts
                col1, col2 = st.columns(2)

                with col1:
                    # Balance distribution
                    balance_categories = {"Dues": 0, "Clear": 0, "Advance": 0}
                    for c in customers:
                        balance = calculate_customer_balance(c)
                        if balance > 0:
                            balance_categories["Dues"] += 1
                        elif balance < 0:
                            balance_categories["Advance"] += 1
                        else:
                            balance_categories["Clear"] += 1

                    fig_balance = px.pie(
                        values=list(balance_categories.values()),
                        names=list(balance_categories.keys()),
                        title="Customer Balance Distribution"
                    )
                    st.plotly_chart(fig_balance, use_container_width=True)

                with col2:
                    # Activity distribution
                    active_customers = sum(1 for c in customers if c.get('transactions'))
                    inactive_customers = len(customers) - active_customers

                    fig_activity = px.pie(
                        values=[active_customers, inactive_customers],
                        names=["Active", "Inactive"],
                        title="Customer Activity Status"
                    )
                    st.plotly_chart(fig_activity, use_container_width=True)

                # Top customers analysis
                st.markdown("#### 🏆 Top Customers Analysis")

                customer_stats = []
                for c in customers:
                    total_paid = sum(safe_float(p.get("amount", 0)) for p in c.get("payment_history", []) if
                                     p.get("status") == "approved")
                    total_transactions = len(c.get("transactions", []))
                    current_balance = calculate_customer_balance(c)

                    customer_stats.append({
                        "Name": c.get('name'),
                        "ID": c.get('customer_id'),
                        "Total_Paid": total_paid,
                        "Transactions": total_transactions,
                        "Current_Balance": current_balance
                    })

                # Top by payments
                top_payers = sorted(customer_stats, key=lambda x: x['Total_Paid'], reverse=True)[:10]
                if top_payers:
                    st.markdown("##### 💰 Top 10 Customers by Total Payments")
                    top_payers_df = pd.DataFrame(top_payers)
                    top_payers_df['Total_Paid_Formatted'] = top_payers_df['Total_Paid'].apply(format_currency)
                    st.dataframe(
                        top_payers_df[['Name', 'ID', 'Total_Paid_Formatted', 'Transactions']].rename(columns={
                            'Total_Paid_Formatted': 'Total Paid',
                            'Transactions': 'Total Transactions'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )

        with report_tabs[2]:  # Transaction Reports
            st.markdown("#### 📊 Transaction Analysis")

            # Collect all transactions
            all_transactions = []
            for c in customers:
                for tx in c.get("transactions", []):
                    all_transactions.append({
                        "Customer": c.get('name'),
                        "Customer_ID": c.get('customer_id'),
                        "Date": tx.get('date'),
                        "Item": tx.get('item'),
                        "Quantity": safe_float(tx.get('qty', 0)),
                        "Action": "Rent" if safe_float(tx.get('qty', 0)) > 0 else "Return"
                    })

            if all_transactions:
                transactions_df = pd.DataFrame(all_transactions)
                transactions_df['Date'] = pd.to_datetime(transactions_df['Date'])

                # Transaction volume over time
                st.markdown("##### 📈 Transaction Volume Trend")
                daily_transactions = transactions_df.groupby(transactions_df['Date'].dt.date).size().reset_index(
                    name='Count')
                daily_transactions['Date'] = pd.to_datetime(daily_transactions['Date'])

                fig_volume = px.line(daily_transactions, x='Date', y='Count', title='Daily Transaction Volume')
                st.plotly_chart(fig_volume, use_container_width=True)

                # Most popular items
                st.markdown("##### 🏗️ Most Popular Items")
                item_activity = transactions_df.groupby('Item').agg({
                    'Quantity': ['sum', 'count']
                }).round(2)
                item_activity.columns = ['Total_Quantity', 'Transaction_Count']
                item_activity = item_activity.reset_index().sort_values('Transaction_Count', ascending=False)

                if not item_activity.empty:
                    st.dataframe(
                        item_activity.rename(columns={
                            'Item': 'Item Name',
                            'Total_Quantity': 'Net Quantity',
                            'Transaction_Count': 'Total Transactions'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )

                # Recent activity
                st.markdown("##### 🕒 Recent Transaction Activity")
                recent_transactions = transactions_df.sort_values('Date', ascending=False).head(20)
                recent_display = recent_transactions.copy()
                recent_display['Date'] = recent_display['Date'].dt.strftime('%Y-%m-%d')
                recent_display['Quantity'] = recent_display['Quantity'].abs().astype(int)

                st.dataframe(
                    recent_display[['Date', 'Customer', 'Item', 'Action', 'Quantity']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("📋 No transaction data available for analysis.")

        with report_tabs[3]:  # Trends
            st.markdown("#### 📈 Business Trends")

            # Payment trends
            all_payments = []
            for c in customers:
                for p in c.get("payment_history", []):
                    if p.get("status") == "approved":
                        all_payments.append({
                            "Date": p.get('date'),
                            "Amount": safe_float(p.get('amount', 0)),
                            "Method": p.get('method', 'Unknown')
                        })

            if all_payments:
                payments_df = pd.DataFrame(all_payments)
                payments_df['Date'] = pd.to_datetime(payments_df['Date'])

                # Monthly revenue trend
                st.markdown("##### 💰 Monthly Revenue Trend")
                monthly_revenue = payments_df.groupby(payments_df['Date'].dt.to_period('M'))[
                    'Amount'].sum().reset_index()
                monthly_revenue['Date'] = monthly_revenue['Date'].astype(str)

                fig_revenue = px.bar(monthly_revenue, x='Date', y='Amount', title='Monthly Revenue')
                fig_revenue.update_layout(xaxis_title="Month", yaxis_title="Revenue (₹)")
                st.plotly_chart(fig_revenue, use_container_width=True)

                # Payment method trends
                st.markdown("##### 💳 Payment Method Preferences")
                method_trends = payments_df['Method'].value_counts().reset_index()
                method_trends.columns = ['Method', 'Count']

                fig_methods = px.bar(method_trends, x='Method', y='Count', title='Payment Methods Usage')
                st.plotly_chart(fig_methods, use_container_width=True)

                # Growth metrics
                if len(monthly_revenue) > 1:
                    current_month = monthly_revenue.iloc[-1]['Amount']
                    previous_month = monthly_revenue.iloc[-2]['Amount'] if len(monthly_revenue) > 1 else 0
                    growth_rate = ((current_month - previous_month) / previous_month * 100) if previous_month > 0 else 0

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("This Month", format_currency(current_month))
                    with col2:
                        st.metric("Last Month", format_currency(previous_month))
                    with col3:
                        st.metric("Growth Rate", f"{growth_rate:.1f}%", delta=f"{growth_rate:.1f}%")
            else:
                st.info("📊 No payment data available for trend analysis.")

    with admin_tabs[4]:  # Enhanced Settings
        st.subheader("⚙️ System Configuration")

        settings_tabs = st.tabs(["🏢 Company Info", "🔐 Security", "🎨 Appearance", "📊 Business Rules"])

        with settings_tabs[0]:  # Company Info
            st.markdown("#### 🏢 Company Information")
            with st.form("enhanced_company_settings"):
                settings = load_company_settings()

                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Company Name*", settings.get("name"))
                    tagline = st.text_input("Tagline", settings.get("tagline"))
                    mobile = st.text_input("Mobile Number*", settings.get("mobile"))
                    email = st.text_input("Email Address", settings.get("email"))
                    website = st.text_input("Website", settings.get("website"))

                with col2:
                    address = st.text_area("Address*", settings.get("address"), height=100)
                    business_hours = st.text_input("Business Hours", settings.get("business_hours"))
                    established_year = st.text_input("Established Year", settings.get("established_year"))
                    upi_id = st.text_input("UPI ID for Payments", settings.get("upi_id"))
                    logo_url = st.text_input("Logo URL", settings.get("logo_url"))

                if st.form_submit_button("💾 Save Company Information", type="primary", use_container_width=True):
                    updated_settings = {
                        "name": name, "tagline": tagline, "mobile": mobile, "email": email,
                        "website": website, "address": address, "business_hours": business_hours,
                        "established_year": established_year, "upi_id": upi_id, "logo_url": logo_url,
                        "currency_symbol": settings.get("currency_symbol"),
                        "date_format": settings.get("date_format"),
                        "admin_password_hash": settings.get("admin_password_hash")
                    }

                    if save_company_settings(updated_settings):
                        st.success("✅ Company information updated successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to save company information.")

        with settings_tabs[1]:  # Security
            st.markdown("#### 🔐 Security Settings")

            with st.form("security_settings"):
                st.markdown("##### Change Admin Password")
                current_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm New Password", type="password")

                if st.form_submit_button("🔒 Update Password", type="primary"):
                    settings = load_company_settings()

                    if not current_password:
                        st.error("❌ Current password is required.")
                    elif hash_password(current_password) != settings.get("admin_password_hash"):
                        st.error("❌ Current password is incorrect.")
                    elif len(new_password) < 6:
                        st.error("❌ New password must be at least 6 characters long.")
                    elif new_password != confirm_password:
                        st.error("❌ New passwords do not match.")
                    else:
                        settings["admin_password_hash"] = hash_password(new_password)
                        if save_company_settings(settings):
                            st.success("✅ Password updated successfully!")
                        else:
                            st.error("❌ Failed to update password.")

        with settings_tabs[2]:  # Appearance
            st.markdown("#### 🎨 Display Settings")

            with st.form("appearance_settings"):
                settings = load_company_settings()

                currency_symbol = st.text_input("Currency Symbol", settings.get("currency_symbol", "₹"))
                date_format_options = {
                    "%d-%b-%Y": "31-Dec-2024",
                    "%d/%m/%Y": "31/12/2024",
                    "%Y-%m-%d": "2024-12-31",
                    "%d %B %Y": "31 December 2024"
                }

                current_format = settings.get("date_format", "%d-%b-%Y")
                format_display = {v: k for k, v in date_format_options.items()}

                selected_format_display = st.selectbox(
                    "Date Format",
                    list(date_format_options.values()),
                    index=list(date_format_options.keys()).index(
                        current_format) if current_format in date_format_options else 0
                )
                date_format = format_display[selected_format_display]

                if st.form_submit_button("🎨 Save Appearance Settings", type="primary"):
                    settings["currency_symbol"] = currency_symbol
                    settings["date_format"] = date_format

                    if save_company_settings(settings):
                        st.success("✅ Appearance settings updated!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to save settings.")

        with settings_tabs[3]:  # Business Rules
            st.markdown("#### 📊 Business Configuration")
            st.info("🚧 Advanced business rules and automation settings will be available in future updates.")

            # Placeholder for future features
            st.markdown("""
            **Planned Features:**
            - Automatic late payment reminders
            - Bulk pricing rules
            - Payment terms configuration
            - Custom report templates
            - Automated backup settings
            """)

    with admin_tabs[5]:  # Enhanced System
        st.subheader("🔧 System Management")

        system_tabs = st.tabs(["🧹 Maintenance", "📊 System Stats", "🔄 Data Management", "🆘 Support"])

        with system_tabs[0]:  # Maintenance
            st.markdown("#### 🧹 System Maintenance")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("##### Session Management")
                if st.button("🧹 Clean Expired Sessions", use_container_width=True):
                    with st.spinner("Cleaning up expired sessions..."):
                        count = cleanup_expired_sessions()
                        st.success(f"✅ Cleaned up {count} expired sessions.")

                st.markdown("##### Cache Management")
                if st.button("🔄 Clear Application Cache", use_container_width=True):
                    # Clear Streamlit cache
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    st.success("✅ Application cache cleared.")

            with col2:
                st.markdown("##### Data Validation")
                if st.button("🔍 Validate Customer Data", use_container_width=True):
                    with st.spinner("Validating customer data..."):
                        issues = []
                        customers = get_all_customers()

                        for c in customers:
                            # Check required fields
                            if not all(c.get(field) for field in ['customer_id', 'name', 'mobile']):
                                issues.append(f"Missing required fields: {c.get('customer_id', 'Unknown')}")

                            # Check mobile format
                            mobile = c.get('mobile', '')
                            if mobile and (len(mobile) != 10 or not mobile.isdigit()):
                                issues.append(f"Invalid mobile format: {c.get('name', 'Unknown')} - {mobile}")

                            # Check transaction data integrity
                            for tx in c.get('transactions', []):
                                try:
                                    dt.datetime.strptime(tx.get('date', ''), '%Y-%m-%d')
                                except ValueError:
                                    issues.append(f"Invalid date in transaction: {c.get('name', 'Unknown')}")

                        if issues:
                            st.warning(f"⚠️ Found {len(issues)} data issues:")
                            for issue in issues[:10]:  # Show first 10
                                st.write(f"• {issue}")
                            if len(issues) > 10:
                                st.write(f"... and {len(issues) - 10} more issues")
                        else:
                            st.success("✅ All customer data is valid!")

        with system_tabs[1]:  # System Stats
            st.markdown("#### 📊 System Statistics")

            # File system stats
            import os

            data_dir_size = sum(os.path.getsize(os.path.join("data", f)) for f in os.listdir("data") if
                                f.endswith('.json')) if os.path.exists("data") else 0
            session_count = len([f for f in os.listdir("sessions") if f.endswith('.json')]) if os.path.exists(
                "sessions") else 0

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📁 Data Size", f"{data_dir_size / 1024:.1f} KB")
            with col2:
                st.metric("🔐 Active Sessions", session_count)
            with col3:
                st.metric("👥 Total Customers", len(customers))
            with col4:
                total_transactions = sum(len(c.get('transactions', [])) for c in customers)
                st.metric("📋 Total Transactions", total_transactions)

            # System health
            st.markdown("##### 💚 System Health")
            health_checks = [
                ("Data Directory", os.path.exists("data")),
                ("Settings File", os.path.exists("settings/config.json")),
                ("Session Directory", os.path.exists("sessions")),
                ("Logs Directory", os.path.exists("logs")),
            ]

            for check, status in health_checks:
                status_icon = "✅" if status else "❌"
                st.write(f"{status_icon} {check}")

        with system_tabs[2]:  # Data Management
            st.markdown("#### 🔄 Data Management")

            st.markdown("##### 📤 Export Data")
            col1, col2 = st.columns(2)

            with col1:
                if st.button("📥 Export All Customer Data (JSON)", use_container_width=True):
                    try:
                        export_data = {
                            "export_date": dt.datetime.now().isoformat(),
                            "total_customers": len(customers),
                            "customers": customers
                        }

                        json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
                        st.download_button(
                            "📥 Download Customer Data",
                            json_str,
                            f"customer_data_export_{dt.date.today().strftime('%Y%m%d')}.json",
                            "application/json",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Export failed: {str(e)}")

            with col2:
                if st.button("📊 Export Financial Summary (CSV)", use_container_width=True):
                    try:
                        financial_data = []
                        for c in customers:
                            balance = calculate_customer_balance(c)
                            total_paid = sum(safe_float(p.get("amount", 0)) for p in c.get("payment_history", []) if
                                             p.get("status") == "approved")

                            financial_data.append({
                                "Customer_ID": c.get('customer_id'),
                                "Name": c.get('name'),
                                "Mobile": c.get('mobile'),
                                "Current_Balance": balance,
                                "Total_Paid": total_paid,
                                "Previous_Balance": safe_float(c.get('previous_balance', 0)),
                                "Status": "Dues" if balance > 0 else ("Advance" if balance < 0 else "Clear")
                            })

                        df = pd.DataFrame(financial_data)
                        csv_str = df.to_csv(index=False)
                        st.download_button(
                            "📥 Download Financial Summary",
                            csv_str,
                            f"financial_summary_{dt.date.today().strftime('%Y%m%d')}.csv",
                            "text/csv",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Export failed: {str(e)}")

            st.markdown("##### ⚠️ Danger Zone")
            with st.expander("🚨 Advanced Data Operations", expanded=False):
                st.warning("⚠️ These operations are irreversible. Use with extreme caution!")

                if st.button("🗑️ Clear All Session Data", type="secondary"):
                    if st.session_state.get('confirm_clear_sessions', False):
                        try:
                            if os.path.exists("sessions"):
                                for f in os.listdir("sessions"):
                                    if f.endswith('.json'):
                                        os.remove(os.path.join("sessions", f))
                            st.success("✅ All session data cleared.")
                            st.session_state.confirm_clear_sessions = False
                        except Exception as e:
                            st.error(f"Error clearing sessions: {str(e)}")
                    else:
                        st.session_state.confirm_clear_sessions = True
                        st.warning("Click again to confirm clearing all sessions.")

        with system_tabs[3]:  # Support 
            st.markdown("#### 🆘 Support Information")

            st.markdown(f"""
            **📋 System Information:**
            - Application Version: 2.0.0 Enhanced
            - Python Version: 3.8+
            - Streamlit Version: Latest
            - Last Updated: {dt.date.today().strftime('%B %Y')}

            **🔧 Technical Support:**
            - For technical issues, please contact your system administrator
            - Check logs directory for detailed error information
            - Ensure all required directories have proper permissions

            **📚 User Guide:**
            - Customer Portal: Login → View balance, history, make payments
            - Admin Panel: Manage customers, approve payments, generate reports
            - System maintains automatic backups of all data

            **🚨 Emergency Procedures:**
            - In case of data corruption, check the data directory
            - Sessions can be safely cleared without data loss
            - Settings can be reset to defaults if needed
            """)
    if st.button("🚪 Logout", use_container_width=True, type="secondary", key=4641):
            if st.session_state.session_id and delete_session(st.session_state.session_id):
                st.session_state.session_id = None
                st.session_state.user_type = None
                st.session_state.user_data = None
                st.success("Logged out successfully!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Error logging out.")

else:
    # Enhanced Landing Page
    st.markdown('<div ', unsafe_allow_html=True)
    display_hero_section()
    st.markdown('</div>', unsafe_allow_html=True)

    # Welcome message with login prompt
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("---")

    if not st.session_state.session_id:
        
        st.title("🔐 Login")
        login_type = 'Customer'

        if login_type == "Customer":
            st.subheader("Customer Login")
            with st.form("customer_login_form"):
                identifier = st.text_input("Mobile Number or Customer ID",
                                           placeholder="E.g., 9876543210 or CUST-001").strip()
                if identifier != '123654':
                    hide_st_style = """
                    <style>
                    MainMenu {visibility: hidden;}
                    headerNoPadding {visibility: hidden;}
                    _terminalButton_rix23_138 {visibility: hidden;}
                    header {visibility: hidden;}
                    </style>
                    """
                    st.markdown(hide_st_style, unsafe_allow_html=True)
                login_button = st.form_submit_button("🚀 Login", use_container_width=True, type="primary")

            if login_button:
                if identifier == '123654':
                    st.success("1 Step away from admin login🤫🫠!")
                elif not identifier:
                    st.error("Please enter your mobile number or customer ID.")
                else:
                    with st.spinner("Authenticating..."):
                        customer_data = authenticate_customer(identifier)
                        if customer_data:
                            session_id = create_session(customer_data["customer_id"], "customer", customer_data)
                            if session_id:
                                st.session_state.session_id = session_id
                                st.session_state.user_type = "customer"
                                st.session_state.user_data = customer_data
                                st.success("Login successful!")
                                st.balloons()
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Failed to create session.")
                        else:
                            st.error("Invalid credentials. Please check your mobile number or customer ID.")

       
    # Display features
    display_features_section()

    st.markdown("---")
    st.markdown("### 🎯 How It Works")

    # Define colors for each card (you can customize these)
    colors = {
        "background": ["#FFEEEE", "#EEFFEE", "#EEEEFF", "#FFF5EE"],
        "border": ["#FF6B6B", "#4CAF50", "#4285F4", "#FFA726"],
        "text": ["#D32F2F", "#2E7D32", "#1565C0", "#E65100"]
    }

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div style="
            background-color: {colors['background'][0]};
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid {colors['border'][0]};
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            margin: 10px 0;
            transition: transform 0.2s;
        ">
            <h4 style="color: {colors['text'][0]}; margin-top: 0;">1️⃣ Register or login</h4>
            <p style="color: #555555;">Get your customer account set up with our team</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="
            background-color: {colors['background'][1]};
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid {colors['border'][1]};
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            margin: 10px 0;
        ">
            <h4 style="color: {colors['text'][1]}; margin-top: 0;">2️⃣ Rent Equipment</h4>
            <p style="color: #555555;">Choose from our wide range of quality shuttering materials</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="
            background-color: {colors['background'][2]};
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid {colors['border'][2]};
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            margin: 10px 0;
        ">
            <h4 style="color: {colors['text'][2]}; margin-top: 0;">3️⃣ Track Usage</h4>
            <p style="color: #555555;">Monitor your rentals and payments through our digital portal</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div style="
            background-color: {colors['background'][3]};
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid {colors['border'][3]};
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            margin: 10px 0;
        ">
            <h4 style="color: {colors['text'][3]}; margin-top: 0;">4️⃣ Easy Payments</h4>
            <p style="color: #555555;">Pay online via UPI, bank transfer, or traditional methods</p>
        </div>
        """, unsafe_allow_html=True)
    # Call to action
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px;">
            <h3>Ready to Get Started?</h3>
            <p style="margin-bottom: 1.5rem;">Join hundreds of satisfied customers who trust us with their construction needs.</p>
            <p><strong>📞 Call us at {}</strong></p>
            <p>or use the sidebar to access your existing account</p>
        </div>
        """.format(company.get('mobile', 'Contact Admin')), unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; padding: 1rem; color: #7F8C8D; font-size: 0.9em;">
    <p>© {dt.date.today().year} {company.get('name', 'Rental Management System')} | 
    created by Sahil Jammu | Beta Version 1.0.0 </p>
    <p>🏗️ Professional Rental Management Solutions</p>
</div>
""", unsafe_allow_html=True)
