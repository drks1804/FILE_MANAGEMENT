
import os

import boto3
from dotenv import load_dotenv

load_dotenv()

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_ENDPOINT = os.getenv("S3_ENDPOINT")

if not S3_BUCKET_NAME:
    raise ValueError("S3_BUCKET_NAME is required")

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    endpoint_url=S3_ENDPOINT or None,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

BUCKET_NAME = S3_BUCKET_NAME
