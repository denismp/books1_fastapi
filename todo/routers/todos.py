# todo/routers/todos.py
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from ..database import SessionLocal
from ..models import Todos
from .auth import get_current_user, SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/todos", tags=["todos"])

# ──────────────────────────────────────────────────────────────────────────────
# Dependencies
# ──────────────────────────────────────────────────────────────────────────────


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "username": data.get("sub"),
            "id": data.get("id"),
            "user_role": data.get("role"),
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


# Expose get_current_user and get_db for tests and API routes
user_dependency = Annotated[dict, Depends(get_current_user)]
db_dependency = Annotated[Session, Depends(get_db)]


# ──────────────────────────────────────────────────────────────────────────────
# Data models
# ──────────────────────────────────────────────────────────────────────────────
class TodoRequest(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=3, max_length=100)
    priority: int = Field(gt=0, lt=6)
    complete: bool


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def redirect_to_login():
    resp = RedirectResponse("/auth/login-page", status_code=status.HTTP_302_FOUND)
    resp.delete_cookie("access_token")
    return resp


# ──────────────────────────────────────────────────────────────────────────────
# Page Routes (lazy-load Jinja2Templates)
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/todo-page", response_class=HTMLResponse)
async def render_todo_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = get_user_from_cookie(request)
    except HTTPException:
        return redirect_to_login()

    todos_list = db.query(Todos).filter(Todos.owner_id == user["id"]).all()

    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(
        directory=str(Path(__file__).parent.parent / "templates")
    )
    return templates.TemplateResponse(
        "todo.html",
        {"request": request, "todos": todos_list, "user": user},
    )


@router.get("/add-todo-page", response_class=HTMLResponse)
async def render_add_todo_page(request: Request):
    try:
        user = get_user_from_cookie(request)
    except HTTPException:
        return redirect_to_login()

    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(
        directory=str(Path(__file__).parent.parent / "templates")
    )
    return templates.TemplateResponse(
        "add-todo.html", {"request": request, "user": user}
    )


@router.get("/edit-todo-page/{todo_id}", response_class=HTMLResponse)
async def render_edit_todo_page(
    request: Request, todo_id: int, db: Session = Depends(get_db)
):
    try:
        user = get_user_from_cookie(request)
    except HTTPException:
        return redirect_to_login()

    todo = db.query(Todos).filter(Todos.id == todo_id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found.")

    from fastapi.templating import Jinja2Templates

    templates = Jinja2Templates(
        directory=str(Path(__file__).parent.parent / "templates")
    )
    return templates.TemplateResponse(
        "edit-todo.html",
        {"request": request, "todo": todo, "user": user},
    )


# ──────────────────────────────────────────────────────────────────────────────
# JSON API Endpoints
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/", status_code=status.HTTP_200_OK)
async def read_all(
    user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    return db.query(Todos).filter(Todos.owner_id == user["id"]).all()


@router.get("/todo/{todo_id}", status_code=status.HTTP_200_OK)
async def read_todo(
    todo_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = (
        db.query(Todos)
        .filter(Todos.id == todo_id)
        .filter(Todos.owner_id == user["id"])
        .first()
    )
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found.")
    return todo


@router.post("/todo", status_code=status.HTTP_201_CREATED)
async def create_todo(
    todo_request: TodoRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = Todos(**todo_request.model_dump(), owner_id=user["id"])
    db.add(todo)
    db.commit()
    return {"detail": "Todo created."}


@router.put("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(
    todo_id: int,
    todo_request: TodoRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = (
        db.query(Todos)
        .filter(Todos.id == todo_id)
        .filter(Todos.owner_id == user["id"])
        .first()
    )
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found.")
    for k, v in todo_request.model_dump().items():
        setattr(todo, k, v)
    db.commit()


@router.delete("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    todo_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = (
        db.query(Todos)
        .filter(Todos.id == todo_id)
        .filter(Todos.owner_id == user["id"])
        .delete()
    )
    db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Todo not found.")
