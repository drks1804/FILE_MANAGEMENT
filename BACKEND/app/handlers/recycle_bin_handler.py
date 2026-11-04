from sqlalchemy.orm import Session
from app.database.models import File, Upload,Sharelink,Vector
from fastapi import HTTPException,status
from app.service.s3_client import s3,BUCKET_NAME
from app.service.faiss_index import remove_embeddings
import numpy as np


def get_recycle_bin_files_handler(
    user_id: int,
    db: Session
):
    files = (
        db.query(File)
        .filter(
            File.user_id == user_id,
            File.deleted_at.isnot(None)
        )
        .all()
    )

    result = []

    for file in files:
        result.append({
            "file_id": file.file_id,
            "file_name": file.file_name,
            "file_size": file.file_size,
            "file_type": file.file_type,
            "deleted_at": file.deleted_at
        })

    return result

def restore_file_handler(
    file_id: int,
    user_id: int,
    db: Session
):
    file = (
        db.query(File)
        .filter(
            File.file_id == file_id,
            File.user_id == user_id,
            File.deleted_at.isnot(None)
        )
        .first()
    )

    if not file:
        return {
            "message": "File not found in the recycle bin"
        }

    file.deleted_at = None
    db.commit()

    return {
        "message": "File restored successfully"
    }

def permanently_delete_file_handler(
        file_id: int,
        user_id: int,
        db: Session
):

    file = (
        db.query(File)
        .filter(
            File.file_id == file_id,
            File.user_id == user_id,
            File.deleted_at.isnot(None)
        )
        .first()
    )

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    s3_key = f"user_{user_id}/file_{file_id}"
    

    try:
        s3.delete_object(
            Bucket=BUCKET_NAME,
            Key=s3_key
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"failed to delete file from storage: {str(e)}"
        )

    vector_rows = (
        db.query(Vector)
        .filter(Vector.file_id == file_id)
        .all()
    )

    vector_ids = []

    for vector in vector_rows:
        vector_ids.append(vector.vector_id)

    if vector_ids:
        vector_ids = np.array(
            vector_ids,
            dtype="int64"
        )

        try:
            remove_embeddings(vector_ids)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"failed to remove embeddings from from FAISS: {str(e)}"
            )

    for vector in vector_rows:
        db.delete(vector)

    db.flush()

    db.query(Upload).filter(
        Upload.user_id == user_id,
        Upload.file_id == file.file_id
    ).delete(
        synchronize_session=False
    )

    db.flush()

    share_links = (
        db.query(Sharelink)
        .filter(Sharelink.file_id == file_id)
        .all()
    )

    for share_link in share_links:
        share_link.status = False

    db.flush()

    db.delete(file)

    db.commit()

    return {
        "message": "File deleted successfully"
    }