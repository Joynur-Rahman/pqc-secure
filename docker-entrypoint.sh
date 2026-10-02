#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h postgres -U pqc_user -d pqc_secure; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Wait for MinIO to be ready
echo "Waiting for MinIO to be ready..."
until curl -s http://minio:9000/minio/health/live > /dev/null; do
  sleep 1
done
echo "MinIO is ready!"

# Run database migrations (if any exist)
echo "Running database migrations..."
alembic upgrade head || true

# Create MinIO bucket if it doesn't exist
echo "Setting up MinIO bucket..."
python -c "
import boto3
from botocore.config import Config

s3 = boto3.client(
    's3',
    endpoint_url='http://minio:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin123',
    config=Config(signature_version='s3v4')
)

try:
    s3.create_bucket(Bucket='pqc-files')
    print('Bucket created successfully')
except s3.exceptions.BucketAlreadyExists:
    print('Bucket already exists')
except s3.exceptions.BucketAlreadyOwnedByYou:
    print('Bucket already owned by you')
" || echo "Note: MinIO bucket setup skipped (boto3 not available)"

# Start the application
echo "Starting application..."
exec "$@"
