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
    model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config) # Sử dụng gemini-1.5-flash
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
                color: #7f8c8d; font-size: 12px; text-align: center; padding-top: 20px;
            }
             body:has([data-theme="dark"]) .footer-copyright { color: #95a5a6; }

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
        "shifts_per_week_target": 4, # Mục tiêu số ca mỗi tuần
        "min_rest_hours": st.sidebar.number_input("Giờ nghỉ tối thiểu (>1 ca/ngày)", min_value=1, value=8, step=1),
        "max_consecutive_days": st.sidebar.number_input("Ngày làm liên tiếp tối đa", min_value=1, max_value=7, value=6, step=1),
        "preferences_weight_hint": st.sidebar.slider("Ưu tiên nguyện vọng ghi chú", 0.0, 1.0, 0.7, 0.1)
    }
    st.sidebar.divider(); st.sidebar.markdown("**ℹ️ Quy tắc:**")
    st.sidebar.markdown(f"- **Ca 1:** {requirements['shifts_definition']['Ca 1']['start']} - {requirements['shifts_definition']['Ca 1']['end']}")
    st.sidebar.markdown(f"- **Ca 2:** {requirements['shifts_definition']['Ca 2']['start']} - {requirements['shifts_definition']['Ca 2']['end']}")
    st.sidebar.markdown(f"- **Số người/ca:** **2** (ngày thường), **3** (ngày trùng tháng VD: 3/3, 5/5...)")
    st.sidebar.markdown(f"- **Tối đa:** **{requirements['max_shifts_per_day']}** ca/người/ngày")
    st.sidebar.markdown(f"- **Tổng số ca/tuần (Mục tiêu):** **{requirements['shifts_per_week_target']}** ca/người") # Hiển thị mục tiêu
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
            # Thử định dạng DD/MM/YYYY trước
            start_date = pd.to_datetime(date_val_str, format='%d/%m/%Y', errors='coerce')
            if pd.isna(start_date): # Nếu thất bại, thử định dạng MM/DD/YYYY
                start_date = pd.to_datetime(date_val_str, format='%m/%d/%Y', errors='coerce')
            if pd.isna(start_date): # Nếu vẫn thất bại, thử định dạng YYYY-MM-DD
                start_date = pd.to_datetime(date_val_str, format='%Y-%m-%d', errors='coerce')
            if pd.isna(start_date): # Nếu vẫn thất bại, để pandas tự động phát hiện
                 start_date = pd.to_datetime(date_val_str, errors='coerce')

            if pd.notna(start_date):
                start_date = start_date - timedelta(days=start_date.weekday()) # Lùi về thứ 2 đầu tuần
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
        4: ['thứ 6', 'fri'], 5: ['thứ 7', 'sat'], 6: ['chủ nhật', 'sun', 'cn'] # Thêm 'cn'
    }
    found_day_cols = False
    for day_index, keywords in day_keywords_map.items():
        for col in df_input.columns:
            col_lower = str(col).lower()
            # --- More specific check for day columns, allowing for variations ---
            if any(f'[{keyword}]' in col_lower for keyword in keywords) or \
               any(f' {keyword}' in col_lower for keyword in keywords) or \
               any(keyword == col_lower.replace("bạn có thể làm việc thời gian nào?", "").strip().replace("[","").replace("]","") for keyword in keywords):
                 day_mapping[day_index] = col; found_day_cols = True; break
    if not found_day_cols: st.error("❌ Không tìm thấy các cột ngày (VD: '... [Thứ 2]'). Kiểm tra lại tên cột."); return None
    if not employee_col: st.error("❌ Không tìm thấy cột tên nhân viên."); return None

    for index, row in df_input.iterrows():
        employee = row.get(employee_col); note = row.get(note_col, '') if note_col else ''
        if not employee or pd.isna(employee): continue
        for day_index, day_col in day_mapping.items():
            current_date = start_date + timedelta(days=day_index)
            availability_text = str(row.get(day_col, '')).lower()
            can_do_ca1 = False; can_do_ca2 = False
            if 'nghỉ' in availability_text or 'off' in availability_text or 'bận' in availability_text: pass # Both remain False
            else:
                if 'ca 1' in availability_text or 'sáng' in availability_text or '9h' in availability_text or '9:00' in availability_text: can_do_ca1 = True
                if 'ca 2' in availability_text or 'chiều' in availability_text or '14h' in availability_text or '2h' in availability_text or '14:00' in availability_text: can_do_ca2 = True
                # If text exists but doesn't specify shift, assume both possible unless explicitly 'nghi'
                if not can_do_ca1 and not can_do_ca2 and availability_text.strip() != '' and not any(x in availability_text for x in ['nghỉ', 'off', 'bận']):
                     can_do_ca1 = True; can_do_ca2 = True
            processed_rows.append({'Date': current_date.date(), 'Employee': str(employee).strip(), 'Shift': 'Ca 1', 'Can_Work': can_do_ca1, 'Note': note})
            processed_rows.append({'Date': current_date.date(), 'Employee': str(employee).strip(), 'Shift': 'Ca 2', 'Can_Work': can_do_ca2, 'Note': note})
    if not processed_rows: st.warning("⚠️ Không có dữ liệu đăng ký hợp lệ."); return pd.DataFrame(columns=['Date', 'Employee', 'Shift', 'Can_Work', 'Note'])
    lookup_df = pd.DataFrame(processed_rows)
    lookup_df['Date'] = pd.to_datetime(lookup_df['Date']).dt.date # Ensure Date is date object
    st.success("✅ Đã xử lý xong dữ liệu đăng ký gốc."); return lookup_df


