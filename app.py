# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import io # Required for reading string data as file
import google.generativeai as genai
import yaml
from datetime import datetime, timedelta
# from config import GOOGLE_API_KEY # <<< REMOVED IMPORT
import re
import json
import sys # Required for checking xlsxwriter
import numpy as np # Needed for date calculations

# ------------------------------------------------------------------------------
# Page Configuration (Set Title and Icon)
st.set_page_config(page_title="AI Schedule Manager", page_icon="📅", layout="wide")

# Check for xlsxwriter (optional but good for Excel export)
try:
    import xlsxwriter
except ImportError:
    st.warning("Module 'xlsxwriter' is recommended for Excel export. Install using: pip install xlsxwriter")

# --- UPDATED: Check and configure Google API Key using Streamlit Secrets ---
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    st.error("Lỗi: Google API Key chưa được cấu hình trong Streamlit Secrets!")
    st.info("Vui lòng thêm GOOGLE_API_KEY vào mục Secrets trong cài đặt ứng dụng của bạn trên Streamlit Community Cloud.")
    st.stop() # Stop execution if no API key

# Configure Google Generative AI
try:
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
     st.error(f"Lỗi cấu hình Google API: {e}"); st.stop()

# Generation config for Google Generative AI
generation_config = { "temperature": 0.7, "top_p": 1, "top_k": 1, "max_output_tokens": 4096 }

# Initialize the Generative Model
try:
    model = genai.GenerativeModel(model_name="gemini-1.5-pro", generation_config=generation_config)
except Exception as e:
    st.error(f"Lỗi khởi tạo mô hình AI: {e}"); st.error("Kiểm tra API Key và kết nối mạng."); st.stop()

# --- Define Predefined Column Names ---
PREDEFINED_COLUMNS = [
    "Tên nhân viên:",
    "Đăng kí ca cho tuần:",
    "bạn có thể làm việc thời gian nào? [Thứ 2]",
    "bạn có thể làm việc thời gian nào? [Thứ 3]",
    "bạn có thể làm việc thời gian nào? [Thứ 4]",
    "bạn có thể làm việc thời gian nào? [Thứ 5]",
    "bạn có thể làm việc thời gian nào? [Thứ 6]",
    "bạn có thể làm việc thời gian nào? [Thứ 7]",
    "bạn có thể làm việc thời gian nào? [Chủ nhật]",
    "Ghi chú (nếu có)"
]

# --- Custom CSS for Styling (Keep as is) ---
def load_css():
    """Loads custom CSS styles."""
    # CSS content kept the same as previous version
    st.markdown("""
        <style>
            /* General Body and Font */
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            /* Main Container */
            .main .block-container { padding-top: 2rem; padding-bottom: 5rem; padding-left: 2rem; padding-right: 2rem; } /* Reduced padding */
            /* Titles */
            h1, h2 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px; margin-bottom: 20px;}
            h3 { color: #34495e; margin-top: 25px; margin-bottom: 15px; }
            body:has([data-theme="dark"]) h1, body:has([data-theme="dark"]) h2, body:has([data-theme="dark"]) h3 { color: #ecf0f1; border-bottom-color: #5dade2;}
            body:has([data-theme="dark"]) h3 { color: #bdc3c7;}

            /* Buttons */
            .stButton>button { border-radius: 8px; padding: 10px 15px; font-weight: 600; border: none; color: white; background-color: #3498db; transition: background-color 0.3s ease; margin-top: 5px; margin-bottom: 5px;} /* Slightly less padding */
            .stButton>button:hover { background-color: #2980b9; }
            .stButton>button:active { background-color: #2471a3; }
            .stButton[key*="generate_ai_button"]>button { background-color: #2ecc71; }
            .stButton[key*="generate_ai_button"]>button:hover { background-color: #27ae60; }
            /* Button for copy text */
             .stButton[key*="generate_copy_text_button"]>button { background-color: #9b59b6; /* Purple */ }
             .stButton[key*="generate_copy_text_button"]>button:hover { background-color: #8e44ad; /* Darker Purple */ }


            /* Text Area */
            .stTextArea textarea { border-radius: 8px; border: 1px solid #bdc3c7; padding: 10px; min-height: 150px; font-family: monospace; /* Use monospace for better alignment */}
            body:has([data-theme="dark"]) .stTextArea textarea { border: 1px solid #566573; }
            .stTextArea label { font-weight: 600; color: #34495e; margin-bottom: 5px; display: block;}
            body:has([data-theme="dark"]) .stTextArea label { color: #bdc3c7; }

            /* DataFrames / Data Editor / Manual Table */
            .stDataFrame, .stDataEditor, .manual-table-header, .manual-table-row { border-radius: 8px; overflow: visible; margin-bottom: 10px;} /* Reduced margin */
            .manual-table-header > div { font-weight: bold; background-color: #eaf2f8; padding: 8px 6px; text-align: center; border: 1px solid #d6eaf8; font-size: 0.9rem;} /* Smaller padding/font */
            body:has([data-theme="dark"]) .manual-table-header > div { background-color: #34495e; border: 1px solid #4e6070; }
            .manual-table-row > div { padding: 4px 6px; border: 1px solid #e8ecf1; min-height: 55px; display: flex; align-items: center; justify-content: center;} /* Reduced padding */
            body:has([data-theme="dark"]) .manual-table-row > div { border: 1px solid #4a4f5a; }
            /* Alternating row colors for manual table */
            .manual-table-row:nth-child(even) > div { background-color: #f8f9fa; }
            body:has([data-theme="dark"]) .manual-table-row:nth-child(even) > div { background-color: #2c3e50; }


            /* Selectbox in manual table */
            .manual-table-row .stSelectbox { width: 100%; overflow: visible !important; }
            .manual-table-row .stSelectbox div[data-baseweb="select"] { font-size: 0.85rem; width: 100%; background-color: var(--background-color); }
            .manual-table-row .stSelectbox div[data-baseweb="select"] > div:first-child { color: var(--text-color) !important; overflow: visible !important; }
            .manual-table-row .stSelectbox div[data-baseweb="select"] > div:first-child > div { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; max-width: none !important; }


            /* Sidebar */
             .stSidebar .stNumberInput input, .stSidebar .stSlider, .stSidebar .stCheckbox { margin-bottom: 10px; }
             .stSidebar h3 { color: #3498db; margin-top: 15px;}
             body:has([data-theme="dark"]) .stSidebar h3 { color: #5dade2; }
             .stSidebar .stMarkdown p { font-size: 0.95rem; line-height: 1.4;}
             .stSidebar .stDivider { margin-top: 15px; margin-bottom: 15px;}

            /* --- UPDATED: Footer style for sidebar --- */
            .footer-copyright {
                /* position: fixed; right: 15px; bottom: 10px; /* REMOVED fixed positioning */
                color: #7f8c8d; /* Lighter gray color */
                font-size: 12px; /* Smaller font */
                text-align: center; /* Center align in sidebar */
                padding-top: 20px; /* Add some space above */
                /* z-index: 9999; /* Not needed without fixed */
            }
             body:has([data-theme="dark"]) .footer-copyright {
                  color: #95a5a6; /* Adjust color for dark theme */
             }

            /* Login Box Specific Styles */
            .login-box { margin: 50px auto 0 auto; max-width: 380px; background-color: rgba(255, 255, 255, 0.9); backdrop-filter: blur(5px); padding: 35px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.15); text-align: center; }
            .login-title { font-size: 24px; font-weight: 600; color: #31333F; margin-bottom: 25px; border-bottom: none; }
            .login-box .stTextInput>div>div>input { padding: 12px; border: 1px solid #ccc; border-radius: 5px; width: 100%; margin-bottom: 15px;}
            .login-box .stButton>button { width: 100%; height: 48px; background-color: #31333F; color: #FFFFFF; border: none; border-radius: 5px; font-size: 16px; font-weight: 600; cursor: pointer; margin-top: 15px; }
            .login-box .stButton>button:hover { background-color: #50525C; }
            .login-page-background { background: linear-gradient(to right, #74ebd5, #ACB6E5); min-height: 100vh; width: 100%; display: flex; align-items: center; justify-content: center; position: absolute; top: 0; left: 0; z-index: -1; }

            /* Container styling */
            div[data-testid="stVerticalBlock"]:has(> div > div > div.stContainer) { }
             body:has([data-theme="dark"]) div[data-testid="stVerticalBlock"]:has(> div > div > div.stContainer) { }

        </style>
    """, unsafe_allow_html=True)


