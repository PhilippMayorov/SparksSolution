"""
Authentication router.

Handles user authentication for nurse login.
Uses Supabase Auth for authentication and JWT token management.
"""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from gotrue import User as SupabaseUser

from models.schemas import UserCreate, UserResponse, TokenResponse
from services.supabase_client import get_supabase_client

router = APIRouter()

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user_from_token(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Validate Supabase Auth JWT token and get current user.

    Args:
        token: JWT token from Authorization header

    Returns:
        User dict from Supabase Auth

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        db = get_supabase_client()

        # Get user from Supabase Auth using the token
        response = db.client.auth.get_user(token)

        if not response or not response.user:
            raise credentials_exception

        supabase_user = response.user

        # Get additional user profile data from users table if it exists
        user_profile = await db.get_user_by_email(supabase_user.email)

        # Combine Supabase Auth user with profile data
        user_data = {
            "id": supabase_user.id,
            "email": supabase_user.email,
            "role": user_profile.get("role", "nurse") if user_profile else "nurse",
            "first_name": user_profile.get("first_name", "") if user_profile else "",
            "last_name": user_profile.get("last_name", "") if user_profile else "",
            "is_active": user_profile.get("is_active", True) if user_profile else True,
            "created_at": supabase_user.created_at,
            "last_login": user_profile.get("last_login") if user_profile else None
        }

        if not user_data.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        return user_data

    except Exception as e:
        print(f"Error validating token: {e}")
        raise credentials_exception


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    """
    Register a new user (nurse/coordinator/admin).

    Creates user in Supabase Auth and stores profile in users table.
    """
    db = get_supabase_client()

    try:
        # Create user in Supabase Auth
        auth_response = db.client.auth.sign_up({
            "email": user.email,
            "password": user.password,
            "options": {
                "data": {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role.value
                }
            }
        })

        if not auth_response or not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user in authentication system"
            )

        supabase_user = auth_response.user

        # Create user profile in users table
        user_data = {
            "id": supabase_user.id,  # Use the same ID from Supabase Auth
            "email": user.email,
            "role": user.role.value,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": True
        }

        created_user = await db.create_user(user_data)

        if not created_user:
            # User created in auth but profile failed - log warning
            print(f"Warning: User {user.email} created in auth but profile creation failed")

        return {
            "id": supabase_user.id,
            "email": supabase_user.email,
            "role": user.role.value,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": True,
            "created_at": supabase_user.created_at
        }

    except Exception as e:
        error_message = str(e)
        if "already registered" in error_message.lower() or "duplicate" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        print(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {error_message}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user using Supabase Auth and return JWT token.

    Uses OAuth2 password flow (username/password in form data).
    Username field should contain the email address.
    """
    db = get_supabase_client()

    try:
        # Authenticate with Supabase Auth
        auth_response = db.client.auth.sign_in_with_password({
            "email": form_data.username,  # username field contains email
            "password": form_data.password
        })

        if not auth_response or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        session = auth_response.session
        supabase_user = auth_response.user

        # Get user profile from users table
        user_profile = await db.get_user_by_email(supabase_user.email)

        # Check if user is active
        if user_profile and not user_profile.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        # Update last login if profile exists
        if user_profile:
            from uuid import UUID
            await db.update_user_last_login(UUID(user_profile["id"]))

        # Prepare user data
        user_data = {
            "id": supabase_user.id,
            "email": supabase_user.email,
            "role": user_profile.get("role", "nurse") if user_profile else "nurse",
            "first_name": user_profile.get("first_name", "") if user_profile else "",
            "last_name": user_profile.get("last_name", "") if user_profile else "",
            "is_active": user_profile.get("is_active", True) if user_profile else True,
            "created_at": supabase_user.created_at
        }

        # Return Supabase session token
        return {
            "access_token": session.access_token,
            "token_type": "bearer",
            "expires_in": session.expires_in,
            "refresh_token": session.refresh_token,
            "user": user_data
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: dict = Depends(get_current_user_from_token)):
    """
    Get current authenticated user.

    Requires valid JWT token in Authorization header.
    """
    return current_user


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user_from_token)):
    """
    Logout user.

    With JWT tokens, logout is handled client-side by removing the token.
    This endpoint is here for compatibility but doesn't need to do anything.
    """
    return {"message": "Logged out successfully"}


# Helper function for route dependencies
def get_current_active_user(current_user: dict = Depends(get_current_user_from_token)) -> dict:
    """
    Dependency to get current authenticated and active user.

    Usage in protected routes:
        @router.get("/protected")
        async def protected_route(user: dict = Depends(get_current_active_user)):
            return {"user_id": user["id"]}
    """
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user
