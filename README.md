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
RECIPIENT_GLINER_MODEL_PATH=
```
`RECIPIENT_GLINER_MODEL_PATH` can point either to the model snapshot itself or to a Hugging Face cache folder like `models--urchade--gliner_multi-v2.1`.
For fully offline GLiNER usage, the GLiNER snapshot must also contain tokenizer files. If they are missing, save the base tokenizer into the snapshot, for example from `backend`:
```
python - <<'PY'
from pathlib import Path
from transformers import AutoTokenizer

root = Path("../models/models--urchade--gliner_multi-v2.1").resolve()
snapshot = root / "snapshots" / (root / "refs" / "main").read_text().strip()
AutoTokenizer.from_pretrained("microsoft/mdeberta-v3-base").save_pretrained(snapshot)
PY
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