# --- Credential Loading and Login Logic ---
def load_credentials():
    """Loads credentials from Streamlit secrets or local file."""
    credentials_dict = st.secrets.get("credentials", {})
    if not credentials_dict:
         st.warning("Không tìm thấy credentials trong Secrets. Thử đọc file credentials.yaml...")
         try:
             with open('credentials.yaml') as file:
                 credentials_dict = yaml.safe_load(file) or {}
         except FileNotFoundError: st.error("File credentials.yaml không tồn tại."); return {}
         except yaml.YAMLError as e: st.error(f"Lỗi đọc credentials.yaml: {e}"); return {}
    return credentials_dict

def login():
    """Handles the login interface and logic."""
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    st.markdown('<div class="login-page-background"></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<h2 class='login-title'>AI Schedule Manager</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: #566573; margin-top: -15px; margin-bottom: 30px;'>Vui lòng đăng nhập</p>", unsafe_allow_html=True)
        credentials = load_credentials();
        if not credentials: st.markdown("</div>", unsafe_allow_html=True); return False
        username = st.text_input("Tên đăng nhập", key="login_user").strip()
        password = st.text_input("Mật khẩu", type="password", key="login_pass")
        if st.button("Đăng nhập", key="login_button_main", use_container_width=True):
            if username in credentials and credentials[username] == password:
                st.session_state.logged_in = True; st.success("Đăng nhập thành công!"); st.rerun()
            else: st.error("Tên đăng nhập hoặc mật khẩu không đúng.")
        st.markdown("</div>", unsafe_allow_html=True)
    return st.session_state.logged_in


# --- Scheduling Requirements Input ---
def get_scheduling_requirements():
    """Gets scheduling constraints from the sidebar."""
    st.sidebar.header("⚙️ Điều Kiện Lập Lịch")
    st.sidebar.divider()
    requirements = {
        "shifts_definition": {"Ca 1": {"start": "09:00", "end": "15:00"}, "Ca 2": {"start": "14:00", "end": "20:00"}},
        "max_shifts_per_day": 1,
        "shifts_per_week_target": 4,
        "min_rest_hours": st.sidebar.number_input("Giờ nghỉ tối thiểu (>1 ca/ngày)", min_value=1, value=8, step=1),
        "max_consecutive_days": st.sidebar.number_input("Ngày làm liên tiếp tối đa", min_value=1, max_value=7, value=6, step=1),
        "preferences_weight_hint": st.sidebar.slider("Ưu tiên nguyện vọng ghi chú", 0.0, 1.0, 0.7, 0.1)
    }
    st.sidebar.divider(); st.sidebar.markdown("**ℹ️ Quy tắc:**")
    st.sidebar.markdown(f"- **Ca 1:** {requirements['shifts_definition']['Ca 1']['start']} - {requirements['shifts_definition']['Ca 1']['end']}")
    st.sidebar.markdown(f"- **Ca 2:** {requirements['shifts_definition']['Ca 2']['start']} - {requirements['shifts_definition']['Ca 2']['end']}")
    st.sidebar.markdown(f"- **Số người/ca:** **2** (ngày thường), **3** (ngày trùng tháng VD: 3/3, 5/5...)")
    st.sidebar.markdown(f"- **Tối đa:** **{requirements['max_shifts_per_day']}** ca/người/ngày")
    st.sidebar.markdown(f"- **Tổng số ca/tuần:** **{requirements['shifts_per_week_target']}** ca/người")
    st.sidebar.divider()
    if not requirements["min_rest_hours"] > 0 or not requirements["max_consecutive_days"] > 0:
        st.sidebar.error("Giờ nghỉ và ngày làm liên tiếp phải lớn hơn 0."); return None
    return requirements


# --- Helper Function to Find Start Date (Keep updated date parsing) ---
def find_start_date(df_input):
    """Finds the start date (Monday) from the input DataFrame."""
    week_start_col = next((col for col in df_input.columns if 'tuần' in col.lower() or 'week' in col.lower()), None)
    start_date = None
    if week_start_col and not df_input[week_start_col].empty:
        date_val_str = str(df_input[week_start_col].dropna().iloc[0]) # Get value as string
        try:
            start_date = pd.to_datetime(date_val_str, dayfirst=True, errors='coerce') # Try DD/MM/YYYY first
            if pd.isna(start_date): start_date = pd.to_datetime(date_val_str, errors='coerce')
            if pd.notna(start_date): start_date = start_date - timedelta(days=start_date.weekday())
        except Exception as e:
             st.warning(f"Lỗi phân tích ngày tháng từ cột '{week_start_col}': {e}. Giá trị: '{date_val_str}'"); pass
    return start_date

# --- RE-ADD: Preprocess Pasted Data for Availability Lookup ---
def preprocess_pasted_data_for_lookup(df_input):
    """Processes the raw pasted DataFrame to create a structured availability lookup table."""
    st.info("⚙️ Đang xử lý dữ liệu đăng ký gốc để tra cứu...")
    processed_rows = []
    start_date = find_start_date(df_input)
    if start_date is None:
        st.warning("⚠️ Không xác định được ngày bắt đầu tuần. Chức năng tìm thay thế sẽ không hoạt động.")
        return pd.DataFrame(columns=['Date', 'Employee', 'Shift', 'Can_Work', 'Note']) # Return empty DF

    employee_col = next((col for col in df_input.columns if 'tên' in col.lower()), None)
    note_col = next((col for col in df_input.columns if 'ghi chú' in col.lower()), None)
    day_mapping = {}; day_keywords_map = {
        0: ['thứ 2', 'mon'], 1: ['thứ 3', 'tue'], 2: ['thứ 4', 'wed'], 3: ['thứ 5', 'thu'],
        4: ['thứ 6', 'fri'], 5: ['thứ 7', 'sat'], 6: ['chủ nhật', 'sun']
    }
    found_day_cols = False
    for day_index, keywords in day_keywords_map.items():
        for col in df_input.columns:
            # --- More specific check for day columns ---
            col_lower = str(col).lower()
            if any(f'[{keyword}]' in col_lower for keyword in keywords) or any(f' {keyword}' in col_lower for keyword in keywords):
                 day_mapping[day_index] = col; found_day_cols = True; break
    if not found_day_cols: st.error("❌ Không tìm thấy các cột ngày (VD: '... [Thứ 2]')."); return None
    if not employee_col: st.error("❌ Không tìm thấy cột tên nhân viên."); return None

    for index, row in df_input.iterrows():
        employee = row.get(employee_col); note = row.get(note_col, '') if note_col else ''
        if not employee or pd.isna(employee): continue
        for day_index, day_col in day_mapping.items():
            current_date = start_date + timedelta(days=day_index)
            availability_text = str(row.get(day_col, '')).lower()
            can_do_ca1 = False; can_do_ca2 = False
            if 'nghỉ' in availability_text or 'off' in availability_text: pass # Both remain False
            else:
                if 'ca 1' in availability_text or 'sáng' in availability_text or '9h' in availability_text: can_do_ca1 = True
                if 'ca 2' in availability_text or 'chiều' in availability_text or '14h' in availability_text: can_do_ca2 = True
                # If text exists but doesn't specify shift, assume both possible unless explicitly 'nghi'
                if not can_do_ca1 and not can_do_ca2 and availability_text.strip() != '':
                     can_do_ca1 = True; can_do_ca2 = True
            processed_rows.append({'Date': current_date.date(), 'Employee': employee.strip(), 'Shift': 'Ca 1', 'Can_Work': can_do_ca1, 'Note': note})
            processed_rows.append({'Date': current_date.date(), 'Employee': employee.strip(), 'Shift': 'Ca 2', 'Can_Work': can_do_ca2, 'Note': note})
    if not processed_rows: st.warning("⚠️ Không có dữ liệu đăng ký hợp lệ."); return pd.DataFrame(columns=['Date', 'Employee', 'Shift', 'Can_Work', 'Note'])
    lookup_df = pd.DataFrame(processed_rows)
    lookup_df['Date'] = pd.to_datetime(lookup_df['Date']).dt.date # Ensure Date is date object
    st.success("✅ Đã xử lý xong dữ liệu đăng ký gốc."); return lookup_df


# --- AI Schedule Generation Function (Keep dynamic staffing logic and 4 shifts/week rule) ---
def generate_schedule_with_ai(df_input, requirements, model):
    """Constructs a prompt and calls the AI model to generate the schedule."""
    # This function remains the same as the previous version (v10)
    st.info(" Chuẩn bị dữ liệu và tạo prompt cho AI...")
    data_prompt_list = []; data_prompt_list.append("Dữ liệu đăng ký của nhân viên:")
    employee_col = next((col for col in df_input.columns if 'tên' in col.lower()), None)
    note_col = next((col for col in df_input.columns if 'ghi chú' in col.lower()), None)
    day_keywords = ['thứ 2', 'thứ 3', 'thứ 4', 'thứ 5', 'thứ 6', 'thứ 7', 'chủ nhật', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    day_cols = [col for col in df_input.columns if any(keyword in str(col).lower() for keyword in day_keywords)]
    start_date = find_start_date(df_input); start_date_str_for_prompt = start_date.strftime('%Y-%m-%d') if start_date else "Không xác định"
    if not employee_col: st.error("Lỗi: Không thể xác định cột 'Tên nhân viên'."); return None
    if not day_cols: st.warning("Không tìm thấy cột ngày (Thứ 2-CN).")
    if start_date is None: st.warning("Không xác định được ngày bắt đầu tuần.")

    data_prompt_list.append(f"(Dữ liệu cho tuần bắt đầu Thứ 2 khoảng: {start_date_str_for_prompt})")
    for index, row in df_input.iterrows(): # Format data for prompt
        emp_name = row[employee_col]; data_prompt_list.append(f"Nhân viên: {emp_name}")
        availability_info = []
        if day_cols:
            for day_col in day_cols:
                 cell_value = row.get(day_col)
                 if pd.notna(cell_value): availability_info.append(f"- {day_col}: {cell_value}")
                 else: availability_info.append(f"- {day_col}: (Trống)")
        else: availability_info.append(f"  (Thông tin chi tiết: {row.to_dict()})")
        data_prompt_list.extend(availability_info)
        if note_col and pd.notna(row.get(note_col)): data_prompt_list.append(f"- Ghi chú: {row[note_col]}")
        else: data_prompt_list.append(f"- Ghi chú: Không có")
        data_prompt_list.append("---")
    data_prompt = "\n".join(data_prompt_list)

    daily_staffing_prompt = "- **Yêu cầu số lượng nhân viên (Part-time) mỗi ca:**\n"
    if start_date:
        for i in range(7):
            current_day = start_date + timedelta(days=i)
            staff_count = 3 if current_day.day == current_day.month else 2
            day_name = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"][i]
            daily_staffing_prompt += f"  + Ngày {current_day.strftime('%Y-%m-%d')} ({day_name}): **{staff_count} người/ca** (Ca 1 và Ca 2).\n"
    else: daily_staffing_prompt += "  + **2 người/ca** cho tất cả các ngày.\n"

    req_prompt_list = [] # Format requirements for prompt
    req_prompt_list.append("\nRàng buộc và Quy tắc xếp lịch:")
    req_prompt_list.append(f"- Ca làm việc: Ca 1 ({requirements['shifts_definition']['Ca 1']['start']} - {requirements['shifts_definition']['Ca 1']['end']}), Ca 2 ({requirements['shifts_definition']['Ca 2']['start']} - {requirements['shifts_definition']['Ca 2']['end']}).")
    req_prompt_list.append(f"- Mỗi nhân viên làm tối đa {requirements['max_shifts_per_day']} ca/ngày.")
    req_prompt_list.append(f"- **QUAN TRỌNG (Công bằng):** Mỗi nhân viên phải được xếp lịch làm việc **ĐÚNG {requirements['shifts_per_week_target']} ca** trong cả tuần.")
    req_prompt_list.append(f"- Ít nhất {requirements['min_rest_hours']} giờ nghỉ giữa các ca (nếu có thể >1 ca/ngày).")
    req_prompt_list.append(f"- Tối đa {requirements['max_consecutive_days']} ngày làm việc liên tiếp.")
    req_prompt_list.append(daily_staffing_prompt) # Add dynamic daily staffing
    # --- UPDATED: Refined note handling instructions ---
    req_prompt_list.append(f"- Xử lý 'Ghi chú' của nhân viên:")
    req_prompt_list.append(f"  + **Ưu tiên 1 (Bắt buộc):** Ghi chú 'nghỉ', 'bận', 'không thể', 'xin off' -> TUYỆT ĐỐI KHÔNG xếp lịch.")
    req_prompt_list.append(f"  + **Ưu tiên 2 (Mong muốn):** Ghi chú 'muốn làm', 'ưu tiên', 'có thể làm' -> CỐ GẮNG xếp nếu không vi phạm ràng buộc khác (mức độ ưu tiên gợi ý: {requirements['preferences_weight_hint']}).")
    req_prompt_list.append(f"  + **Ưu tiên 3 (Giờ làm không trọn vẹn):** Nếu ghi chú có giờ cụ thể (VD: 'chỉ làm 9h-12h', 'làm từ 16h'), hãy làm theo các bước sau:")
    req_prompt_list.append(f"      1. Ưu tiên xếp đủ số người có thể làm **trọn vẹn** ca đó trước.")
    req_prompt_list.append(f"      2. **CHỈ KHI** ca đó vẫn còn thiếu người theo yêu cầu số lượng, thì MỚI xem xét xếp nhân viên có giờ làm không trọn vẹn vào để đáp ứng nguyện vọng của họ (dù họ không làm đủ giờ).")
    req_prompt_list.append(f"      3. Nếu ca đã đủ người làm trọn vẹn, thì KHÔNG xếp thêm người chỉ làm được một phần giờ.")
    req_prompt_list.append("- Chỉ xếp lịch vào ca nhân viên đăng ký/có thể làm.")
    req_prompt_list.append("- Bỏ qua nhân viên 'FM/Sup'.")
    req_prompt = "\n".join(req_prompt_list)

    full_prompt = f"""
Bạn là một trợ lý quản lý lịch làm việc siêu hạng. Dựa vào dữ liệu đăng ký của nhân viên (chủ yếu là Part-time) và các quy tắc ràng buộc dưới đây, hãy tạo ra một lịch làm việc tối ưu cho tuần, **bắt đầu từ ngày Thứ Hai là {start_date_str_for_prompt} (YYYY-MM-DD)**.

{data_prompt}

{req_prompt}

**Yêu cầu đầu ra:**
Hãy trình bày lịch làm việc dưới dạng một bảng MARKDOWN rõ ràng.
**Cột đầu tiên PHẢI là "Ngày" và chứa ngày tháng cụ thể (theo định dạng<y_bin_46>-MM-DD)** cho từng ngày trong tuần (Thứ 2 đến Chủ Nhật), tính toán dựa trên ngày bắt đầu tuần đã cho ({start_date_str_for_prompt}).
Các cột tiếp theo là "Ca" và "Nhân viên được phân công". Sắp xếp theo ngày. **Trong cột "Nhân viên được phân công", liệt kê TẤT CẢ tên nhân viên được xếp vào ca đó, cách nhau bằng dấu phẩy.**

Ví dụ định dạng bảng MARKDOWN mong muốn (với ngày bắt đầu là 2025-05-05, là ngày Double Day):

| Ngày       | Ca    | Nhân viên được phân công |
|------------|-------|--------------------------|
| 2025-05-05 | Ca 1  | NV A, NV B, NV X         | <--- 3 người vì là ngày 5/5
| 2025-05-05 | Ca 2  | NV C, NV D, NV Y         | <--- 3 người vì là ngày 5/5
| 2025-05-06 | Ca 1  | NV E, NV F               | <--- 2 người vì là ngày thường
| ... (cho đến 2025-05-11) ... | ...   | ...                      |

**QUAN TRỌNG:** Chỉ trả về BẢNG MARKDOWN lịch làm việc, không thêm bất kỳ lời giải thích hay bình luận nào khác trước hoặc sau bảng. Đảm bảo cột "Ngày" chứa ngày<y_bin_46>-MM-DD chính xác cho cả tuần. **Đảm bảo xử lý các 'Ghi chú' theo hướng dẫn đã nêu, đặc biệt là logic ưu tiên cho giờ làm không trọn vẹn.** Đảm bảo mọi ràng buộc khác được đáp ứng (đặc biệt là **số người/ca theo từng ngày**, **ĐÚNG {requirements['shifts_per_week_target']} ca/người/tuần**, và {requirements['max_shifts_per_day']} ca/người/ngày). Nếu không thể tạo lịch đáp ứng tất cả ràng buộc (ví dụ: thiếu người cho một ca nào đó, hoặc không thể đảm bảo 4 ca/tuần cho mọi người), hãy ghi rõ điều đó trong bảng hoặc nêu lý do ngắn gọn ngay dưới bảng.
"""
    with st.expander("Xem Prompt gửi đến AI (để tham khảo)"): st.text(full_prompt)
    try: # Call AI Model
        st.info("⏳ Đang gọi AI để tạo lịch..."); response = model.generate_content(full_prompt)
        st.success("✅ AI đã phản hồi."); return response.text
    except Exception as e: st.error(f"Lỗi khi gọi AI: {e}"); return None


# --- Function to Parse AI Response (Keep Improved Column Handling) ---
def parse_ai_schedule(ai_response_text):
    """Attempts to parse the AI's Markdown table response into a DataFrame."""
    st.info("🔎 Đang phân tích phản hồi từ AI...")
    with st.expander("Xem phản hồi thô từ AI"): st.text(ai_response_text)
    match = re.search(r"(\|[^\n]+\|\n\|\s*[-|:]+\s*\|\n(?:\|[^\n]+\|\n?)+)", ai_response_text, re.MULTILINE)
    if not match:
         lines = [line.strip() for line in ai_response_text.strip().split('\n') if line.strip().startswith('|')]
         if len(lines) > 1: st.warning("Không tìm thấy cấu trúc Markdown chuẩn, thử phân tích dòng '|'."); table_content = "\n".join(lines)
         else: st.error("Không tìm thấy định dạng bảng Markdown."); return None
    else: table_content = match.group(1)
    try:
        if table_content.startswith('|---'): table_content = "| H1 | H2 | H3 |\n" + table_content
        data_io = io.StringIO(table_content);
        df_schedule = pd.read_csv(data_io, sep='|', skipinitialspace=True, header=0)
        # Robust Cleaning
        if not df_schedule.empty and df_schedule.columns[0].strip() == '': df_schedule = df_schedule.iloc[:, 1:]
        if not df_schedule.empty and df_schedule.columns[-1].strip() == '': df_schedule = df_schedule.iloc[:, :-1]
        separator_pattern = r'--'; df_schedule = df_schedule[~df_schedule.iloc[:, 0].astype(str).str.contains(separator_pattern)]
        df_schedule = df_schedule.dropna(axis=0, how='all').dropna(axis=1, how='all')
        df_schedule.columns = [col.strip() for col in df_schedule.columns]
        for col in df_schedule.select_dtypes(include=['object']).columns: df_schedule[col] = df_schedule[col].str.strip()
        df_schedule = df_schedule.loc[:, df_schedule.columns.str.strip() != '']
        df_schedule = df_schedule.loc[:, ~df_schedule.columns.str.match('Unnamed')]
        # Assign Column Names by Position
        if len(df_schedule.columns) >= 3:
            df_schedule.columns = ["Ngày", "Ca", "Nhân viên được phân công"] + list(df_schedule.columns[3:])
            df_schedule = df_schedule[["Ngày", "Ca", "Nhân viên được phân công"]]
        else: st.error(f"Lỗi phân tích: Bảng chỉ có {len(df_schedule.columns)} cột, cần ít nhất 3."); st.dataframe(df_schedule); return None
        # Date Conversion
        if "Ngày" in df_schedule.columns:
            try:
                df_schedule['Ngày'] = pd.to_datetime(df_schedule['Ngày'], format='%Y-%m-%d', errors='coerce')
                if df_schedule['Ngày'].isnull().any(): st.warning("Cảnh báo: Một số giá trị 'Ngày' từ AI không hợp lệ.")
                df_schedule = df_schedule.dropna(subset=['Ngày'])
            except Exception as date_err: st.warning(f"Lỗi chuyển đổi cột 'Ngày' từ AI: {date_err}")
        else: st.error("Lỗi nghiêm trọng: Không tìm thấy cột 'Ngày'."); return None
        if df_schedule.empty: st.warning("Không có dữ liệu hợp lệ sau khi phân tích."); return None
        st.success("✅ Phân tích lịch trình từ AI thành công."); return df_schedule
    except Exception as e: st.error(f"Lỗi nghiêm trọng khi phân tích bảng Markdown: {e}"); return None


# --- Function to Display Formatted Schedule (Keep using Selectbox) ---
def display_editable_schedule_with_dropdowns(parsed_schedule_df, availability_df):
    """Displays the schedule using columns and selectboxes for editing."""
    st.subheader("📅 Lịch Làm Việc Tuần (Chỉnh sửa / Thay thế)")
    if parsed_schedule_df is None or parsed_schedule_df.empty: st.warning("Không có dữ liệu lịch để hiển thị."); return None
    if availability_df is None: st.warning("Thiếu dữ liệu tra cứu người thay thế."); return None # Need availability data

    try:
        # Ensure 'Ngày' is datetime
        if 'Ngày' in parsed_schedule_df.columns and not pd.api.types.is_datetime64_any_dtype(parsed_schedule_df['Ngày']):
             parsed_schedule_df['Ngày'] = pd.to_datetime(parsed_schedule_df['Ngày'], errors='coerce')
        parsed_schedule_df = parsed_schedule_df.dropna(subset=['Ngày', 'Ca', 'Nhân viên được phân công'])
        if parsed_schedule_df.empty: st.warning("Không còn dữ liệu hợp lệ sau khi lọc."); return None

        # Get unique sorted dates
        unique_dates = sorted(parsed_schedule_df['Ngày'].dt.date.unique())
        if not unique_dates: st.warning("Không có ngày hợp lệ nào trong dữ liệu."); return None

        # Prepare the 8 display columns
        col_names = ['Thứ', 'Ngày', 'Ca 1 (NV1)', 'Ca 1 (NV2)', 'Ca 1 (NV3)', 'Ca 2 (NV1)', 'Ca 2 (NV2)', 'Ca 2 (NV3)']
        # --- UPDATED: Adjust column widths for compactness ---
        col_widths = [0.6, 0.9, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0] # Make first two columns narrower
        header_cols = st.columns(col_widths)
        for col, name in zip(header_cols, col_names):
             col.markdown(f"**{name}**", unsafe_allow_html=True)
        st.divider()

        # Store current selections (important for statefulness)
        if 'current_schedule_selections' not in st.session_state:
             st.session_state.current_schedule_selections = {}

        vietnamese_days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
        edited_data = [] # To store the final selections for download/later use

        for current_date in unique_dates:
            row_cols = st.columns(col_widths) # Use adjusted widths for rows too
            day_name = vietnamese_days[current_date.weekday()]
            date_str = current_date.strftime('%d/%m/%Y')
            row_cols[0].markdown(f"<div style='text-align: center; height: 100%; display: flex; align-items: center; justify-content: center;'>{day_name}</div>", unsafe_allow_html=True)
            row_cols[1].markdown(f"<div style='text-align: center; height: 100%; display: flex; align-items: center; justify-content: center;'>{date_str}</div>", unsafe_allow_html=True)

            # --- Process Ca 1 ---
            staff_ca1_str = parsed_schedule_df[(parsed_schedule_df['Ngày'].dt.date == current_date) & (parsed_schedule_df['Ca'] == 'Ca 1')]['Nhân viên được phân công'].iloc[0] if not parsed_schedule_df[(parsed_schedule_df['Ngày'].dt.date == current_date) & (parsed_schedule_df['Ca'] == 'Ca 1')].empty else ""
            initial_staff_ca1 = [name.strip() for name in staff_ca1_str.split(',') if name.strip()]
            available_ca1_df = availability_df[(availability_df['Date'] == current_date) & (availability_df['Shift'] == 'Ca 1') & (availability_df['Can_Work'] == True)]
            available_ca1_list = [""] + sorted(available_ca1_df['Employee'].unique().tolist()) # Add empty option

            selected_ca1 = []
            for i in range(3): # NV1, NV2, NV3 for Ca 1
                 col_index = i + 2
                 selectbox_key = f"ca1_nv{i+1}_{date_str}"
                 initial_selection = initial_staff_ca1[i] if i < len(initial_staff_ca1) else ""
                 current_selection = st.session_state.current_schedule_selections.get(selectbox_key, initial_selection)
                 if current_selection not in available_ca1_list: current_selection = ""
                 try: selected_index = available_ca1_list.index(current_selection)
                 except ValueError: selected_index = 0
                 selected_emp = row_cols[col_index].selectbox(f"Ca 1 NV{i+1}", options=available_ca1_list, index=selected_index, key=selectbox_key, label_visibility="collapsed")
                 selected_ca1.append(selected_emp)
                 st.session_state.current_schedule_selections[selectbox_key] = selected_emp

            # --- Process Ca 2 ---
            staff_ca2_str = parsed_schedule_df[(parsed_schedule_df['Ngày'].dt.date == current_date) & (parsed_schedule_df['Ca'] == 'Ca 2')]['Nhân viên được phân công'].iloc[0] if not parsed_schedule_df[(parsed_schedule_df['Ngày'].dt.date == current_date) & (parsed_schedule_df['Ca'] == 'Ca 2')].empty else ""
            initial_staff_ca2 = [name.strip() for name in staff_ca2_str.split(',') if name.strip()]
            available_ca2_df = availability_df[(availability_df['Date'] == current_date) & (availability_df['Shift'] == 'Ca 2') & (availability_df['Can_Work'] == True)]
            available_ca2_list = [""] + sorted(available_ca2_df['Employee'].unique().tolist())

            selected_ca2 = []
            for i in range(3): # NV1, NV2, NV3 for Ca 2
                 col_index = i + 5
                 selectbox_key = f"ca2_nv{i+1}_{date_str}"
                 initial_selection = initial_staff_ca2[i] if i < len(initial_staff_ca2) else ""
                 current_selection = st.session_state.current_schedule_selections.get(selectbox_key, initial_selection)
                 if current_selection not in available_ca2_list: current_selection = ""
                 try: selected_index = available_ca2_list.index(current_selection)
                 except ValueError: selected_index = 0
                 selected_emp = row_cols[col_index].selectbox(f"Ca 2 NV{i+1}", options=available_ca2_list, index=selected_index, key=selectbox_key, label_visibility="collapsed")
                 selected_ca2.append(selected_emp)
                 st.session_state.current_schedule_selections[selectbox_key] = selected_emp

            # Store the row data based on selections
            edited_row = {
                'Thứ': day_name, 'Ngày': date_str,
                'Ca 1 (NV1)': selected_ca1[0], 'Ca 1 (NV2)': selected_ca1[1], 'Ca 1 (NV3)': selected_ca1[2],
                'Ca 2 (NV1)': selected_ca2[0], 'Ca 2 (NV2)': selected_ca2[1], 'Ca 2 (NV3)': selected_ca2[2],
            }
            edited_data.append(edited_row)
            st.divider() # Add divider between rows

        # Return the DataFrame constructed from the current selections
        return pd.DataFrame(edited_data)

    except Exception as e:
        st.error(f"Lỗi khi tạo/hiển thị bảng chỉnh sửa: {e}")
        st.write("Dữ liệu DataFrame gốc từ AI (trước khi tạo bảng):")
        st.dataframe(parsed_schedule_df) # Show the intermediate data
        return None # Return None on error


# --- Function to Create 8-Column DataFrame (Helper Function) ---
# --- ADDED BACK: This function is needed if display_editable_schedule_with_dropdowns fails or for initial state ---
def create_8_column_df(df_schedule):
    """Creates the 8-column display DataFrame from the parsed 3-column schedule."""
    if df_schedule is None or df_schedule.empty: return None
    try:
        # Ensure 'Ngày' is datetime
        if 'Ngày' in df_schedule.columns and not pd.api.types.is_datetime64_any_dtype(df_schedule['Ngày']):
             df_schedule['Ngày'] = pd.to_datetime(df_schedule['Ngày'], errors='coerce')
        df_schedule = df_schedule.dropna(subset=['Ngày', 'Ca', 'Nhân viên được phân công'])
        if df_schedule.empty: return None
        unique_dates = sorted(df_schedule['Ngày'].dt.date.unique())
        if not unique_dates: return None

        output_rows = []
        vietnamese_days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
        for current_date in unique_dates:
            day_name = vietnamese_days[current_date.weekday()]
            date_str = current_date.strftime('%d/%m/%Y')
            staff_ca1_str = df_schedule[(df_schedule['Ngày'].dt.date == current_date) & (df_schedule['Ca'] == 'Ca 1')]['Nhân viên được phân công'].iloc[0] if not df_schedule[(df_schedule['Ngày'].dt.date == current_date) & (df_schedule['Ca'] == 'Ca 1')].empty else ""
            staff_ca1_list = [name.strip() for name in staff_ca1_str.split(',') if name.strip()]
            staff_ca2_str = df_schedule[(df_schedule['Ngày'].dt.date == current_date) & (df_schedule['Ca'] == 'Ca 2')]['Nhân viên được phân công'].iloc[0] if not df_schedule[(df_schedule['Ngày'].dt.date == current_date) & (df_schedule['Ca'] == 'Ca 2')].empty else ""
            staff_ca2_list = [name.strip() for name in staff_ca2_str.split(',') if name.strip()]
            row_data = {
                'Thứ': day_name, 'Ngày': date_str,
                'Ca 1 (NV1)': staff_ca1_list[0] if len(staff_ca1_list) > 0 else '', 'Ca 1 (NV2)': staff_ca1_list[1] if len(staff_ca1_list) > 1 else '', 'Ca 1 (NV3)': staff_ca1_list[2] if len(staff_ca1_list) > 2 else '',
                'Ca 2 (NV1)': staff_ca2_list[0] if len(staff_ca2_list) > 0 else '', 'Ca 2 (NV2)': staff_ca2_list[1] if len(staff_ca2_list) > 1 else '', 'Ca 2 (NV3)': staff_ca2_list[2] if len(staff_ca2_list) > 2 else '',
            }
            output_rows.append(row_data)
        df_display = pd.DataFrame(output_rows)
        column_order = ['Thứ', 'Ngày', 'Ca 1 (NV1)', 'Ca 1 (NV2)', 'Ca 1 (NV3)', 'Ca 2 (NV1)', 'Ca 2 (NV2)', 'Ca 2 (NV3)']
        df_display = df_display[column_order]
        return df_display
    except Exception as e:
        st.error(f"Lỗi khi tạo bảng 8 cột (helper): {e}")
        return None


# --- REMOVED: find_replacements_ui function ---

# --- Main Application Logic (UPDATED State Management and Display Logic) ---
def main_app():
    """Main application function after login."""
    load_css()
    st.title("📅 AI Work Schedule Manager")
    st.caption("Dán dữ liệu đăng ký từ Excel và để AI tạo lịch làm việc tối ưu.")
    st.divider()
    # Initialize session state
    if 'df_from_paste' not in st.session_state: st.session_state.df_from_paste = None
    if 'schedule_df' not in st.session_state: st.session_state.schedule_df = None # Parsed 3-column AI result
    if 'edited_schedule_table' not in st.session_state: st.session_state.edited_schedule_table = None # Stores the DF from the manual table
    if 'ai_response_text' not in st.session_state: st.session_state.ai_response_text = None
    if 'availability_lookup_df' not in st.session_state: st.session_state.availability_lookup_df = None # Re-added
    if 'copyable_text' not in st.session_state: st.session_state.copyable_text = None # State for copyable text

    requirements = get_scheduling_requirements()
    if requirements is None: st.stop()
    input_container = st.container(border=True) # Use container with border
    with input_container: # Input Section
        st.subheader("📋 Bước 1: Dán Dữ Liệu Đăng Ký")
        col1, col2 = st.columns([3, 1])
        with col1: pasted_data = st.text_area("Dán dữ liệu từ bảng Excel:", height=250, key="pasted_data_area", label_visibility="collapsed")
        with col2:
            st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
            process_button = st.button("⚙️ Xử lý dữ liệu", key="process_paste_button", use_container_width=True)
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            generate_button_placeholder = st.empty()

    if process_button: # Data Processing Logic
        # Reset states
        st.session_state.df_from_paste = None; st.session_state.schedule_df = None; st.session_state.edited_schedule_table = None;
        st.session_state.ai_response_text = None; st.session_state.availability_lookup_df = None # Reset lookup table
        st.session_state.current_schedule_selections = {} # Reset selections
        st.session_state.copyable_text = None # Reset copyable text
        if pasted_data:
            try:
                # --- UPDATED: Flexible Header Reading ---
                data_io = io.StringIO(pasted_data)
                first_line = data_io.readline().lower() # Read first line for header check
                data_io.seek(0) # Reset pointer to read the whole data again
                header_keywords = ["tên", "thứ", "ghi chú", "tuần", "ngày"] # Keywords to detect header
                if any(keyword in first_line for keyword in header_keywords):
                    temp_df = pd.read_csv(data_io, sep='\t', header=0, skipinitialspace=True)
                    st.info("Đã đọc dữ liệu với tiêu đề từ người dùng.")
                else:
                    temp_df = pd.read_csv(data_io, sep='\t', header=None, names=PREDEFINED_COLUMNS, skipinitialspace=True)
                    st.info("Không phát hiện tiêu đề, đã sử dụng tên cột mặc định.")

                temp_df.dropna(axis=0, how='all', inplace=True); temp_df.dropna(axis=1, how='all', inplace=True)
                if not temp_df.empty:
                    st.session_state.df_from_paste = temp_df; st.success("✅ Đã xử lý dữ liệu dán thành công.")
                    st.session_state.availability_lookup_df = preprocess_pasted_data_for_lookup(st.session_state.df_from_paste)
                else: st.warning("⚠️ Dữ liệu sau khi xử lý bị rỗng.")
            except pd.errors.EmptyDataError: st.warning("⚠️ Dữ liệu dán vào trống.")
            except Exception as e: st.error(f"❌ Lỗi khi đọc dữ liệu: {e}"); st.error("Mẹo: Đảm bảo copy đúng vùng BẢNG (tab-separated).")
        else: st.warning("⚠️ Chưa có dữ liệu nào được dán vào.")

    if st.session_state.df_from_paste is not None: # Display Processed Data & Generate Button
        with st.container(border=True):
             st.subheader("📄 Bước 2: Kiểm Tra Dữ Liệu Gốc")
             st.dataframe(st.session_state.df_from_paste, use_container_width=True)
             if not st.session_state.df_from_paste.empty:
                  if generate_button_placeholder.button("✨ Tạo Lịch với AI", key="generate_ai_button", use_container_width=True):
                      with st.spinner("⏳ Đang yêu cầu AI tạo lịch..."): # AI Generation Trigger
                          ai_response = generate_schedule_with_ai(st.session_state.df_from_paste, requirements, model)
                          st.session_state.ai_response_text = ai_response; st.session_state.schedule_df = None; st.session_state.edited_schedule_table = None # Reset results
                          st.session_state.current_schedule_selections = {} # Reset selections on new generation
                          st.session_state.copyable_text = None # Reset copyable text
                          if ai_response:
                              parsed_df = parse_ai_schedule(ai_response)
                              if parsed_df is not None:
                                   st.session_state.schedule_df = parsed_df # Store the 3-column parsed data
                                   # --- Generate the initial 8-column display DF ---
                                   st.session_state.edited_schedule_table = create_8_column_df(st.session_state.schedule_df) # Use helper to create
                          else: st.error("❌ Không nhận được phản hồi từ AI.")
             else: st.info("Dữ liệu đã xử lý trống, không thể tạo lịch.")

    # --- Display Result Section (using manual table with dropdowns) ---
    if st.session_state.edited_schedule_table is not None: # Check if the 8-column DF exists
        with st.container(border=True):
             # Display the editable table and store the resulting DataFrame
             st.session_state.edited_schedule_table = display_editable_schedule_with_dropdowns(
                 st.session_state.schedule_df, # Pass the original parsed schedule for initial values
                 st.session_state.availability_lookup_df # Pass availability data
             )

        # REMOVED: Call to find_replacements_ui

        # --- ADDED: Section to generate copyable text ---
        st.divider()
        with st.container(border=True):
             st.subheader("📝 Sao Chép Dữ Liệu Lịch")
             copy_text_button = st.button("Tạo văn bản để Copy sang Excel/Sheet", key="generate_copy_text_button", use_container_width=True)
             if copy_text_button:
                  df_to_copy = st.session_state.get('edited_schedule_table', None)
                  if df_to_copy is not None:
                       try:
                            # Convert DataFrame to tab-separated string
                            copy_string = df_to_copy.to_csv(sep='\t', index=False, header=True) # Include header
                            st.session_state.copyable_text = copy_string
                       except Exception as e:
                            st.error(f"Lỗi khi tạo văn bản để copy: {e}")
                            st.session_state.copyable_text = None
                  else:
                       st.warning("Không có dữ liệu lịch đã chỉnh sửa để tạo văn bản.")
                       st.session_state.copyable_text = None

             # Display the text area if copyable_text exists
             if st.session_state.copyable_text:
                  st.text_area(
                       "Copy toàn bộ nội dung dưới đây (Ctrl+A, Ctrl+C) và dán vào ô A1 của Excel/Sheet:",
                       st.session_state.copyable_text,
                       height=200,
                       key="copy_text_output"
                  )


        # --- Download Section (Downloads the EDITED 8-column table) ---
        st.divider(); st.subheader("📥 Tải Xuống Lịch (8 Cột - Đã Chỉnh Sửa)")
        col_dl1, col_dl2 = st.columns(2)

        df_to_download_final = st.session_state.get('edited_schedule_table', None) # Get the DF from the manual table

        if df_to_download_final is not None:
            try: # 8-Col CSV
                csv_8col = df_to_download_final.to_csv(index=False, encoding='utf-8-sig')
                col_dl1.download_button("Tải CSV (Đã sửa)", csv_8col, "edited_schedule_8col.csv", "text/csv", use_container_width=True, key="dl_csv_8col_edit")
            except Exception as e: col_dl1.error(f"Lỗi CSV 8 cột: {e}")
            try: # 8-Col Excel
                buffer_excel_8col = io.BytesIO()
                engine = 'xlsxwriter' if 'xlsxwriter' in sys.modules else 'openpyxl'
                with pd.ExcelWriter(buffer_excel_8col, engine=engine) as writer:
                    df_to_download_final.to_excel(writer, index=False, sheet_name='Edited_Schedule_8Col')
                col_dl2.download_button("Tải Excel (Đã sửa)", buffer_excel_8col.getvalue(), "edited_schedule_8col.xlsx", "application/vnd.ms-excel", use_container_width=True, key="dl_excel_8col_edit")
            except Exception as e: col_dl2.error(f"Lỗi Excel 8 cột: {e}")
        else:
            col_dl1.warning("Không có dữ liệu lịch đã sửa để tải.")
            col_dl2.warning("Không có dữ liệu lịch đã sửa để tải.")


    # --- UPDATED: Use user-provided copyright in Sidebar ---
    st.sidebar.divider() # Add a divider before copyright
    st.sidebar.markdown("<p class='footer-copyright'>Copyright ©LeQuyPhat</p>", unsafe_allow_html=True)

# --- Entry Point ---
def main():
    """Main function to handle login state."""
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    load_css() # Load CSS needs to happen outside login check if login UI uses it
    if not st.session_state.logged_in: login()
    else: main_app()

if __name__ == "__main__":
    main()
