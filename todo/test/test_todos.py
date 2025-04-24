# todo/test/test_todos.py
import pytest
from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ──────────────────────────────────────────────────────────────────────────────
# Build an isolated test engine / SessionLocal
# ──────────────────────────────────────────────────────────────────────────────
TEST_ENGINE = create_engine(
    "sqlite:///./testdb.db",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,              # single connection for whole test run
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

# ──────────────────────────────────────────────────────────────────────────────
# Patch todo.database *before* FastAPI and routers import it
# ──────────────────────────────────────────────────────────────────────────────
import todo.database as _db                              # noqa: E402  (import after TEST_ENGINE)
_db.engine = TEST_ENGINE
_db.SessionLocal = TestingSessionLocal
_db.Base.metadata.create_all(bind=TEST_ENGINE)           # ensure tables

# Now that the database module is patched, import the rest of the app
from todo.main import app                                # noqa: E402 This imports all the routers from main.py
from todo.routers.todos import get_db, get_current_user  # noqa: E402
from todo.models import Todos                            # noqa: E402


# ──────────────────────────────────────────────────────────────────────────────
# Dependency overrides
# ──────────────────────────────────────────────────────────────────────────────
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    return {"username": "denis", "id": 1, "user_role": "admin"}


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)


# ──────────────────────────────────────────────────────────────────────────────
# Fixture: start every test with a clean table and one known row
# ──────────────────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def test_todo():
    with TEST_ENGINE.connect() as conn:
        conn.execute(text("DELETE FROM todos;"))
        conn.commit()

    db = TestingSessionLocal()
    todo = Todos(
        title="Learn to code!",
        description="Need to learn everyday!",
        priority=5,
        complete=False,
        owner_id=1,
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)
    yield todo
    db.close()


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────
def test_read_all_authenticated(test_todo: Todos):
    response = client.get("/admin/todo")       # adjust if your path differs
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 1
    assert data[0] == {
        "id": test_todo.id,
        "title": "Learn to code!",
        "description": "Need to learn everyday!",
        "priority": 5,
        "complete": False,
        "owner_id": 1,
    }


def test_read_one_authenticated(test_todo: Todos):
    response = client.get(f"/admin/todo/{test_todo.id}")       # adjust if your path differs
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    # assert len(data) == 1
    assert data == {
        "id": test_todo.id,
        "title": "Learn to code!",
        "description": "Need to learn everyday!",
        "priority": 5,
        "complete": False,
        "owner_id": 1,
    }


def test_read_one_authenticated_not_found():
    response = client.get("/admin/todo/999")
    assert response.status_code == 404
    assert response.json() == {'detail': 'Todo not found.'}


def test_create_todo(test_todo: Todos):
    request_data = {
        "title": "New Todo!",
        "description": "New todo description",
        "priority": 5,
        "complete": False,
    }

    response = client.post("/todo/", json=request_data)
    assert response.status_code == 201

    db = TestingSessionLocal()
    model = db.query(Todos).filter(Todos.id == 2).first()
    assert model.title == request_data.get("title")
    assert model.description == request_data.get("description")
    assert model.priority == request_data.get("priority")
    assert model.complete == request_data.get("complete")


def test_update_todo(test_todo: Todos):
    request_data = {
        "title": "Change the title of the todo already saved!",
        "description": "Need to learn everyday!",
        "priority": 5,
        "complete": False,
    }

    response = client.put("/todo/1", json=request_data)
    assert response.status_code == 204
    db = TestingSessionLocal()
    model = db.query(Todos).filter(Todos.id == 1).first()
    assert model.title == "Change the title of the todo already saved!"


def test_update_todo_not_found(test_todo: Todos):
    request_data = {
        "title": "Change the title of the todo already saved!",
        "description": "Need to learn everyday!",
        "priority": 5,
        "complete": False,
    }

    response = client.put("/todo/999", json=request_data)
    assert response.status_code == 404
    assert response.json() == {"detail": "Todo not found."}


def test_delete_todo(test_todo: Todos):
    response = client.delete('/todo/1')
    assert response.status_code == 204
    db = TestingSessionLocal()
    model = db.query(Todos).filter(Todos.id == 1).first()
    assert model is None


def test_delete_todo_not_found():
    response = client.delete('/todo/999')
    assert response.status_code == 404
    assert response.json() == {'detail': 'Todo not found.'}
