from fastapi import APIRouter, Depends, File, UploadFile
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from core.deps import get_current_user, get_db_dep
from core.models.user import AppUser, UserAvatar
from core.schemas.auth import ChangePasswordIn, ForgotIn, LoginIn, MeOut, ResetIn, TokenOut
from services import auth_service, avatar_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db_dep)):
    return auth_service.login(db, data.email, data.password)


@router.get("/me", response_model=MeOut)
def me(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db_dep)):
    return MeOut(
        id=user.id,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        avatar_url=avatar_service.avatar_url(db, user.id),
    )


@router.post("/me/avatar", response_model=MeOut)
async def upload_avatar(file: UploadFile = File(...), user: AppUser = Depends(get_current_user),
                        db: Session = Depends(get_db_dep)):
    try:
        data = await file.read(avatar_service.MAX_UPLOAD_BYTES + 1)
        await run_in_threadpool(avatar_service.save_avatar, db, user.id, data)
        return await run_in_threadpool(me, user, db)
    finally:
        await file.close()


@router.delete("/me/avatar", response_model=MeOut)
def delete_avatar(user: AppUser = Depends(get_current_user), db: Session = Depends(get_db_dep)):
    avatar = db.get(UserAvatar, user.id)
    if avatar:
        db.delete(avatar)
        db.commit()
    return me(user, db)


@router.post("/change-password")
def change_password(
        data: ChangePasswordIn,
        db: Session = Depends(get_db_dep),
        user: AppUser = Depends(get_current_user),
):
    return auth_service.change_password(db, user, data.old_password, data.new_password)


@router.post("/forgot-password")
def forgot(data: ForgotIn, db: Session = Depends(get_db_dep)):
    return auth_service.request_password_reset(db, data.email)


@router.post("/reset-password")
def reset(data: ResetIn, db: Session = Depends(get_db_dep)):
    return auth_service.reset_password(db, data.token, data.new_password)
