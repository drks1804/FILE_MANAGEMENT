from fastapi import APIRouter, Depends, UploadFile, status, BackgroundTasks,File
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import User
from app.service.security import get_current_user
from app.schema.file_schema import RenameRequest,UploadInitRequest
from app.handlers.files_handler import(
    upload_file_handler,
    upload_part_handler,
    get_uploaded_parts_handler,
    complete_upload_handler,
    get_files_handler,
    get_file_handler,
    view_file_handler,
    delete_file_handler,
    download_file_handler,
    rename_file_handler,
    favorite_file_handler,
    get_incomplete_handlers,
    cancel_upload_handler
)


router = APIRouter(
    prefix="/files",
    tags=["Files"]
)



@router.post("/upload", status_code=status.HTTP_201_CREATED)
def get_Uploads(
    Upload_data:UploadInitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return upload_file_handler(
        Upload_data,
        current_user.user_id,
        db
    )

@router.post("/{file_id}/parts")
def upload_part(
    file_id: int,
    part_number: int,
    chunk: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    return upload_part_handler(
        file_id,
        part_number,
        chunk,
        current_user.user_id,
        db
    )

@router.get("/{file_id}/parts")
def get_uploaded_parts(
    file_id,
    current_user:User = Depends(get_current_user),
    db:Session = Depends(get_db)
):
    return get_uploaded_parts_handler(
        file_id,
        current_user.user_id,
        db
    )

@router.get("/incomplete")
def incomplete_upload(
    current_user:User = Depends(get_current_user),
    db:Session = Depends(get_db)
):
    return get_incomplete_handlers(
        current_user.user_id,
        db
    )

@router.post("/{file_id}/complete")
def complete_upload(
    file_id:int,
    background_tasks:BackgroundTasks,
    current_user:User = Depends(get_current_user),
    db:Session = Depends(get_db)
):

    return complete_upload_handler(
        file_id=file_id,
        user_id=current_user.user_id,
        db=db,
        backround_tasks=background_tasks
    )

@router.delete("/{file_id}/cancel")
def cancel_upload(
    file_id:int,
    current_user:User = Depends(get_current_user),
    db:Session = Depends(get_db)
):
    return cancel_upload_handler(
        user_id=current_user.user_id,
        file_id=file_id,
        db=db
    )

@router.get("")
def get_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_files_handler(
        current_user.user_id,
        db
    )


@router.get("/{file_id}")
def get_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_file_handler(
        file_id,
        current_user.user_id,
        db
    )


@router.get("/{file_id}/view")
def view_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return view_file_handler(
        file_id,
        current_user.user_id,
        db
    )


@router.get("/{file_id}/download")
def download(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return download_file_handler(
        file_id,
        current_user.user_id,
        db
    )


@router.patch("/{file_id}/favorite")
def favorite_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return favorite_file_handler(
        file_id,
        current_user.user_id,
        db
    )


@router.patch("/{file_id}/rename")
def rename(
    file_id: int,
    request: RenameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return rename_file_handler(
        file_id,
        request.new_file_name,
        current_user.user_id,
        db
    )


@router.delete("/{file_id}/delete")
def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return delete_file_handler(
        file_id,
        current_user.user_id,
        db
    )