"""
认证 API：注册、登录、当前用户信息与编辑
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError

from app.database import get_db
from app.models.models import User
from app.schemas.schemas import UserCreate, UserLogin, UserUpdate, UserResponse, TokenResponse
from app.core.auth import get_password_hash, verify_password, create_access_token, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_to_response(user: User) -> UserResponse:
    """ORM User 转 UserResponse（created_at 由 schema 的 field_serializer 负责序列化）"""
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=bool(user.is_active),
        created_at=user.created_at,
    )


@router.post("/register", response_model=TokenResponse)
def register(request: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    try:
        if db.query(User).filter(User.email == request.email).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已被注册")
        user = User(
            email=request.email,
            hashed_password=get_password_hash(request.password),
            display_name=request.display_name or request.email.split("@")[0],
            is_active=True,
        )
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已被注册或数据无效")
        except OperationalError as e:
            db.rollback()
            logger.exception("Database error on register: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="数据库暂时不可用，请稍后重试",
            )
        token = create_access_token(user.id)
        return TokenResponse(
            access_token=token,
            user=_user_to_response(user),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Register failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}",
        )


@router.post("/login", response_model=TokenResponse)
def login(request: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已禁用")
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=_user_to_response(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息（需 token）"""
    return _user_to_response(current_user)


@router.put("/me", response_model=UserResponse)
def update_me(
    request: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新当前用户信息（需 token）"""
    if request.display_name is not None:
        current_user.display_name = request.display_name
    if request.password is not None:
        current_user.hashed_password = get_password_hash(request.password)
    db.commit()
    db.refresh(current_user)
    return _user_to_response(current_user)
