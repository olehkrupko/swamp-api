"""Authentication routes for admin login and token verification.

Provides endpoints for admin user login and token-based authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from models.model_users import User
from responses.PrettyJsonResponse import PrettyJsonResponse


router = APIRouter(
    prefix="/auth",
)


# curl -F username=XXXX -F password=XXXX "http://localhost:34001/auth/login/"
@router.post("/login/", response_class=PrettyJsonResponse)
async def login(
    response: Response, form_data: OAuth2PasswordRequestForm = Depends()
) -> dict[str, bool]:
    """Admin user login endpoint.

    Authenticates user credentials and sets an HTTP-only authentication cookie.

    Args:
        response: FastAPI response object to set cookies.
        form_data: Username and password from form submission.

    Returns:
        dict: {'success': True} on successful login.

    Raises:
        HTTPException: 401 if credentials are invalid.
    """
    EXPIRATION_DAYS = 7

    auth = User.authenticate_user(
        username=form_data.username,
        password=form_data.password,
    )
    if not auth.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    response.set_cookie(
        key="access_token",
        value=await User.generate_token(
            username=auth["username"],
            expires_days=EXPIRATION_DAYS,
        ),
        httponly=True,
        # secure=True,    # only HTTPS
        max_age=EXPIRATION_DAYS * 24 * 3600,
        samesite="Strict",  # Helps prevent CSRF attacks
        # domain=None,  # Set to your domain in production
    )
    return {"success": True}


@router.get(
    "/verify/",
    response_class=PrettyJsonResponse,
    dependencies=[Depends(User.admin_only)],
)
async def verify() -> dict[str, object]:
    """Verify admin authentication token.

    Checks that the request has a valid authentication token.
    This is a protected endpoint requiring valid admin credentials.

    Returns:
        dict: {'success': True, 'description': 'Admin access confirmed'}

    Raises:
        HTTPException: 401 or 403 if not authenticated.
    """
    return {"success": True, "description": "Admin access confirmed"}
