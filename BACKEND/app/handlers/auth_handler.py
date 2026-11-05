from fastapi import HTTPException, status
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
from datetime import timedelta
import secrets
from app.database.redis_client import redis_client
from app.database.models import User, RefreshToken
from app.schema.auth_schema import RegisterRequest,LoginRequest,ForgotPasswordRequest,PasswordResetResponse,ResetPasswordRequest,ProfileUpdate
from app.service.security import create_refresh_tokens, hash_password, verify_password,create_access_token
from app.service.email_service import send_email
from app.service.utils import utc_now

load_dotenv()

MAX_LOGIN_ATTEMPTS = 5
LOGIN_COUNTER_TTL = 900
LOGIN_LOCK_TTL = 900


def register_user(request: RegisterRequest, db: Session):

    existing_user = (
        db.query(User)
        .filter(User.email == request.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    if request.password != request.confirm_password:
        raise HTTPException(
            status_code = status.HTTP_406_NOT_ACCEPTABLE,
            detail="Passwords do not match"
        )

    hashed_password = hash_password(request.password)

    new_user = User(
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        password_hashed=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


FAILED_LOGIN_SCRIPT = """
local locked = redis.call('EXISTS', KEYS[2])

if locked == 1 then
    return -1
end

local count = redis.call('INCR', KEYS[1])

redis.call('EXPIRE', KEYS[1], ARGV[1])

if count >= tonumber(ARGV[2]) then
    redis.call('DEL', KEYS[1])
    redis.call('SET', KEYS[2], '1', 'EX', ARGV[3])
    return -2
end

return count
"""


def record_failed_login(email: str):

    normalized_email = email.strip().lower()

    count_key = f"login:{normalized_email}:count"
    locked_key = f"login:{normalized_email}:locked"

    result = redis_client.eval(
        FAILED_LOGIN_SCRIPT,
        2,
        count_key,
        locked_key,
        LOGIN_COUNTER_TTL,
        MAX_LOGIN_ATTEMPTS,
        LOGIN_LOCK_TTL
    )

    return result



def login_user(request: LoginRequest, db: Session):

    normalized_email = request.email.strip().lower()

    count_key = f"login:{normalized_email}:count"
    locked_key = f"login:{normalized_email}:locked"

    # Step 1: Check whether the email is locked
    remaining_ttl = redis_client.ttl(locked_key)

    if remaining_ttl > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many incorrect attempts. Please wait before trying again.",
            headers={"Retry-After": str(remaining_ttl)}
        )

    # Step 2: Find the user
    existing_user = (
        db.query(User)
        .filter(User.email == request.email)
        .first()
    )

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found Register before Login"
        )

    # Step 3: Verify password
    if not verify_password(
        request.password,
        existing_user.password_hashed
    ):
        result = record_failed_login(normalized_email)

        if result == -1 or result == -2:
            remaining_ttl = redis_client.ttl(locked_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many incorrect attempts. Account locked for 15 minutes.",
                headers={"Retry-After": str(remaining_ttl)}
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect Password"
        )

    # Step 4: Correct password - clear failed attempts
    redis_client.delete(count_key)

    # Step 5: Generate access token
    access_token = create_access_token(
        user_id=existing_user.user_id,
        email=existing_user.email
    )

    # Step 6: Generate refresh token
    refresh_token, token_hash = create_refresh_tokens()

    new_refresh_token = RefreshToken(
        user_id=existing_user.user_id,
        token_hash=token_hash,
        expires_at=utc_now() + timedelta(days=7),
        created_at=utc_now()
    )

    db.add(new_refresh_token)
    db.commit()

    return {
        "user": existing_user,
        "access_token": access_token,
        "refresh_token": refresh_token
    }


def forgot_password_user(
    request: ForgotPasswordRequest,
    db: Session
):

    existing_user = (
        db.query(User)
        .filter(User.email == request.email)
        .first()
    )

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=" User not registered "
        )

    token = secrets.token_urlsafe(16)

    user_id = existing_user.user_id

    user_key = f"reset:user:{user_id}"
    token_key = f"reset:{token}"

    old_token = redis_client.get(user_key)

    if old_token:
        redis_client.delete(f"reset:{old_token}")

    redis_client.set(
        user_key,
        token,
        ex = 300
    )

    redis_client.set(
        token_key,user_id,
        ex = 300
    )

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:4200").rstrip("/")

    reset_link = f"{frontend_url}/reset-password?token={token}"

    mail_body = f"""
    <html>
    <body>
        <p>Hello,</p>

        <p>We received a request to reset the password for your
        File Management System account.</p>

        <p>Click the link below to reset your password:</p>

        <p>
        <a href="{reset_link}">Reset Password</a>
        </p>

        <p>This link is temporary and can only be used according to
        its expiry and validity rules.</p>

        <p>If you did not request a password reset, you can ignore
        this email. Your password will remain unchanged.</p>

        <p>Regards,<br>
        File Management System Team</p>
    </body>
    </html>
    """

    send_email(
        to_email=request.email,
        subject="Password Reset Link",
        body=mail_body
    )

    return PasswordResetResponse(
        message=reset_link
    )
    
def reset_password_user(
    request: ResetPasswordRequest,
    db: Session
):

    user_id = redis_client.get(
        f"reset:{request.token}"
    )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reset Link expired"
        )

    user_id = int(user_id)

    user = (
        db.query(User)
        .filter(User.user_id == user_id)
        .with_for_update()
        .first()
    )
    if not user:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    token_user_id = redis_client.get(
        f"reset:{request.token}"
    )

    if not token_user_id:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Reset link expired or already used"
        )

    if int(token_user_id) != user_id:
        db.rollback()
        raise HTTPException (
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        ) 
    new_hash_password = hash_password(
        request.new_password
    )

    user.password_hashed = new_hash_password

    redis_client.delete(
        f"reset:{request.token}"
    )
    redis_client.delete(
        f"reset:user:{user_id}"
    )

    db.commit()

    return PasswordResetResponse(
        message="Password changed successfully"
    )

def validate_reset_token(token:str):

    user_id = redis_client.get(
        f"reset:{token}"
    )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reset link is invalid or expired"
        )

    return PasswordResetResponse(
        message="Reset link is valid"
    )

def get_profile_handler(
    current_user
):

    return {
        "first_name":current_user.first_name,
        "last_name":current_user.last_name,
        "email":current_user.email
    }

def update_profile_handler(
    request: ProfileUpdate,
    current_user: User,
    db: Session
):

    if request.first_name is not None:
        current_user.first_name = request.first_name

    if request.last_name is not None:
        current_user.last_name = request.last_name

    if request.email is not None:

        existing_email_user = (
            db.query(User)
            .filter(
                User.email == request.email,
                User.user_id != current_user.user_id
            )
            .first()
        )

        if existing_email_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        current_user.email = request.email

    db.commit()

    return {
        "message": "Profile updated successfully"
    }