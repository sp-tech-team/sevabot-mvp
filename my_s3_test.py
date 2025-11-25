import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client('s3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

bucket_name = 'sevabot-chat-backup'

# Check if bucket exists and who owns it
try:
    location = s3.get_bucket_location(Bucket=bucket_name)
    print(f"✅ Bucket exists in region: {location['LocationConstraint']}")
except s3.exceptions.NoSuchBucket:
    print(f"❌ Bucket '{bucket_name}' does not exist")
    print("   You need to create it in AWS Console → S3")
except Exception as e:
    print(f"❌ Error: {e}")
    if '403' in str(e) or 'Forbidden' in str(e):
        print("\n⚠️  The bucket exists but you don't have permission to access it.")
        print("   Either:")
        print("   1. Add S3 permissions to your IAM user (see Step 3)")
        print("   2. The bucket belongs to a different AWS account")