# --- AI Schedule Generation Function (UPDATED PROMPT with reinforced Double Day rule) ---
def generate_schedule_with_ai(df_input, requirements, model):
    """Constructs a prompt and calls the AI model to generate the schedule."""
    st.info(" Chuẩn bị dữ liệu và tạo prompt cho AI...")
    data_prompt_list = []; data_prompt_list.append("Dữ liệu đăng ký của nhân viên:")
    employee_col = next((col for col in df_input.columns if 'tên' in col.lower()), None)
    note_col = next((col for col in df_input.columns if 'ghi chú' in col.lower()), None)
    day_keywords = ['thứ 2', 'thứ 3', 'thứ 4', 'thứ 5', 'thứ 6', 'thứ 7', 'chủ nhật', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'cn']
    day_cols_map = {} # Sử dụng map để giữ đúng thứ tự ngày
    days_order = ["thứ 2", "thứ 3", "thứ 4", "thứ 5", "thứ 6", "thứ 7", "chủ nhật"] # hoặc "cn"

    # Tìm cột cho từng ngày
    for day_name_vn in days_order:
        for col in df_input.columns:
            col_lower = str(col).lower()
            # Kiểm tra chính xác hơn, ví dụ: "[thứ 2]" hoặc "thứ 2" ở cuối
            if f"[{day_name_vn}]" in col_lower or col_lower.endswith(day_name_vn) or day_name_vn in col_lower:
                day_cols_map[day_name_vn] = col
                break
    day_cols = [day_cols_map[d] for d in days_order if d in day_cols_map] # Lấy các cột theo đúng thứ tự

    start_date = find_start_date(df_input); start_date_str_for_prompt = start_date.strftime('%Y-%m-%d') if start_date else "Không xác định"
    if not employee_col: st.error("Lỗi: Không thể xác định cột 'Tên nhân viên'."); return None
    if not day_cols: st.warning("Không tìm thấy đủ các cột ngày (Thứ 2-CN). Kiểm tra lại tên cột trong file Excel.")
    if start_date is None: st.warning("Không xác định được ngày bắt đầu tuần.")

    data_prompt_list.append(f"(Dữ liệu cho tuần bắt đầu Thứ 2 khoảng: {start_date_str_for_prompt})")
    for index, row in df_input.iterrows(): # Format data for prompt
        emp_name = row[employee_col]; data_prompt_list.append(f"Nhân viên: {emp_name}")
        availability_info = []
        if day_cols:
            for day_col_name in day_cols: # Duyệt theo thứ tự đã sắp xếp
                 cell_value = row.get(day_col_name)
                 # Lấy tên ngày từ tên cột để hiển thị (ví dụ: "Thứ 2" từ "bạn có thể làm việc thời gian nào? [Thứ 2]")
                 clean_day_name = day_col_name
                 match = re.search(r'\[(.*?)\]', day_col_name)
                 if match:
                     clean_day_name = match.group(1)
                 elif any(d in day_col_name.lower() for d in days_order):
                     for d_keyword in days_order:
                         if d_keyword in day_col_name.lower():
                             clean_day_name = d_keyword.capitalize()
                             break

                 if pd.notna(cell_value): availability_info.append(f"- {clean_day_name}: {cell_value}")
                 else: availability_info.append(f"- {clean_day_name}: (Trống)")
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
            day_name_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"][i]
            daily_staffing_prompt += f"  + Ngày {current_day.strftime('%Y-%m-%d')} ({day_name_vn}): **{staff_count} người/ca** (Ca 1 và Ca 2).\n"
    else: daily_staffing_prompt += "  + **2 người/ca** cho tất cả các ngày.\n"

    req_prompt_list = [] # Format requirements for prompt
    req_prompt_list.append("\nRàng buộc và Quy tắc xếp lịch:")
    req_prompt_list.append(f"- Ca làm việc: Ca 1 ({requirements['shifts_definition']['Ca 1']['start']} - {requirements['shifts_definition']['Ca 1']['end']}), Ca 2 ({requirements['shifts_definition']['Ca 2']['start']} - {requirements['shifts_definition']['Ca 2']['end']}).")
    req_prompt_list.append(f"- Mỗi nhân viên làm tối đa {requirements['max_shifts_per_day']} ca/ngày.")
    # --- MODIFIED LINE ---
    req_prompt_list.append(f"- **YÊU CẦU ƯU TIÊN CAO NHẤT (Công bằng & Bắt buộc):** Phải tuyệt đối đảm bảo mỗi nhân viên (không bao gồm FM/Sup và những người có ghi chú xin nghỉ cả tuần hoặc không đủ lịch đăng ký) được xếp lịch làm việc **CHÍNH XÁC VÀ ĐỦ {requirements['shifts_per_week_target']} ca** trong cả tuần. Đây là một trong những mục tiêu quan trọng nhất của việc xếp lịch. Nếu không thể đáp ứng cho một số cá nhân do lịch đăng ký của họ quá hạn chế hoặc các ràng buộc khác không thể giải quyết, AI cần nêu rõ lý do cho từng trường hợp đó.")
    req_prompt_list.append(f"- Ít nhất {requirements['min_rest_hours']} giờ nghỉ giữa các ca (nếu có thể >1 ca/ngày).")
    req_prompt_list.append(f"- Tối đa {requirements['max_consecutive_days']} ngày làm việc liên tiếp.")
    req_prompt_list.append(daily_staffing_prompt[:-1]) # Remove last newline
    req_prompt_list.append("  + **LƯU Ý:** Ngày trùng tháng (ví dụ 3/3, 5/5) cần 3 người/ca, các ngày khác cần 2 người/ca.")
    req_prompt_list.append(f"- Xử lý 'Ghi chú' của nhân viên:")
    req_prompt_list.append(f"  + **Ưu tiên 1 (Bắt buộc):** Ghi chú 'nghỉ', 'bận', 'không thể', 'xin off', 'xin nghỉ' -> TUYỆT ĐỐI KHÔNG xếp lịch.")
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
**Cột đầu tiên PHẢI là "Ngày" và chứa ngày tháng cụ thể (theo định dạng YYYY-MM-DD)** cho từng ngày trong tuần (Thứ 2 đến Chủ Nhật), tính toán dựa trên ngày bắt đầu tuần đã cho ({start_date_str_for_prompt}).
Các cột tiếp theo là "Ca" và "Nhân viên được phân công". Sắp xếp theo ngày. **Trong cột "Nhân viên được phân công", liệt kê TẤT CẢ tên nhân viên được xếp vào ca đó, cách nhau bằng dấu phẩy.**

