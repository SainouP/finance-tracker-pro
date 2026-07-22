from datetime import date
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from app.database import get_session
from app.main import app, seed_demo

engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
def override_session():
    with Session(engine) as session: yield session
app.dependency_overrides[get_session]=override_session
client=TestClient(app)

def setup_function():
    SQLModel.metadata.drop_all(engine); SQLModel.metadata.create_all(engine)
    with Session(engine) as session: seed_demo(session)

def token():
    r=client.post("/api/auth/login",json={"email":"demo@finance.com","password":"Demo123"})
    assert r.status_code==200
    return r.json()["access_token"]
def auth(t):return {"Authorization":f"Bearer {t}"}

def test_health(): assert client.get("/health").json()["version"]=="5.0.0"
def test_private_summary(): assert client.get("/api/summary").status_code==401
def test_transaction():
    r=client.post("/api/transactions",json={"transaction_type":"Gasto","category":"Comida","amount":45.5,
      "description":"Almuerzo","payment_method":"Yape","transaction_date":str(date.today())},headers=auth(token()))
    assert r.status_code==201
def test_goal_contribution_changes_balance():
    t=token(); before=client.get("/api/summary",headers=auth(t)).json()["balance"]
    goal=client.post("/api/goals",json={"name":"Viaje","target_amount":1000,"current_amount":0},headers=auth(t)).json()
    r=client.post(f"/api/goals/{goal['id']}/contribute",json={"amount":100},headers=auth(t))
    assert r.status_code==200
    assert client.get("/api/summary",headers=auth(t)).json()["balance"]==before-100
def test_recurring_cannot_be_paid_twice_same_month():
    t=token()
    item=client.post("/api/recurring",json={"name":"Celular","category":"Servicios","amount":80,"due_day":20},headers=auth(t)).json()
    assert client.post(f"/api/recurring/{item['id']}/pay",headers=auth(t)).status_code==201
    assert client.post(f"/api/recurring/{item['id']}/pay",headers=auth(t)).status_code==409
