"""
Authentication router.

Handles user authentication for nurse login.
Uses Supabase Auth or custom JWT-based authentication.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from models.schemas import UserCreate, UserLogin, UserResponse, TokenResponse
from services import get_supabase_client

router = APIRouter()

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    """
    Register a new user (nurse/admin).
    
    TODO: Implement user registration
    - Hash password
    - Store in Supabase users table
    - Optionally use Supabase Auth
    """
    # TODO: Implement registration logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Registration not implemented yet"
    )


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user and return JWT token.
    
    TODO: Implement login logic
    - Verify credentials against Supabase
    - Generate JWT token
    - Return token with expiry
    """
    # TODO: Implement login logic
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Login not implemented yet"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Get current authenticated user.
    
    TODO: Implement token verification
    - Decode JWT
    - Fetch user from database
    - Return user info
    """
    # TODO: Implement user lookup from token
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User lookup not implemented yet"
    )


@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """
    Logout user (invalidate token).
    
    TODO: Implement token invalidation
    - Add token to blacklist or
    - Use short-lived tokens with refresh mechanism
    """
    return {"message": "Logged out successfully"}


# Helper function to get current user (use as dependency)
async def get_current_user_dependency(token: str = Depends(oauth2_scheme)):
    """
    Dependency to get current authenticated user.
    
    Usage:
        @router.get("/protected")
        async def protected_route(user: UserResponse = Depends(get_current_user_dependency)):
            return {"user": user}
    """
    # TODO: Implement actual token verification
    # For now, return mock user for development
    return {
        "id": "00000000-0000-0000-0000-000000000000",
        "email": "nurse@example.com",
        "full_name": "Test Nurse",
        "role": "nurse"
    }
