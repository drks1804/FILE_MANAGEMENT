from datetime import datetime, timezone
import numpy as np
from fastapi import UploadFile, BackgroundTasks,HTTPException,status, Response
from sqlalchemy.orm import Session
from magika import Magika
from app.database.models import File, Upload,Sharelink,Vector
from app.service.s3_operations import *
from app.schema.file_schema import UploadInitRequest
from app.service.indexing import background_index_file
from app.service.faiss_index import remove_embeddings
from app.service.s3_client import s3,BUCKET_NAME


m = Magika()


def upload_file_handler(
    upload_data: UploadInitRequest,
    user_id: int,
    db: Session
):
    try:
        # Create a new file record
        new_file = File(
            user_id=user_id,
            file_name=upload_data.file_name,
            file_size=upload_data.file_size,
            file_type="application/octet-stream",
            is_indexed=False,
            is_favorite=False,
            updated_at=datetime.now(timezone.utc),
            folder_id=None
        )

        db.add(new_file)
        db.flush()

        # Start the S3 multipart upload
        multipart_result = start_multipart_upload(
            user_id=user_id,
            file_id=new_file.file_id
        )

        # Create the upload record
        new_upload = Upload(
            user_id=user_id,
            file_id=new_file.file_id,
            upload_status="in_progress",
            uploaded_size=0,
            s3_upload_id=multipart_result["s3_upload_id"]
        )

        db.add(new_upload)
        db.commit()

    except Exception:
        db.rollback()
        raise

    db.refresh(new_file)
    db.refresh(new_upload)

    return {
        "file_id": new_file.file_id,
        "upload_id": new_upload.upload_id,
        "s3_upload_id": new_upload.s3_upload_id,
        "file_name": new_file.file_name,
        "file_size": new_file.file_size,
        "file_type": new_file.file_type,
        "is_indexed": new_file.is_indexed,
        "upload_status": new_upload.upload_status
    }


def upload_part_handler(
    file_id: int,
    part_number: int,
    chunk: UploadFile,
    user_id: int,
    db: Session
):
    file_record = (
        db.query(File)
        .filter(
            File.file_id == file_id,
            File.user_id == user_id
        )
        .first()
    )

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    upload_record = (
        db.query(Upload)
        .filter(
            Upload.file_id == file_id,
            Upload.user_id == user_id,
            Upload.upload_status == "in_progress"
        )
        .first()
    )

    if not upload_record or not upload_record.s3_upload_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active upload session not found"
        )

    s3_key = f"user_{user_id}/file_{file_id}"

    # Read the selected part.
    chunk.file.seek(0)
    chunk_data = chunk.file.read()

    # Check whether the current S3 multipart upload still exists.
    try:
        list_uploaded_parts(
            s3_key=s3_key,
            s3_upload_id=upload_record.s3_upload_id
        )

    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")

        if error_code != "NoSuchUpload":
            raise

        # The old S3 session no longer exists.
        # Start a replacement session.
        multipart_result = start_multipart_upload(
            user_id=user_id,
            file_id=file_id
        )

        upload_record.s3_upload_id = multipart_result["s3_upload_id"]
        upload_record.uploaded_size = 0
        db.commit()
        db.refresh(upload_record)

    # Upload the part using the current S3 session.
    result = upload_multipart_part(
        s3_key=s3_key,
        s3_upload_id=upload_record.s3_upload_id,
        part_number=part_number,
        chunk=chunk_data
    )

    return result

def get_uploaded_parts_handler(
        file_id:int,
        user_id:int,
        db:Session
):
    
    file_record = (
        db.query(File)
        .filter(
            File.file_id == file_id,
            File.user_id == user_id
        )
        .first()
    )

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    upload_record = (
        db.query(Upload)
        .filter(
            Upload.file_id == file_id,
            Upload.user_id == user_id,
            Upload.upload_status == "in_progress"
        )
        .first()
    )

    if not upload_record or not upload_record.s3_upload_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active upload session not found"
        )

    uploaded_parts = list_uploaded_parts(
        s3_key=f"user_{user_id}/file_{file_id}",
        s3_upload_id=upload_record.s3_upload_id
    )

    return {
        "file_id": file_id,
        "upload_id": upload_record.upload_id,
        "uploaded_parts": uploaded_parts
    }  

def get_incomplete_handlers(
        user_id:int,
        db:Session
):

    incomplete_uploads = (
        db.query(Upload,File)
        .join(
            File,
            Upload.file_id == File.file_id
        )
        .filter(
            File.user_id == user_id,
            Upload.upload_status == "in_progress",
            File.user_id == user_id
        )
        .all()
    )

    results = []

    for upload_record,file_record in incomplete_uploads:
        results.append({
            "file_id": file_record.file_id,
            "upload_id": upload_record.upload_id,
            "file_name": file_record.file_name,
            "file_size": file_record.file_size,
            "uploaded_size": upload_record.uploaded_size,
            "upload_status": upload_record.upload_status            
        })

    return results



