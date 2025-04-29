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

HERE = Path(__file__).parent
templates = Jinja2Templates(directory=HERE / "templates")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


@app.get("/", response_class=RedirectResponse)
def root():
    return RedirectResponse(url="/home", status_code=status.HTTP_302_FOUND)


@app.get(
    "/home",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
)
async def read_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/healthy")
def health_check():
    return {"status": "Healthy"}


app.include_router(auth.router)
app.include_router(todos.router)
app.include_router(admin.router)
app.include_router(users.router)
