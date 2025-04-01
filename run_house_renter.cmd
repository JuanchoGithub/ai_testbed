cd house_renter
powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process"
call .venv\Scripts\activate
call streamlit run app.py
cmd /k
