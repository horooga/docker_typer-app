from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from decouple import config
from fastapi import FastAPI, Request, Form, Cookie, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, Response
import jwt
import time
import yaml
import time
import random

app = FastAPI()
templates = Jinja2Templates(directory="static/html")
app.mount("/static", StaticFiles(directory="static"))
JWT_SECRET = config("secret")
JWT_ALGORITHM = config("algorithm")
PASSWORD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")

with open("users.yaml", "r") as f:
    try:
        users = yaml.safe_load(f)
    except Exception as e:
        print(e)

with open("stats.yaml", "r") as f:
    try:
        stats = yaml.safe_load(f)
    except Exception as e:
        print(e)
        
with open("questions.yaml", "r") as f:
    try:
        answers = yaml.safe_load(f)
        questions = [i for i in answers]
        questions_amount = len(questions)
    except Exception as e:
        print(e)

def validate(username: str, password: str) -> [str]:
    if not username:
        return ["Password is empty!"]
    if not password:
        return ["Password is empty!"]
    arr = []
    if len(username) > 20:
        arr.append("Username should be shorter then 20 symbols!")
    if len(username) < 5:
        arr.append("Username should be longer then 5 symbols!")
    if len(password) < 8:
        arr.append("Password should be longer then 8 symbols!")
    if not username.isalnum():
        arr.append("Username should contain only letters and numbers")
    return arr


def make_jwt(nickname: str) -> str:
    return jwt.encode({
        "username": nickname,
        "exp": time.time() + 3600,
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_username_from_token(token: str = Cookie(default=None)) -> str | None:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded_token["username"] if decoded_token["exp"] >= time.time() else None
    except:
        return None

@app.get("/")
async def start() -> FileResponse:
    return FileResponse("static/html/start.html")

@app.get("/login")
async def login(request: Request, auth_username = Depends(get_username_from_token)):
    if not auth_username:
        return templates.TemplateResponse("login.html", {"request": request, "feedback": ""})
    return RedirectResponse("/user", status_code = 302)

@app.post("/logout")
async def logout():
    response = RedirectResponse("/login", status_code = 302)
    response.delete_cookie("token")
    return response

@app.get("/register")
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "feedback": ""})

@app.post("/user-login")
async def user_login(request: Request, username: str = Form(), password: str = Form()):
    if username not in users:
        return templates.TemplateResponse("register.html", {"request": request, "feedback": "User is not registered"})
    if PASSWORD_CONTEXT.verify(password, users[username]):
        response = RedirectResponse("/user", status_code = 302)
        response.set_cookie("token", make_jwt(username))
        return response
    return templates.TemplateResponse("login.html", {"request": request, "feedback": "Incorrect password or username"})

@app.post("/user-register")
async def user_register(request: Request, username: str = Form(), password: str = Form()):
    if username in users:
        return templates.TemplateResponse("register.html", {"request": request, "errors": ["User is already registered"]})
    errors = validate(username, password)
    if errors:
        return templates.TemplateResponse("register.html", {"request": request, "errors": errors})
    users[username] = PASSWORD_CONTEXT.hash(password)
    with open("users.yaml", "a") as f:
        try:
            yaml.safe_dump({username: users[username]}, f, default_flow_style = False)
            return templates.TemplateResponse("login.html", {"request": request, "errors": ["You are successfully registered!"]})
        except:
            return templates.TemplateResponse("login.html", {"request": request, "errors": ["Sorry, try again"]})

@app.post("/type")
async def type(
    request: Request,
    question: str = Form(default = None),
    answer: str = Form(default = None),
    start_time: str = Form(default = None),
    auth_username: str = Depends(get_username_from_token),
):
    if not auth_username:
        return RedirectResponse("/login", status_code = 302)
    if start_time:
        return templates.TemplateResponse("type.html", {
            "request": request,
            "question": questions[random.randrange(questions_amount)],
            "res": "skip" if not answer else "true" if answer == answers[question] else "false",
            "feedback": f"Time elapsed: {str(round(time.time() - float(start_time), 3))} seconds" if answer == answers[question] else f"Answer was: {answers[question]}",
            "start_time": str(round(time.time()))
        })
    else:
        return templates.TemplateResponse("first_type.html", {
            "request": request,
            "question": questions[random.randrange(questions_amount)],
            "start_time": str(round(time.time()))
        })

@app.get("/user")
async def get_stats(request: Request, auth_username: str = Depends(get_username_from_token)):
    if not auth_username:
        return RedirectResponse("/login", status_code = 302)
    user_stats = stats[auth_username]
    return templates.TemplateResponse("user.html", {"request": request, "username": auth_username, "stats": user_stats})
