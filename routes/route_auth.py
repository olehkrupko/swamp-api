import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from models.model_users import User
from responses.PrettyJsonResponse import PrettyJsonResponse


router = APIRouter(
    prefix="/auth",
)


# curl -F username=XXXX -F password=XXXX "http://localhost:34001/auth/login/"
@router.post("/login/", response_class=PrettyJsonResponse)
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    auth = User.authenticate_user(username=form_data.username, password=form_data.password)
    if not auth.get("success", False):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    return {
        "accessToken": await User.generate_token(data={"sub": auth["username"]}, expires_days=7),
    }
