# CNTR_seek

STeps To RUN

1. cd zero shot classification
2. create virtual env using  python -m venv venv
3. activate venv using
     mac : source venv/bin/activate
     windows : venv\Scripts\activate
4. pip install -r requirements.txt
5. Open 2 terminals ...1 for frontend, one for backend
For frontend:
  1. cd frontend
  2. npm install
  3. npm run
For Backend :
  1. cd backend
  2. uvicorn app.main:app --reload  (make sure venv is activated in step 3)