Ví dụ định dạng bảng MARKDOWN mong muốn (với ngày bắt đầu là 2025-05-05, là ngày Double Day):

| Ngày       | Ca    | Nhân viên được phân công |
|------------|-------|--------------------------|
| 2025-05-05 | Ca 1  | NV A, NV B, NV X         | <--- 3 người vì là ngày 5/5
| 2025-05-05 | Ca 2  | NV C, NV D, NV Y         | <--- 3 người vì là ngày 5/5
| 2025-05-06 | Ca 1  | NV E, NV F               | <--- 2 người vì là ngày thường
| ... (cho đến 2025-05-11) ... | ...   | ...                      |

**QUAN TRỌNG:** Chỉ trả về BẢNG MARKDOWN lịch làm việc, không thêm bất kỳ lời giải thích hay bình luận nào khác trước hoặc sau bảng. Đảm bảo cột "Ngày" chứa ngày YYYY-MM-DD chính xác cho cả tuần. **Đảm bảo xử lý các 'Ghi chú' theo hướng dẫn đã nêu, đặc biệt là logic ưu tiên cho giờ làm không trọn vẹn.** Đảm bảo mọi ràng buộc khác được đáp ứng (đặc biệt là **số người/ca theo từng ngày** như đã nêu ở trên, **ĐÚNG {requirements['shifts_per_week_target']} ca/người/tuần**, và {requirements['max_shifts_per_day']} ca/người/ngày). Nếu không thể tạo lịch đáp ứng tất cả ràng buộc (ví dụ: thiếu người cho một ca nào đó, hoặc không thể đảm bảo {requirements['shifts_per_week_target']} ca/tuần cho mọi người), hãy ghi rõ điều đó trong bảng hoặc nêu lý do ngắn gọn ngay dưới bảng.
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
    # Cố gắng tìm bảng Markdown, kể cả khi có text thừa xung quanh
    table_match = re.search(r"(\n?\|.*?\n(?:\|.*?\n)+)", ai_response_text, re.DOTALL)
    if not table_match:
        # Nếu không tìm thấy bảng hoàn chỉnh, thử tìm các dòng bắt đầu bằng '|'
        lines = [line.strip() for line in ai_response_text.strip().split('\n') if line.strip().startswith('|')]
        if len(lines) > 1:
            st.warning("Không tìm thấy cấu trúc Markdown chuẩn, thử phân tích các dòng bắt đầu bằng '|'.")
            table_content = "\n".join(lines)
            # Kiểm tra xem có dòng header hợp lệ không (chứa ít nhất 2 dấu gạch nối)
            if not re.search(r"\|.*-.*-.*\|", lines[1]):
                st.warning("Dòng header Markdown có vẻ không hợp lệ, sẽ cố gắng thêm header mặc định.")
                # Thêm header giả định nếu dòng thứ hai không phải là dòng phân cách header
                table_content = "| Ngày | Ca | Nhân viên được phân công |\n|---|---|---|\n" + table_content
        else:
            st.error("Không tìm thấy định dạng bảng Markdown trong phản hồi của AI.")
            return None
    else:
        table_content = table_match.group(1).strip()
        # Kiểm tra lại header sau khi trích xuất
        lines = table_content.split('\n')
        if len(lines) > 1 and not re.search(r"\|.*-.*-.*\|", lines[1]):
            st.warning("Dòng header Markdown sau khi trích xuất có vẻ không hợp lệ, sẽ cố gắng thêm header mặc định.")
            table_content = "| Ngày | Ca | Nhân viên được phân công |\n|---|---|---|\n" + lines[0] + "\n" + "\n".join(lines[2:])


    try:
        data_io = io.StringIO(table_content)
        # Đọc CSV, bỏ qua các dòng trống và dòng không phải là bảng
        df_schedule = pd.read_csv(data_io, sep='|', skipinitialspace=True, on_bad_lines='skip')

        # Loại bỏ các cột và hàng trống hoặc không hợp lệ
        df_schedule = df_schedule.dropna(axis=1, how='all') # Bỏ cột toàn NaN
        df_schedule = df_schedule.iloc[:, 1:-1] # Bỏ cột trống ở đầu và cuối do dấu '|'
        df_schedule.columns = [col.strip() for col in df_schedule.columns]
        # Loại bỏ dòng phân cách của Markdown (ví dụ: |---|---|---|)
        df_schedule = df_schedule[~df_schedule.iloc[:, 0].astype(str).str.contains(r'--\s*--', na=False)]
        df_schedule = df_schedule.dropna(axis=0, how='all') # Bỏ hàng toàn NaN

        # Đổi tên cột nếu cần
        if len(df_schedule.columns) >= 3:
            # Ưu tiên tên cột từ AI nếu hợp lệ, nếu không thì dùng tên mặc định
            expected_cols = ["Ngày", "Ca", "Nhân viên được phân công"]
            current_cols = df_schedule.columns.tolist()
            # Kiểm tra xem tên cột hiện tại có vẻ hợp lý không
            if not all(any(expected.lower() in current.lower() for expected in expected_cols) for current in current_cols[:3]):
                 st.warning(f"Tên cột từ AI không khớp hoàn toàn: {current_cols}. Sử dụng tên cột mặc định.")
                 df_schedule = df_schedule.iloc[:, :3] # Chỉ lấy 3 cột đầu
                 df_schedule.columns = expected_cols
            else:
                # Giữ lại tên cột từ AI nhưng chuẩn hóa
                df_schedule.columns = [current_cols[0]] + [current_cols[1]] + [current_cols[2]] + current_cols[3:]
                df_schedule = df_schedule.iloc[:, :3] # Chỉ lấy 3 cột chính
                df_schedule.columns = expected_cols # Đảm bảo tên cột chuẩn

        elif len(df_schedule.columns) == 2 and "Ngày" in df_schedule.columns[0] and "Ca" in df_schedule.columns[1]:
            st.warning("Bảng từ AI thiếu cột 'Nhân viên được phân công'. Sẽ hiển thị với cột đó trống.")
            df_schedule["Nhân viên được phân công"] = ""
            df_schedule.columns = ["Ngày", "Ca", "Nhân viên được phân công"]
        else:
            st.error(f"Lỗi phân tích: Bảng chỉ có {len(df_schedule.columns)} cột, cần ít nhất 3 cột ('Ngày', 'Ca', 'Nhân viên').")
            st.dataframe(df_schedule)
            return None

        # Làm sạch dữ liệu trong các ô
        for col in df_schedule.columns:
            if df_schedule[col].dtype == 'object':
                df_schedule[col] = df_schedule[col].str.strip()

        # Chuyển đổi cột 'Ngày'
        if "Ngày" in df_schedule.columns:
            try:
                # Thử nhiều định dạng ngày tháng
                df_schedule['Ngày'] = pd.to_datetime(df_schedule['Ngày'], errors='coerce')
                # Kiểm tra lại nếu có giá trị NaT sau khi chuyển đổi
                if df_schedule['Ngày'].isnull().any():
                    st.warning("Cảnh báo: Một số giá trị 'Ngày' từ AI không hợp lệ hoặc không đúng định dạng YYYY-MM-DD. Sẽ cố gắng chuyển đổi lại.")
                    # Thử lại với các định dạng phổ biến khác nếu cần
                    for idx, val in df_schedule['Ngày'].items():
                        if pd.isna(val):
                            try:
                                df_schedule.loc[idx, 'Ngày'] = pd.to_datetime(df_schedule.loc[idx, 'Ngày_str_backup'], dayfirst=True, errors='coerce') # Giả sử có cột backup
                            except: # Bỏ qua nếu không có cột backup hoặc vẫn lỗi
                                pass
                df_schedule = df_schedule.dropna(subset=['Ngày']) # Bỏ những dòng không có ngày hợp lệ
            except Exception as date_err:
                st.warning(f"Lỗi chuyển đổi cột 'Ngày' từ AI: {date_err}. Kiểm tra định dạng ngày trong phản hồi của AI.")
        else:
            st.error("Lỗi nghiêm trọng: Không tìm thấy cột 'Ngày' trong bảng phân tích.")
            return None

        if df_schedule.empty:
            st.warning("Không có dữ liệu hợp lệ sau khi phân tích phản hồi từ AI.")
            return None

        st.success("✅ Phân tích lịch trình từ AI thành công."); return df_schedule
    except Exception as e:
        st.error(f"Lỗi nghiêm trọng khi phân tích bảng Markdown từ AI: {e}")
        st.info("Vui lòng kiểm tra 'Phản hồi thô từ AI' ở trên để xem định dạng AI trả về.")
        return None


