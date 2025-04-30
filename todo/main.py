# todo/main.py
from fastapi import FastAPI, Request, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from todo import models
from todo.database import engine
from todo.routers import auth, todos, admin, users

app = FastAPI()
models.Base.metadata.create_all(bind=engine)

# Static files
HERE = Path(__file__).parent
static_path = HERE / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# Templates (deferred for runtime to avoid import issues in tests)
def get_templates():
    return Jinja2Templates(directory=str(HERE / "templates"))


@app.get("/", response_class=HTMLResponse)
def root_redirect(request: Request):
    return RedirectResponse(url="/todos/todo-page", status_code=status.HTTP_302_FOUND)


@app.get("/healthy", response_class=HTMLResponse)
def health_check(request: Request):
    return {"status": "Healthy"}


# Routers
app.include_router(auth.router)
app.include_router(todos.router)
app.include_router(admin.router)
app.include_router(users.router)
