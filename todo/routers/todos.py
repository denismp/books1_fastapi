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
from .auth import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/todos", tags=["todos"])

# one-time template setup (runtime safe)
HERE = Path(__file__).parent.parent
from fastapi.templating import (
    Jinja2Templates,
)  # top‐level import is fine, needs jinja2 installed

templates = Jinja2Templates(directory=str(HERE / "templates"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dep = Annotated[Session, Depends(get_db)]


def redirect_to_login():
    r = RedirectResponse("/auth/login-page", status_code=status.HTTP_302_FOUND)
    r.delete_cookie("access_token")
    return r


def get_user_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "username": payload["sub"],
            "id": payload["id"],
            "user_role": payload["role"],
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


class TodoRequest(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=3, max_length=100)
    priority: int = Field(gt=0, lt=6)
    complete: bool


# ─────────────────────────────────────────────────────────────
# Page Routes
# ─────────────────────────────────────────────────────────────
@router.get("/todo-page", response_class=HTMLResponse)
async def render_todo_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = get_user_from_cookie(request)
    except HTTPException:
        return redirect_to_login()

    todos_list = db.query(Todos).filter(Todos.owner_id == user["id"]).all()
    return templates.TemplateResponse(
        "todo.html", {"request": request, "todos": todos_list, "user": user}
    )


@router.get("/add-todo-page", response_class=HTMLResponse)
async def render_add_todo_page(request: Request):
    try:
        user = get_user_from_cookie(request)
    except HTTPException:
        return redirect_to_login()

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

    return templates.TemplateResponse(
        "edit-todo.html", {"request": request, "todo": todo, "user": user}
    )


# ─────────────────────────────────────────────────────────────
# JSON API Endpoints
# ─────────────────────────────────────────────────────────────
@router.get("/", status_code=status.HTTP_200_OK)
async def read_all(
    user: dict = Depends(get_user_from_cookie), db: Session = Depends(get_db)
):
    return db.query(Todos).filter(Todos.owner_id == user["id"]).all()


@router.get("/todo/{todo_id}", status_code=status.HTTP_200_OK)
async def read_todo(
    todo_id: int,
    user: dict = Depends(get_user_from_cookie),
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
    user: dict = Depends(get_user_from_cookie),
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
    user: dict = Depends(get_user_from_cookie),
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
    for attr, val in todo_request.model_dump().items():
        setattr(todo, attr, val)
    db.commit()


@router.delete("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    todo_id: int,
    user: dict = Depends(get_user_from_cookie),
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
