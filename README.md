https://github.com/user-attachments/assets/a10d3a17-07d0-428e-9114-bdac1521524b

# CardioSight Standalone

Standalone local Django + Vue build for the CardioSight service from K-Medai.

## What is included

- CardioSight-only Vue frontend at `/CardioSight`
- Django API backend with CardioSight upload and patient data endpoints
- Local sample patient data under `backend/media/patients_data`
- Model weights under `backend/weights`

Other services from `vueservice_25_06_15`, such as Home, VasoGuide, DNA, Iris, K-Prevail, and Prevail ISHLT, are intentionally excluded.

## Git note

The `.pth`, `.dat`, and `.png` files are marked for Git LFS in `.gitattributes`.
Before pushing this directory to GitHub, install and enable Git LFS:

```sh
git lfs install
git add .gitattributes
git add backend/weights backend/media/patients_data
```

Without Git LFS, GitHub will reject the large model files.

## Environment

Tested with:

- Python `3.11`
- Node.js `24.2.0`
- npm `11.3.0`

Version hints are included in `.python-version` and `.nvmrc`.

Python setup:

```sh
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Frontend setup:

```sh
cd frontend
npm ci
```

If you need CPU-only PyTorch wheels, install PyTorch first using the official CPU index, then install the remaining requirements:

```sh
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.6.0 torchvision==0.21.0
pip install -r requirements.txt
```

## Run locally

Terminal 1:

```sh
./scripts/start_backend.sh
```

Terminal 2:

```sh
./scripts/start_frontend.sh
```

Open:

```text
http://localhost:8080/CardioSight
```

The Vite dev server proxies API and media requests to Django on port `8000`.

## API paths

The frontend uses the same CardioSight paths as the deployed service:

- `GET /cardiosight/patients_data/`
- `POST /cardiosight/upload`
- `GET /media/...`

Compatibility aliases are also available for the older `ecg_web` paths:

- `GET /api/patients_data/`
- `POST /api/upload`

## Re-copy weights

If the model files are missing, copy them from the original local source:

```sh
./scripts/prepare_weights.sh
```

Or pass another source root:

```sh
./scripts/prepare_weights.sh "/path/to/medical hack 2025"
```
