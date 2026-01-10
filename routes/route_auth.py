import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from models.model_users import User
from responses.PrettyJsonResponse import PrettyJsonResponse


router = APIRouter(
    prefix="/auth",
)


# curl -F username=XXXX -F password=XXXX "http://localhost:34001/auth/login/"
@router.post("/login/", response_class=PrettyJsonResponse)
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    EXPIRATION_DAYS = 7

    auth = User.authenticate_user(username=form_data.username, password=form_data.password)
    if not auth.get("success", False):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    response.set_cookie(
        key="access_token",
        value=await User.generate_token(username=auth["username"], expires_days=EXPIRATION_DAYS),
        httponly=True,
        # secure=True,    # Ensures the cookie is only sent over HTTPS (highly recommended for production)
        max_age=EXPIRATION_DAYS*24*3600,   # Cookie expiration time in seconds (e.g., 1 hour)
        samesite="Strict", # Helps prevent CSRF attacks
        # domain=None,  # Set to your domain in production
    )
    return {"success": True}


@router.get("/verify/", response_class=PrettyJsonResponse)
async def verify(request: Request):
    token = request.cookies.get("access_token", "")

    if await User.verify_token(token):
        return {"success": True}

    return {"success": False}
