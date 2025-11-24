"""
Authentication API routes.

Provides endpoints for:
- User registration
- User login (token issuance)
- Current user info retrieval
"""

from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from tinybase.auth import (
    CurrentUser,
    DbSession,
    create_auth_token,
    hash_password,
    verify_password,
)
from tinybase.db.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class RegisterRequest(BaseModel):
    """User registration request."""
    
    email: EmailStr = Field(description="User email address")
    password: str = Field(min_length=8, description="Password (min 8 characters)")


class RegisterResponse(BaseModel):
    """User registration response."""
    
    id: str = Field(description="User ID")
    email: str = Field(description="User email address")
    message: str = Field(default="User registered successfully")


class LoginRequest(BaseModel):
    """User login request."""
    
    email: EmailStr = Field(description="User email address")
    password: str = Field(description="User password")


class LoginResponse(BaseModel):
    """User login response with token."""
    
    token: str = Field(description="Bearer token for API authentication")
    token_type: str = Field(default="bearer")
    user_id: str = Field(description="Authenticated user ID")
    email: str = Field(description="Authenticated user email")
    is_admin: bool = Field(description="Whether user has admin privileges")


class UserInfo(BaseModel):
    """Current user information."""
    
    id: str = Field(description="User ID")
    email: str = Field(description="User email address")
    is_admin: bool = Field(description="Whether user has admin privileges")
    created_at: str = Field(description="User creation timestamp")


# =============================================================================
# Routes
# =============================================================================


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password.",
)
def register(request: RegisterRequest, session: DbSession) -> RegisterResponse:
    """
    Register a new user account.
    
    Creates a new user with the provided email and password. The password
    is hashed before storage using bcrypt.
    """
    # Check if email already exists
    existing = session.exec(
        select(User).where(User.email == request.email)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create new user
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return RegisterResponse(
        id=str(user.id),
        email=user.email,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login and get access token",
    description="Authenticate with email and password to receive a bearer token.",
)
def login(request: LoginRequest, session: DbSession) -> LoginResponse:
    """
    Authenticate user and issue access token.
    
    Verifies the provided email and password, then creates and returns
    a new bearer token for API authentication.
    """
    # Find user by email
    user = session.exec(
        select(User).where(User.email == request.email)
    ).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Create and return token
    auth_token = create_auth_token(session, user)
    
    return LoginResponse(
        token=auth_token.token,
        user_id=str(user.id),
        email=user.email,
        is_admin=user.is_admin,
    )


@router.get(
    "/me",
    response_model=UserInfo,
    summary="Get current user info",
    description="Retrieve information about the currently authenticated user.",
)
def get_me(user: CurrentUser) -> UserInfo:
    """
    Get information about the current authenticated user.
    
    Requires a valid bearer token in the Authorization header.
    """
    return UserInfo(
        id=str(user.id),
        email=user.email,
        is_admin=user.is_admin,
        created_at=user.created_at.isoformat(),
    )