def complete_upload_handler(
        file_id:int,
        user_id:int,
        backround_tasks:BackgroundTasks,
        db:Session
):

    file_record = (
        db.query(File)
        .filter(
            File.file_id == file_id,
            File.user_id == user_id
        )
        .first()
    )

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    upload_record = (
        db.query(Upload)
        .filter(
            Upload.file_id == file_id,
            Upload.user_id == user_id,
            Upload.upload_status == "in_progress"
        ).first()
    )

    if not upload_record or not upload_record.s3_upload_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active upload session not found"
        )

    upload_parts = list_uploaded_parts(
        s3_key=f"user_{user_id}/file_{file_id}",
        s3_upload_id=upload_record.s3_upload_id
    )

    if not upload_parts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No parts have been uploaded"
        )

    parts = []

    for part in upload_parts:
        parts.append({
            "PartNumber": part.get("PartNumber", part.get("partNumber")),
            "ETag": part["ETag"]
        })

    complete_multipart_upload(
        s3_key=f"user_{user_id}/file_{file_id}",
        s3_upload_id=upload_record.s3_upload_id,
        parts=parts
    )

    file_bytes = get_file_from_s3(
        user_id=user_id,
        file_id=file_id
    )

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Uploaded file could not be retrieved from S3"
        )

    result = m.identify_bytes(file_bytes)

    detected_file_type = result.output.mime_type

    file_record.file_type = detected_file_type

    upload_record.upload_status = "completed"
    upload_record.uploaded_size = file_record.file_size

    db.commit()

    backround_tasks.add_task(
        background_index_file,
        user_id,
        file_record.file_type,
        file_record.file_id
    )

    return{
        "file_id": file_record.file_id,
        "upload_id": upload_record.upload_id,
        "upload_status": upload_record.upload_status,
        "uploaded_size": upload_record.uploaded_size,
        "message": "File uploaded successfully"
    }



def cancel_upload_handler(
    file_id: int,
    user_id: int,
    db: Session
):
    file_record = (
        db.query(File)
        .filter(
            File.file_id == file_id,
            File.user_id == user_id
        )
        .first()
    )

    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    upload_record = (
        db.query(Upload)
        .filter(
            Upload.file_id == file_id,
            Upload.user_id == user_id,
            Upload.upload_status == "in_progress"
        )
        .first()
    )

    if not upload_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active upload session not found"
        )

    s3_key = f"user_{user_id}/file_{file_id}"

    try:
        # Abort the incomplete S3 multipart upload.
        if upload_record.s3_upload_id:
            abort_multipart_upload(
                s3_key=s3_key,
                s3_upload_id=upload_record.s3_upload_id
            )

        # Delete related vector records, if any.
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

            remove_embeddings(vector_ids)

        for vector in vector_rows:
            db.delete(vector)

        db.flush()

        # Delete all upload records associated with this file.
        db.query(Upload).filter(
            Upload.user_id == user_id,
            Upload.file_id == file_id
        ).delete(
            synchronize_session=False
        )

        db.flush()

        # Disable any related share links.
        share_links = (
            db.query(Sharelink)
            .filter(Sharelink.file_id == file_id)
            .all()
        )

        for share_link in share_links:
            share_link.status = False

        db.flush()

        # Delete the parent File record last.
        db.delete(file_record)
        db.commit()

        return {
            "file_id": file_id,
            "message": "Incomplete upload cancelled successfully"
        }

    except Exception:
        db.rollback()
        raise

def get_files_handler(
    user_id: int,
    db: Session
):
    files = (
        db.query(File)
        .filter(File.user_id == user_id)
        .all()
    )

    return files

def get_file_handler(
    file_id: int,
    user_id: int,
    db: Session
):
    file = (
        db.query(File)
        .filter(
            File.file_id == file_id,
            File.user_id == user_id
        )
        .first()
    )

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    return file

def view_file_handler(
    file_id: int,
    user_id: int,
    db: Session
):
    file = (
        db.query(File)
        .filter(
            File.file_id == file_id,
            File.user_id == user_id
        )
        .first()
    )

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )


    file_bytes = get_file_from_s3(
        user_id=user_id,
        file_id=file.file_id
    )

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in storage"
        )


    media_type = file.file_type

    if not media_type:
        media_type = "application/octet-stream"

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{file.file_name}"'
        }
    )

def download_file_handler(
    file_id: int,
    user_id: int,
    db: Session
):
    file = (
        db.query(File)
        .filter(
            File.file_id == file_id,
            File.user_id == user_id
        )
        .first()
    )

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )


    file_bytes = get_file_from_s3(
        user_id=user_id,
        file_id=file.file_id
    )

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in storage"
        )


    media_type = file.file_type

    if not media_type:
        media_type = "application/octet-stream"

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file.file_name}"'
        }
    )

def favorite_file_handler(
    file_id: int,
    user_id: int,
    db: Session
):
    file = (
        db.query(File)
        .filter(
            File.file_id == file_id,
            File.user_id == user_id
        )
        .first()
    )

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    file.is_favorite = not file.is_favorite

    db.commit()
    db.refresh(file)

    return {
        "file_id": file.file_id,
        "file_name": file.file_name,
        "is_favorite": file.is_favorite
    }

def rename_file_handler(
    file_id: int,
    new_file_name: str,
    user_id: int,
    db: Session
):
    file = (
        db.query(File)
        .filter(
            File.file_id == file_id,
            File.user_id == user_id
        )
        .first()
    )

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    file.file_name = new_file_name

    db.commit()

    return {
        "message": "File renamed successfully"
    }

def delete_file_handler(
    file_id: int,
    user_id: int,
    db: Session
):
    file = (
        db.query(File)
        .filter(
            File.file_id == file_id,
            File.user_id == user_id
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