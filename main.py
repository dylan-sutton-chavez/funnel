from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import EmailStr
from typing import Optional
from fastapi_throttle import RateLimiter
import resend
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

resend.api_key = os.environ["RESEND_API_KEY"]

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE")

supabase: Client = create_client(url, key)

with open("waitlist_message.txt", "r", encoding="utf-8") as f:
    waitlist_message = f.read()

"""waitlist_noreply recipient(str) → bool/str"""
def waitlist_noreply(recipient: str):
    resend.Emails.send({
        "from": "No Reply <noreply@funnel.rest>",
        "to": [recipient], 
        "subject": "Welcome to Funnel - Email Confirmation",
        "text": waitlist_message
    })
    return True

app = FastAPI()

limiter_index = RateLimiter(times=6, seconds=60)
limiter_waitlist = RateLimiter(times=2, seconds=300)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse, dependencies=[Depends(limiter_index)])
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/waitlist", dependencies=[Depends(limiter_waitlist)])
def add_to_waitlist(email: EmailStr = Form(...), name: Optional[str] = Form(None)):
    try:
        supabase.table("users").insert({"name": name, "email": email}).execute()
        waitlist_noreply(email)
        return {"message": "You have been added to the waitlist.", "status": True}
    except:
        return {"message": "There was an error, please try again later.", "status": False}
    
@app.exception_handler(HTTPException)
async def throttle_handler(request, exc):
    return JSONResponse({"detail": "Too many requests"}, status_code=429)

@app.exception_handler(404)
async def not_found_redirect(request: Request, exc):
    return RedirectResponse(url="/")


# python -m uvicorn main:app --reload

