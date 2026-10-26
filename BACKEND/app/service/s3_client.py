import os

import boto3
from dotenv import load_dotenv

load_dotenv()

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

if not S3_BUCKET_NAME:
    raise ValueError("S3_BUCKET_NAME is required")

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
)

BUCKET_NAME = S3_BUCKET_NAME
