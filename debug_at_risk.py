from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
resp = client.get('/customers/at-risk', headers={'Authorization':'Bearer testtoken:admin@umtech.com'})
print('STATUS', resp.status_code)
print('BODY', resp.text)
