# Simple API JWT Auth application

```bash
pip install uv

uv sync
uv run granian --interface asgi app.main:app
```

## Debug with DAP

```bash
uv run --with debugpy debugpy --listen 127.0.0.1:5678 -m granian --interface asgi app.main:app
```
