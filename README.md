# Requirements
- Python>=3.12
- Node
- PostgreSQL
- DjVuLibre with `ddjvu` in PATH, optional for DJVU upload conversion

# Install Django and PostgreSQL
Create virtual environment and install python packages:
```
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt`
```

Create *.env*:
```
SECRET_KEY=''
DEBUG=True
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432
SENTIMENT_MODEL_PATH=
```

Then create separate database and user. Add them in *.env*.\
Generate django secret key in terminal and add it in *.env*:
```
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```
Do migration to create tables in database:
```
python manage.py migrate
```
# Install Node
Install node packages:
```
cd frontend
npm install
npm run build
```
# Dev 
Run backend, Django Q and frontend together:
```
python scripts/dev.py
```

Or run them manually in separate terminals:
```
cd backend
python manage.py runserver
python manage.py qcluster

cd frontend
npm run dev
```
