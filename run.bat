Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\.venv\Scripts\activate
cd .\house_renter\
streamlit run app.py