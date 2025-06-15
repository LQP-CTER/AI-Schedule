AI Schedule Manager
AI Schedule Manager is a Streamlit-based web application designed to automate the creation of weekly work schedules for part-time employees. It allows users to paste employee availability data from Excel, processes it using Google's Generative AI (Gemini model), and generates an optimized schedule based on predefined constraints. The application also supports manual editing of the schedule with dropdown menus and allows exporting the results to CSV or Excel formats.

Features
Data Input: Paste employee availability data (tab-separated) from Excel into a text area.
AI-Powered Scheduling: Uses Google's Gemini model to generate an optimized weekly schedule based on employee availability and scheduling constraints.
Editable Schedule: Displays the generated schedule in an interactive table with dropdown menus for manual adjustments, supporting replacement suggestions based on availability.
Export Options: Download the edited schedule as a CSV or Excel file, or copy it as tab-separated text for pasting into Excel/Sheets.
Customizable Constraints: Configure scheduling rules via the sidebar, including shift definitions, maximum shifts per day, rest hours, and preference weights.
User Authentication: Simple login system using credentials stored in Streamlit Secrets or a credentials.yaml file.
Responsive Design: Custom CSS for a polished UI, supporting both light and dark themes.
Prerequisites
Python: Version 3.8 or higher.
Google API Key: Required for accessing Google's Generative AI (Gemini model).
Dependencies: Install required Python packages listed in requirements.txt.
Installation
Clone the Repository:
bash

Collapse

Wrap

Run

Copy
git clone <repository-url>
cd ai-schedule-manager
Set Up a Virtual Environment (recommended):
bash

Collapse

Wrap

Run

Copy
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install Dependencies: Create a requirements.txt file with the following content:
text

Collapse

Wrap

Copy
streamlit
pandas
google-generativeai
pyyaml
xlsxwriter
numpy
Then run:
bash

Collapse

Wrap

Run

Copy
pip install -r requirements.txt
Configure Google API Key:
Add your Google API Key to Streamlit Secrets:
For local development, create a .streamlit/secrets.toml file:
toml

Collapse

Wrap

Copy
GOOGLE_API_KEY = "your-google-api-key"
For Streamlit Community Cloud, add GOOGLE_API_KEY in the app's Secrets settings.
Alternatively, the app checks for a credentials.yaml file for authentication (see below).
Set Up Credentials (Optional): If using a credentials.yaml file for login:
yaml

Collapse

Wrap

Copy
username1: password1
username2: password2
Place this file in the project root directory.
Run the Application:
bash

Collapse

Wrap

Run

Copy
streamlit run app.py
The app will open in your default web browser.
Usage
Login:
Enter your username and password on the login page (configured via secrets.toml or credentials.yaml).
Upon successful login, you’ll be directed to the main application.
Input Data:
Copy a table from Excel containing employee availability data (tab-separated format).
Paste the data into the text area under "Bước 1: Dán Dữ Liệu Đăng Ký".
Expected columns include:
Tên nhân viên (Employee Name)
Đăng kí ca cho tuần (Week start date, e.g., DD/MM/YYYY)
Availability for each day (e.g., bạn có thể làm việc thời gian nào? [Thứ 2] for Monday)
Ghi chú (Notes, optional)
Click "Xử lý dữ liệu" to process the input.
Generate Schedule:
Review the processed data displayed in a table.
Click "Tạo Lịch với AI" to generate a schedule using the Gemini AI model.
The AI considers constraints like:
Shift times (Ca 1: 09:00–15:00, Ca 2: 14:00–20:00).
Staffing needs (2 employees per shift on regular days, 3 on "double days" like 3/3 or 5/5).
Maximum 1 shift per day per employee, 4 shifts per week, and other rules set in the sidebar.
Edit Schedule:
View the generated schedule in an interactive table with dropdown menus for each shift.
Select replacement employees from available options (based on the processed availability data).
Changes are saved in the session state for consistency.
Copy or Download:
Click "Tạo văn bản để Copy sang Excel/Sheet" to generate a tab-separated text version of the edited schedule.
Copy the text and paste it into Excel/Sheets starting at cell A1.
Download the edited schedule as a CSV or Excel file using the provided buttons.
Adjust Constraints:
Use the sidebar to modify scheduling rules, such as minimum rest hours, maximum consecutive workdays, or preference weights for notes.
Example Input Data
text

Collapse

Wrap

Copy
Tên nhân viên:	Đăng kí ca cho tuần:	bạn có thể làm việc thời gian nào? [Thứ 2]	bạn có thể làm việc thời gian nào? [Thứ 3]	...	Ghi chú (nếu có)
NV A	02/06/2025	Ca 1	Nghỉ	...	Muốn làm Ca 1
NV B	02/06/2025	Ca 1, Ca 2	Ca 2	...	Chỉ làm 9h-12h Thứ 2
NV C	02/06/2025	Nghỉ	Ca 1	...	Xin off Thứ 2
Notes
Data Format: Ensure the pasted data is tab-separated (copied directly from Excel). The app supports headers matching the predefined columns or auto-assigns them if headers are missing.
Double Days: Days where the day and month are the same (e.g., 5/5) require 3 employees per shift; other days require 2.
Error Handling: The app provides detailed error messages for issues like missing API keys, invalid data formats, or AI response parsing failures.
Dependencies: Install xlsxwriter for Excel export (pip install xlsxwriter). If unavailable, the app falls back to openpyxl.
Security: Store sensitive data (API keys, credentials) securely in Streamlit Secrets or a credentials.yaml file, and avoid hardcoding.
Troubleshooting
API Key Error: Ensure GOOGLE_API_KEY is correctly set in .streamlit/secrets.toml or the Streamlit Cloud Secrets settings.
Data Parsing Issues: Verify that the pasted data is tab-separated and contains expected columns. Check for extra spaces or inconsistent formats.
AI Response Errors: If the AI fails to generate a schedule, check the prompt (visible in the expander) for issues or ensure a stable internet connection.
Login Failure: Confirm that credentials in secrets.toml or credentials.yaml are correct.
Contributing
Contributions are welcome! Please:

Fork the repository.
Create a feature branch (git checkout -b feature/your-feature).
Commit your changes (git commit -m "Add your feature").
Push to the branch (git push origin feature/your-feature).
Open a Pull Request.
License
Copyright © LeQuyPhat. All rights reserved.
