# todo/test/test_todos.py
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine, text
from fastapi.testclient import TestClient
import pytest
from todo.models import Todos, Users
from todo.routers.auth import bcrypt_context

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
from todo.main import app                                # noqa: E402 noqa: F811 This imports all the routers from main.py


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    return {'username': 'codingwithrobytest', 'id': 1, 'user_role': 'admin'}


client = TestClient(app)


@pytest.fixture
def test_todo():
    todo = Todos(
        title="Learn to code!",
        description="Need to learn everyday!",
        priority=5,
        complete=False,
        owner_id=1,
    )

    db = TestingSessionLocal()
    db.add(todo)
    db.commit()
    yield todo
    with TEST_ENGINE.connect() as connection:
        connection.execute(text("DELETE FROM todos;"))
        connection.commit()


@pytest.fixture
def test_user():
    user = Users(
        username="codingwithrobytest",
        email="codingwithrobytest@email.com",
        first_name="Eric",
        last_name="Roby",
        hashed_password=bcrypt_context.hash("testpassword"),
        role="admin",
        phone_number="(111)-111-1111"
    )
    db = TestingSessionLocal()
    db.add(user)
    db.commit()
    yield user
    with TEST_ENGINE.connect() as connection:
        connection.execute(text("DELETE FROM users;"))
        connection.commit()
