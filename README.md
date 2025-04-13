# Simple API JWT Auth application

```bash
pip install uv

uv sync

# run with graniar
uv run granian --interface asgi app.main:app

# run with uvicorn
uv run uvicorn --no-access-log app.main:app
```

## Debug with DAP

```bash
uvx debugpy --listen 127.0.0.1:5678 -m granian --interface asgi app.main:app

uv run --with debugpy debugpy --listen 127.0.0.1:5678 -m granian --interface asgi app.main:app
```

## Usage

```bash
# Register
xh -v :8000/v1/auth/register email=idm@example.com password=secret


# Login
xh -v -f :8000/v1/auth/login username=idm@example.com password=secret
set TOKEN $(xh -f :8000/v1/auth/login username=idm@example.com password=secret | jq -r .access_token)

# Get users
xh -v -A bearer -a $TOKEN :8000/v1/users/
```

### With SSL

```bash
# server
uv run uvicorn --no-access-log --ssl-keyfile ssl/localhost.key --ssl-certfile ssl/localhost.pem --ssl-cert-reqs 2 --ssl-ca-certs ssl/root.pem app.main:app

# client
xh -v -f https://localhost:8000/v1/auth/login username=idm@example.com password=secret --verify ssl/root.pem --cert ssl/client.pem --cert-key ssl/client.key
```