# --- Function to Display Formatted Schedule (Keep using Selectbox) ---
def display_editable_schedule_with_dropdowns(parsed_schedule_df, availability_df):
    """Displays the schedule using columns and selectboxes for editing."""
    st.subheader("📅 Lịch Làm Việc Tuần (Chỉnh sửa / Thay thế)")
    if parsed_schedule_df is None or parsed_schedule_df.empty: st.warning("Không có dữ liệu lịch để hiển thị."); return None
    if availability_df is None or availability_df.empty:
        st.warning("Thiếu dữ liệu tra cứu người thay thế (availability_df trống). Không thể tạo danh sách chọn.")
        # Hiển thị bảng chỉ đọc nếu không có availability_df
        st.dataframe(create_8_column_df(parsed_schedule_df))
        return create_8_column_df(parsed_schedule_df) # Trả về bảng 8 cột không chỉnh sửa được

    try:
        # Ensure 'Ngày' is datetime
        if 'Ngày' in parsed_schedule_df.columns and not pd.api.types.is_datetime64_any_dtype(parsed_schedule_df['Ngày']):
             parsed_schedule_df['Ngày'] = pd.to_datetime(parsed_schedule_df['Ngày'], errors='coerce')
        # Loại bỏ các dòng có giá trị NaN trong các cột quan trọng
        parsed_schedule_df = parsed_schedule_df.dropna(subset=['Ngày', 'Ca'])
        # Đảm bảo cột 'Nhân viên được phân công' là string, thay NaN bằng chuỗi rỗng
        if 'Nhân viên được phân công' in parsed_schedule_df.columns:
            parsed_schedule_df['Nhân viên được phân công'] = parsed_schedule_df['Nhân viên được phân công'].fillna('').astype(str)
        else:
            parsed_schedule_df['Nhân viên được phân công'] = ""


        if parsed_schedule_df.empty: st.warning("Không còn dữ liệu hợp lệ sau khi lọc."); return None

        # Get unique sorted dates
        unique_dates = sorted(parsed_schedule_df['Ngày'].dt.date.unique())
        if not unique_dates: st.warning("Không có ngày hợp lệ nào trong dữ liệu."); return None

        col_names = ['Thứ', 'Ngày', 'Ca 1 (NV1)', 'Ca 1 (NV2)', 'Ca 1 (NV3)', 'Ca 2 (NV1)', 'Ca 2 (NV2)', 'Ca 2 (NV3)']
        col_widths = [0.6, 0.9, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0]
        header_cols = st.columns(col_widths)
        for col, name in zip(header_cols, col_names):
             col.markdown(f"<div style='text-align: center; font-weight: bold;'>{name}</div>", unsafe_allow_html=True) # Căn giữa và in đậm header
        st.divider()

        if 'current_schedule_selections' not in st.session_state:
             st.session_state.current_schedule_selections = {}

        vietnamese_days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
        edited_data = []

        all_available_employees = [""] + sorted(availability_df['Employee'].unique().tolist()) # Danh sách chung cho trường hợp không tìm thấy nhân viên cụ thể

        for current_date_obj in unique_dates: # Đổi tên biến để rõ ràng hơn
            row_cols = st.columns(col_widths)
            day_name = vietnamese_days[current_date_obj.weekday()]
            date_str = current_date_obj.strftime('%d/%m/%Y')
            row_cols[0].markdown(f"<div style='text-align: center; height: 100%; display: flex; align-items: center; justify-content: center;'>{day_name}</div>", unsafe_allow_html=True)
            row_cols[1].markdown(f"<div style='text-align: center; height: 100%; display: flex; align-items: center; justify-content: center;'>{date_str}</div>", unsafe_allow_html=True)

            # --- Process Ca 1 ---
            ca1_data = parsed_schedule_df[(parsed_schedule_df['Ngày'].dt.date == current_date_obj) & (parsed_schedule_df['Ca'] == 'Ca 1')]
            staff_ca1_str = ca1_data['Nhân viên được phân công'].iloc[0] if not ca1_data.empty else ""
            initial_staff_ca1 = [name.strip() for name in staff_ca1_str.split(',') if name.strip()]
            # Lấy danh sách nhân viên có thể làm Ca 1 vào ngày này
            available_ca1_df = availability_df[(availability_df['Date'] == current_date_obj) & (availability_df['Shift'] == 'Ca 1') & (availability_df['Can_Work'] == True)]
            available_ca1_list = [""] + sorted(available_ca1_df['Employee'].unique().tolist())
            if not available_ca1_list and not all_available_employees: # Nếu không có ai đăng ký ca này
                available_ca1_list = ["(Không có ai đăng ký)"]


            selected_ca1 = []
            for i in range(3): # NV1, NV2, NV3 for Ca 1
                 col_index = i + 2
                 selectbox_key = f"ca1_nv{i+1}_{date_str}_{current_date_obj.year}" # Thêm năm để key duy nhất hơn
                 initial_selection = initial_staff_ca1[i] if i < len(initial_staff_ca1) else ""
                 # Lấy lựa chọn hiện tại từ session state, nếu không có thì dùng initial_selection
                 current_selection_val = st.session_state.current_schedule_selections.get(selectbox_key, initial_selection)

                 # Đảm bảo current_selection_val nằm trong danh sách tùy chọn
                 options_list_c1 = available_ca1_list if available_ca1_list != ["(Không có ai đăng ký)"] else all_available_employees
                 if current_selection_val not in options_list_c1 and initial_selection in options_list_c1:
                     current_selection_val = initial_selection # Reset về initial nếu current không hợp lệ nhưng initial hợp lệ
                 elif current_selection_val not in options_list_c1:
                     current_selection_val = options_list_c1[0] if options_list_c1 else "" # Chọn giá trị đầu tiên (thường là rỗng)

                 try: selected_index_c1 = options_list_c1.index(current_selection_val)
                 except ValueError: selected_index_c1 = 0

                 selected_emp_c1 = row_cols[col_index].selectbox(f"Ca 1 NV{i+1} {date_str}", options=options_list_c1, index=selected_index_c1, key=selectbox_key, label_visibility="collapsed")
                 selected_ca1.append(selected_emp_c1)
                 st.session_state.current_schedule_selections[selectbox_key] = selected_emp_c1

            # --- Process Ca 2 ---
            ca2_data = parsed_schedule_df[(parsed_schedule_df['Ngày'].dt.date == current_date_obj) & (parsed_schedule_df['Ca'] == 'Ca 2')]
            staff_ca2_str = ca2_data['Nhân viên được phân công'].iloc[0] if not ca2_data.empty else ""
            initial_staff_ca2 = [name.strip() for name in staff_ca2_str.split(',') if name.strip()]
            available_ca2_df = availability_df[(availability_df['Date'] == current_date_obj) & (availability_df['Shift'] == 'Ca 2') & (availability_df['Can_Work'] == True)]
            available_ca2_list = [""] + sorted(available_ca2_df['Employee'].unique().tolist())
            if not available_ca2_list and not all_available_employees:
                available_ca2_list = ["(Không có ai đăng ký)"]

            selected_ca2 = []
            for i in range(3): # NV1, NV2, NV3 for Ca 2
                 col_index = i + 5
                 selectbox_key = f"ca2_nv{i+1}_{date_str}_{current_date_obj.year}"
                 initial_selection = initial_staff_ca2[i] if i < len(initial_staff_ca2) else ""
                 current_selection_val = st.session_state.current_schedule_selections.get(selectbox_key, initial_selection)

                 options_list_c2 = available_ca2_list if available_ca2_list != ["(Không có ai đăng ký)"] else all_available_employees
                 if current_selection_val not in options_list_c2 and initial_selection in options_list_c2:
                     current_selection_val = initial_selection
                 elif current_selection_val not in options_list_c2:
                     current_selection_val = options_list_c2[0] if options_list_c2 else ""

                 try: selected_index_c2 = options_list_c2.index(current_selection_val)
                 except ValueError: selected_index_c2 = 0

                 selected_emp_c2 = row_cols[col_index].selectbox(f"Ca 2 NV{i+1} {date_str}", options=options_list_c2, index=selected_index_c2, key=selectbox_key, label_visibility="collapsed")
                 selected_ca2.append(selected_emp_c2)
                 st.session_state.current_schedule_selections[selectbox_key] = selected_emp_c2

            edited_row = {
                'Thứ': day_name, 'Ngày': date_str,
                'Ca 1 (NV1)': selected_ca1[0], 'Ca 1 (NV2)': selected_ca1[1], 'Ca 1 (NV3)': selected_ca1[2],
                'Ca 2 (NV1)': selected_ca2[0], 'Ca 2 (NV2)': selected_ca2[1], 'Ca 2 (NV3)': selected_ca2[2],
            }
            edited_data.append(edited_row)
            st.divider()

        return pd.DataFrame(edited_data)

    except Exception as e:
        st.error(f"Lỗi khi tạo/hiển thị bảng chỉnh sửa: {e}")
        st.exception(e) # In chi tiết lỗi để debug
        st.write("Dữ liệu DataFrame gốc từ AI (parsed_schedule_df):")
        st.dataframe(parsed_schedule_df)
        st.write("Dữ liệu tra cứu (availability_df):")
        st.dataframe(availability_df)
        return create_8_column_df(parsed_schedule_df) # Trả về bảng 8 cột không chỉnh sửa được nếu lỗi


