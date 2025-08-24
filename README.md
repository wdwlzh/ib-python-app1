# IB Python App

Minimal notes to run this project inside the devcontainer.

Quick start (inside the dev container at repo root):

1. Create/activate a virtual environment (optional but recommended):

```sh
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```sh
pip install -r requirements.txt
```

3. Run the Flask app (uses port 8000 by default):

```sh
./.venv/bin/python app.py
```

4. Health check:

```sh
curl http://localhost:8000/health
```

Notes:
- The app expects an IB TWS / Gateway reachable at `host.docker.internal:7498` (default). Adjust `app.py`/`ib_positions.py` if your TWS uses a different host or port.
- If you prefer not to use a venv inside the container, you can install packages directly into the container Python.
