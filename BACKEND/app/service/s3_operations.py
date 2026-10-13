from app.service.s3_client import s3,BUCKET_NAME
from botocore.exceptions import ClientError


def start_multipart_upload(
    user_id: int,
    file_id: int
):
    s3_key = f"user_{user_id}/file_{file_id}"

    response = s3.create_multipart_upload(
        Bucket=BUCKET_NAME,
        Key=s3_key
    )

    return {
        "s3_key": s3_key,
        "s3_upload_id": response["UploadId"]
    }


def upload_multipart_part(
    s3_key: str,
    s3_upload_id: str,
    part_number: int,
    chunk: bytes
):
    response = s3.upload_part(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        UploadId=s3_upload_id,
        PartNumber=part_number,
        Body=chunk
    )

    return {
        "part_number": part_number,
        "etag": response["ETag"]
    }


def list_uploaded_parts(
    s3_key: str,
    s3_upload_id: str
):
    response = s3.list_parts(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        UploadId=s3_upload_id
    )

    uploaded_parts = []

    for part in response.get("Parts", []):
        uploaded_parts.append({
            "PartNumber": part["PartNumber"],
            "ETag": part["ETag"],
            "Size": part["Size"]
        })

    return uploaded_parts

def complete_multipart_upload(
    s3_key: str,
    s3_upload_id: str,
    parts: list
):
    response = s3.complete_multipart_upload(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        UploadId=s3_upload_id,
        MultipartUpload={
            "Parts": parts
        }
    )

    return response

def abort_multipart_upload(
    s3_key: str,
    s3_upload_id: str
):
    try:
        response = s3.abort_multipart_upload(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            UploadId=s3_upload_id
        )

        return response

    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        if error_code in [
            "NoSuchUpload",
            "NoSuchKey"
        ]:
            return None

        raise

def upload_to_s3(user_id,file,file_id):
    s3_key = f"user_{user_id}/file_{file_id}"

    try:
        file.file.seek(0)

        s3.upload_fileobj(
            file.file,
            BUCKET_NAME,
            s3_key
        )

        return s3_key

    except ClientError as e:
        raise 

def get_file_from_s3(user_id,file_id):

    s3_key = f"user_{user_id}/file_{file_id}"

    try:
        response = s3.get_object(
            Bucket = BUCKET_NAME,
            Key = s3_key
        )

        return response["Body"].read()

    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        if error_code in ["NoSuchKey","404"]:
            return b""

        raise