# --- Function to Create 8-Column DataFrame (Helper Function) ---
def create_8_column_df(df_schedule):
    """Creates the 8-column display DataFrame from the parsed 3-column schedule."""
    if df_schedule is None or df_schedule.empty: return pd.DataFrame(columns=['Thứ', 'Ngày', 'Ca 1 (NV1)', 'Ca 1 (NV2)', 'Ca 1 (NV3)', 'Ca 2 (NV1)', 'Ca 2 (NV2)', 'Ca 2 (NV3)'])
    try:
        if 'Ngày' in df_schedule.columns and not pd.api.types.is_datetime64_any_dtype(df_schedule['Ngày']):
             df_schedule['Ngày'] = pd.to_datetime(df_schedule['Ngày'], errors='coerce')
        df_schedule = df_schedule.dropna(subset=['Ngày', 'Ca'])
        if 'Nhân viên được phân công' in df_schedule.columns:
            df_schedule['Nhân viên được phân công'] = df_schedule['Nhân viên được phân công'].fillna('').astype(str)
        else:
            df_schedule['Nhân viên được phân công'] = ""

        if df_schedule.empty: return pd.DataFrame(columns=['Thứ', 'Ngày', 'Ca 1 (NV1)', 'Ca 1 (NV2)', 'Ca 1 (NV3)', 'Ca 2 (NV1)', 'Ca 2 (NV2)', 'Ca 2 (NV3)'])
        unique_dates = sorted(df_schedule['Ngày'].dt.date.unique())
        if not unique_dates: return pd.DataFrame(columns=['Thứ', 'Ngày', 'Ca 1 (NV1)', 'Ca 1 (NV2)', 'Ca 1 (NV3)', 'Ca 2 (NV1)', 'Ca 2 (NV2)', 'Ca 2 (NV3)'])

        output_rows = []
        vietnamese_days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
        for current_date_obj in unique_dates: # Đổi tên biến
            day_name = vietnamese_days[current_date_obj.weekday()]
            date_str = current_date_obj.strftime('%d/%m/%Y')

            ca1_data = df_schedule[(df_schedule['Ngày'].dt.date == current_date_obj) & (df_schedule['Ca'] == 'Ca 1')]
            staff_ca1_str = ca1_data['Nhân viên được phân công'].iloc[0] if not ca1_data.empty else ""
            staff_ca1_list = [name.strip() for name in staff_ca1_str.split(',') if name.strip()]

            ca2_data = df_schedule[(df_schedule['Ngày'].dt.date == current_date_obj) & (df_schedule['Ca'] == 'Ca 2')]
            staff_ca2_str = ca2_data['Nhân viên được phân công'].iloc[0] if not ca2_data.empty else ""
            staff_ca2_list = [name.strip() for name in staff_ca2_str.split(',') if name.strip()]

            row_data = {
                'Thứ': day_name, 'Ngày': date_str,
                'Ca 1 (NV1)': staff_ca1_list[0] if len(staff_ca1_list) > 0 else '',
                'Ca 1 (NV2)': staff_ca1_list[1] if len(staff_ca1_list) > 1 else '',
                'Ca 1 (NV3)': staff_ca1_list[2] if len(staff_ca1_list) > 2 else '',
                'Ca 2 (NV1)': staff_ca2_list[0] if len(staff_ca2_list) > 0 else '',
                'Ca 2 (NV2)': staff_ca2_list[1] if len(staff_ca2_list) > 1 else '',
                'Ca 2 (NV3)': staff_ca2_list[2] if len(staff_ca2_list) > 2 else '',
            }
            output_rows.append(row_data)
        df_display = pd.DataFrame(output_rows)
        column_order = ['Thứ', 'Ngày', 'Ca 1 (NV1)', 'Ca 1 (NV2)', 'Ca 1 (NV3)', 'Ca 2 (NV1)', 'Ca 2 (NV2)', 'Ca 2 (NV3)']
        # Đảm bảo tất cả các cột đều tồn tại, nếu không thì tạo cột trống
        for col in column_order:
            if col not in df_display.columns:
                df_display[col] = ''
        df_display = df_display[column_order]
        return df_display
    except Exception as e:
        st.error(f"Lỗi khi tạo bảng 8 cột (helper): {e}")
        return pd.DataFrame(columns=['Thứ', 'Ngày', 'Ca 1 (NV1)', 'Ca 1 (NV2)', 'Ca 1 (NV3)', 'Ca 2 (NV1)', 'Ca 2 (NV2)', 'Ca 2 (NV3)'])


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
    if 'availability_lookup_df' not in st.session_state: st.session_state.availability_lookup_df = pd.DataFrame(columns=['Date', 'Employee', 'Shift', 'Can_Work', 'Note'])
    if 'copyable_text' not in st.session_state: st.session_state.copyable_text = None
    if 'current_schedule_selections' not in st.session_state: st.session_state.current_schedule_selections = {}


    requirements = get_scheduling_requirements()
    if requirements is None: st.stop()
    input_container = st.container(border=True)
    with input_container:
        st.subheader("📋 Bước 1: Dán Dữ Liệu Đăng Ký")
        col1, col2 = st.columns([3, 1])
        with col1: pasted_data = st.text_area("Dán dữ liệu từ bảng Excel (sao chép trực tiếp từ Excel):", height=250, key="pasted_data_area", label_visibility="collapsed")
        with col2:
            st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
            process_button = st.button("⚙️ Xử lý dữ liệu", key="process_paste_button", use_container_width=True)
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            generate_button_placeholder = st.empty()

    if process_button:
        st.session_state.df_from_paste = None; st.session_state.schedule_df = None; st.session_state.edited_schedule_table = None;
        st.session_state.ai_response_text = None;
        st.session_state.availability_lookup_df = pd.DataFrame(columns=['Date', 'Employee', 'Shift', 'Can_Work', 'Note']) # Reset
        st.session_state.current_schedule_selections = {}
        st.session_state.copyable_text = None
        if pasted_data:
            try:
                data_io = io.StringIO(pasted_data)
                # Cố gắng đọc với header, nếu lỗi thì đọc không header
                try:
                    temp_df = pd.read_csv(data_io, sep='\t', header=0, skipinitialspace=True)
                    # Kiểm tra xem header có hợp lệ không (ví dụ: chứa từ khóa)
                    header_keywords = ["tên", "thứ", "ghi chú", "tuần", "ngày"]
                    if not any(keyword in str(col).lower() for col in temp_df.columns for keyword in header_keywords):
                        st.info("Tiêu đề không khớp với từ khóa mong đợi, thử đọc lại không có tiêu đề.")
                        data_io.seek(0) # Reset lại con trỏ file
                        temp_df = pd.read_csv(data_io, sep='\t', header=None, names=PREDEFINED_COLUMNS, skipinitialspace=True)
                        st.info("Đã sử dụng tên cột mặc định.")
                    else:
                        st.info("Đã đọc dữ liệu với tiêu đề từ người dùng.")
                except pd.errors.ParserError: # Xảy ra khi số cột không khớp header
                    st.warning("Lỗi khi đọc với tiêu đề (số cột không khớp). Thử đọc không có tiêu đề.")
                    data_io.seek(0)
                    temp_df = pd.read_csv(data_io, sep='\t', header=None, names=PREDEFINED_COLUMNS, skipinitialspace=True)
                    st.info("Đã sử dụng tên cột mặc định.")
                except Exception: # Các lỗi khác khi đọc với header
                    st.warning("Lỗi khi đọc với tiêu đề. Thử đọc không có tiêu đề.")
                    data_io.seek(0)
                    temp_df = pd.read_csv(data_io, sep='\t', header=None, names=PREDEFINED_COLUMNS, skipinitialspace=True)
                    st.info("Đã sử dụng tên cột mặc định.")


                temp_df.dropna(axis=0, how='all', inplace=True); temp_df.dropna(axis=1, how='all', inplace=True)
                if not temp_df.empty:
                    st.session_state.df_from_paste = temp_df; st.success("✅ Đã xử lý dữ liệu dán thành công.")
                    # Tạo bảng tra cứu availability_lookup_df
                    st.session_state.availability_lookup_df = preprocess_pasted_data_for_lookup(st.session_state.df_from_paste)
                    if st.session_state.availability_lookup_df is None or st.session_state.availability_lookup_df.empty:
                        st.warning("⚠️ Không thể tạo bảng tra cứu lịch đăng ký (availability_lookup_df). Chức năng chỉnh sửa lịch có thể bị hạn chế.")
                        st.session_state.availability_lookup_df = pd.DataFrame(columns=['Date', 'Employee', 'Shift', 'Can_Work', 'Note']) # Khởi tạo lại để tránh lỗi
                else: st.warning("⚠️ Dữ liệu sau khi xử lý bị rỗng.")
            except pd.errors.EmptyDataError: st.warning("⚠️ Dữ liệu dán vào trống.")
            except Exception as e: st.error(f"❌ Lỗi khi đọc dữ liệu: {e}"); st.error("Mẹo: Đảm bảo copy đúng vùng BẢNG (tab-separated)."); st.exception(e)
        else: st.warning("⚠️ Chưa có dữ liệu nào được dán vào.")

    if st.session_state.df_from_paste is not None:
        with st.container(border=True):
             st.subheader("📄 Bước 2: Kiểm Tra Dữ Liệu Gốc")
             st.dataframe(st.session_state.df_from_paste, use_container_width=True, height=300) # Giới hạn chiều cao
             if not st.session_state.df_from_paste.empty:
                  if generate_button_placeholder.button("✨ Tạo Lịch với AI", key="generate_ai_button", use_container_width=True):
                      with st.spinner("⏳ Đang yêu cầu AI tạo lịch..."):
                          ai_response = generate_schedule_with_ai(st.session_state.df_from_paste, requirements, model)
                          st.session_state.ai_response_text = ai_response; st.session_state.schedule_df = None; st.session_state.edited_schedule_table = None
                          st.session_state.current_schedule_selections = {}
                          st.session_state.copyable_text = None
                          if ai_response:
                              parsed_df = parse_ai_schedule(ai_response)
                              if parsed_df is not None and not parsed_df.empty:
                                   st.session_state.schedule_df = parsed_df
                                   # Tạo bảng 8 cột ban đầu từ kết quả AI
                                   st.session_state.edited_schedule_table = create_8_column_df(st.session_state.schedule_df)
                              else:
                                  st.error("❌ Không phân tích được lịch từ AI hoặc lịch trống.")
                                  st.session_state.schedule_df = None # Đảm bảo là None nếu lỗi
                                  st.session_state.edited_schedule_table = create_8_column_df(None) # Tạo bảng trống
                          else:
                              st.error("❌ Không nhận được phản hồi từ AI.")
                              st.session_state.edited_schedule_table = create_8_column_df(None) # Tạo bảng trống
             else: st.info("Dữ liệu đã xử lý trống, không thể tạo lịch.")

    # --- Display Result Section ---
    # Luôn hiển thị khu vực này nếu edited_schedule_table đã được khởi tạo (kể cả khi nó rỗng)
    if st.session_state.get('edited_schedule_table') is not None:
        with st.container(border=True):
             # Hiển thị bảng chỉnh sửa, truyền cả schedule_df (kết quả gốc từ AI) và availability_lookup_df
             # Hàm display_editable_schedule_with_dropdowns sẽ cập nhật st.session_state.edited_schedule_table
             # nếu có sự thay đổi từ người dùng thông qua st.session_state.current_schedule_selections
             current_edited_df = display_editable_schedule_with_dropdowns(
                 st.session_state.schedule_df, # Dữ liệu gốc từ AI để khởi tạo
                 st.session_state.availability_lookup_df
             )
             if current_edited_df is not None:
                 st.session_state.edited_schedule_table = current_edited_df


        st.divider()
        with st.container(border=True):
             st.subheader("📝 Sao Chép Dữ Liệu Lịch")
             copy_text_button = st.button("Tạo văn bản để Copy sang Excel/Sheet", key="generate_copy_text_button", use_container_width=True)
             if copy_text_button:
                  df_to_copy = st.session_state.get('edited_schedule_table', None)
                  if df_to_copy is not None and not df_to_copy.empty:
                       try:
                            copy_string = df_to_copy.to_csv(sep='\t', index=False, header=True)
                            st.session_state.copyable_text = copy_string
                       except Exception as e:
                            st.error(f"Lỗi khi tạo văn bản để copy: {e}")
                            st.session_state.copyable_text = None
                  else:
                       st.warning("Không có dữ liệu lịch đã chỉnh sửa để tạo văn bản hoặc lịch trống.")
                       st.session_state.copyable_text = None

             if st.session_state.copyable_text:
                  st.text_area(
                       "Copy toàn bộ nội dung dưới đây (Ctrl+A, Ctrl+C) và dán vào ô A1 của Excel/Sheet:",
                       st.session_state.copyable_text,
                       height=200,
                       key="copy_text_output"
                  )

        st.divider(); st.subheader("📥 Tải Xuống Lịch (8 Cột - Đã Chỉnh Sửa)")
        col_dl1, col_dl2 = st.columns(2)

        df_to_download_final = st.session_state.get('edited_schedule_table', None)

        if df_to_download_final is not None and not df_to_download_final.empty:
            try:
                csv_8col = df_to_download_final.to_csv(index=False, encoding='utf-8-sig')
                col_dl1.download_button("Tải CSV (Đã sửa)", csv_8col, "edited_schedule_8col.csv", "text/csv", use_container_width=True, key="dl_csv_8col_edit")
            except Exception as e: col_dl1.error(f"Lỗi CSV 8 cột: {e}")
            try:
                buffer_excel_8col = io.BytesIO()
                engine = 'xlsxwriter' if 'xlsxwriter' in sys.modules else 'openpyxl'
                with pd.ExcelWriter(buffer_excel_8col, engine=engine) as writer:
                    df_to_download_final.to_excel(writer, index=False, sheet_name='Edited_Schedule_8Col')
                col_dl2.download_button("Tải Excel (Đã sửa)", buffer_excel_8col.getvalue(), "edited_schedule_8col.xlsx", "application/vnd.ms-excel", use_container_width=True, key="dl_excel_8col_edit")
            except Exception as e: col_dl2.error(f"Lỗi Excel 8 cột: {e}")
        else:
            col_dl1.warning("Không có dữ liệu lịch đã sửa để tải hoặc lịch trống.")
            col_dl2.warning("Không có dữ liệu lịch đã sửa để tải hoặc lịch trống.")


    st.sidebar.divider()
    st.sidebar.markdown("<p class='footer-copyright'>Copyright ©LeQuyPhat</p>", unsafe_allow_html=True)

# --- Entry Point ---
def main():
    """Main function to handle login state."""
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    load_css()
    if not st.session_state.logged_in: login()
    else: main_app()

if __name__ == "__main__":
    main()
