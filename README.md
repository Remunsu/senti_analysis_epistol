# Requirements
- Python>=3.12
- Node>=20.19
- PostgreSQL>=13
- DjVuLibre with `ddjvu` in PATH, optional for DJVU upload conversion

# Install Django and PostgreSQL
Create virtual environment and install python packages:
```
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Download local models into the repository-level `models/` directory:
```
cd backend
source venv/bin/activate

python - <<'PY'
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="seara/rubert-base-cased-russian-sentiment",
    local_dir="../models/seara_rubert-base-cased-russian-sentiment",
)

snapshot_download(
    repo_id="urchade/gliner_multi-v2.1",
    local_dir="../models/gliner_multi-v2.1",
)
PY
```

For offline GLiNER usage, save the base tokenizer into the downloaded GLiNER folder:
```
cd backend
source venv/bin/activate

python - <<'PY'
from transformers import AutoTokenizer

AutoTokenizer.from_pretrained("microsoft/mdeberta-v3-base").save_pretrained(
    "../models/gliner_multi-v2.1"
)
PY
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
SENTIMENT_MODEL_PATH=../models/blanchefort-rubert-base-cased-sentiment
RECIPIENT_GLINER_MODEL_PATH=../models/gliner_multi-v2.1
```
If a fine-tuned sentiment model is used, set `SENTIMENT_MODEL_PATH` to that local model folder instead.
`RECIPIENT_GLINER_MODEL_PATH` can point either to the model snapshot itself or to a Hugging Face cache folder like `models--urchade--gliner_multi-v2.1`.
If `RECIPIENT_GLINER_MODEL_PATH` points to a Hugging Face cache folder, the GLiNER snapshot must also contain tokenizer files for fully offline usage. If they are missing, save the base tokenizer into the snapshot, for example from `backend`:
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

# Production draft
The repository contains deploy templates in `deploy/`:
- `nginx.example.conf`
- `sentiment-backend.service.example`
- `sentiment-qcluster.service.example`

Backend production environment example:
```
cp backend/.env.production.example backend/.env
```
Then edit domain, database credentials, model paths and `SECRET_KEY`.
Keep `SECURE_HSTS_SECONDS=0` until HTTPS is fully checked. After that it can be increased deliberately.

Frontend production environment example:
```
cp frontend/.env.production.example frontend/.env.production
```
Then set:
```
VITE_API_BASE_URL=https://example.com/api
```

Build and prepare files:
```
cd backend
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic

cd ../frontend
npm install
npm run build
```

Run Django in production with Gunicorn, not `runserver`:
```
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 300
```

Run Django Q as a separate process:
```
python manage.py qcluster
```

Nginx should serve:
- `frontend/dist` for `/`
- `backend/staticfiles` for `/static/`
- `backend/media` for `/media/`
- proxy `/api/` and `/admin/` to Gunicorn
