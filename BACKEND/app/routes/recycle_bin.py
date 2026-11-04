from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import User
from app.service.security import get_current_user
from app.handlers.recycle_bin_handler import get_recycle_bin_files_handler, restore_file_handler, permanently_delete_file_handler

router = APIRouter(
    prefix="/recycle-bin",
    tags=["Recycle Bin"]
)


@router.get("")
def get_recycle_bin_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_recycle_bin_files_handler(
        current_user.user_id,
        db
    )

@router.patch("/{file_id}/restore")
def restore_file(
    file_id:int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return restore_file_handler(
        file_id,
        current_user.user_id,
        db
    )

@router.delete("/{file_id}/permanent-delete")
def permanently_delete_file(
    file_id:int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return permanently_delete_file_handler(
        file_id,
        current_user.user_id,
        db
    )