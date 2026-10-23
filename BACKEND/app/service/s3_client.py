import os

import boto3
from dotenv import load_dotenv

load_dotenv()

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

if not S3_BUCKET_NAME:
    raise ValueError("S3_BUCKET_NAME is required")

if not S3_ENDPOINT:
    raise ValueError("S3_ENDPOINT is required for LocalStack")

s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    region_name=AWS_REGION,
)

BUCKET_NAME = S3_BUCKET_NAME
