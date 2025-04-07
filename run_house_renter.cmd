powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process"
call .venv\Scripts\activate
cd .\house_renter
call streamlit run app.py
cmd /k
