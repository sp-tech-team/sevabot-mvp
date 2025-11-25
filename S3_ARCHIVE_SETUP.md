# S3 Conversation Archive Setup Guide

## Overview

This feature automatically archives deleted conversations to AWS S3 before removing them from Supabase, helping you save database storage costs while maintaining a backup of chat history.

## Why Use S3 for Archival?

### Supabase Storage Limitations
- **Free Tier**: 500MB database storage
- **Paid Tiers**: More expensive for large data storage
- **Problem**: Chat conversations with many messages quickly consume database storage

### AWS S3 Free Tier Benefits
- **Storage**: 5GB free for 12 months
- **Requests**: 20,000 GET + 2,000 PUT requests/month
- **Cost-Effective**: After free tier, S3 is much cheaper than database storage
- **Scalability**: Unlimited growth potential

### Storage Cost Comparison
| Service | Free Tier | Cost After Free Tier |
|---------|-----------|---------------------|
| Supabase | 500MB | ~$0.125/GB/month |
| AWS S3 | 5GB (12 months) | ~$0.023/GB/month |

**Result**: S3 is ~5x cheaper than database storage for archival data!

---

## Architecture

### How It Works

1. **User deletes conversation** from their profile
2. **Before deletion**, the system:
   - Fetches conversation + all messages from Supabase
   - Creates JSON file with complete conversation data
   - Uploads to S3 at `archived_conversations/{user_email}/{conversation_id}.json`
   - Updates metadata index for quick lookups
3. **After successful archive**, deletes from Supabase database
4. **Storage saved** on Supabase, backup retained in S3

### File Structure in S3

```
s3://your-bucket-name/
└── archived_conversations/
    ├── user_at_example_com/
    │   ├── uuid-conversation-1.json
    │   ├── uuid-conversation-2.json
    │   └── metadata.json
    └── another_user_at_example_com/
        ├── uuid-conversation-3.json
        └── metadata.json
```

### Archived Conversation Format

Each archived conversation is a JSON file containing:

```json
{
  "conversation": {
    "id": "uuid-here",
    "user_id": "user@example.com",
    "title": "Conversation Title",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-16T14:20:00Z"
  },
  "messages": [
    {
      "id": "msg-uuid-1",
      "conversation_id": "uuid-here",
      "role": "user",
      "content": "User's question here",
      "feedback": null,
      "created_at": "2025-01-15T10:30:15Z"
    },
    {
      "id": "msg-uuid-2",
      "conversation_id": "uuid-here",
      "role": "assistant",
      "content": "AI response here",
      "feedback": "positive",
      "created_at": "2025-01-15T10:30:20Z"
    }
  ],
  "archive_metadata": {
    "archived_at": "2025-01-20T09:00:00Z",
    "message_count": 12,
    "user_email": "user@example.com"
  }
}
```

### Metadata Index Format

```json
{
  "user_email": "user@example.com",
  "archived_conversations": [
    {
      "conversation_id": "uuid-here",
      "title": "Conversation Title",
      "created_at": "2025-01-15T10:30:00Z",
      "archived_at": "2025-01-20T09:00:00Z",
      "message_count": 12
    }
  ]
}
```

---

## Setup Instructions

### Step 1: Create AWS Account & S3 Bucket (FREE)

1. **Create AWS Account**: https://aws.amazon.com/free/
   - 12 months free tier (5GB S3 storage)
   - Requires credit card but won't charge for free tier usage

2. **Create S3 Bucket**:
   ```bash
   # Option A: AWS Console (Recommended for beginners)
   # 1. Go to AWS Console > S3
   # 2. Click "Create bucket"
   # 3. Bucket name: "sevabot-documents-prod" (or your choice)
   # 4. Region: ap-south-1 (or nearest to you)
   # 5. Block all public access: YES (keep data private)
   # 6. Create bucket

   # Option B: AWS CLI
   aws s3 mb s3://sevabot-documents-prod --region ap-south-1
   ```

3. **Create IAM User with S3 Access**:
   ```bash
   # AWS Console > IAM > Users > Add User
   # 1. Username: sevabot-s3-user
   # 2. Access type: Programmatic access
   # 3. Permissions: Attach existing policy "AmazonS3FullAccess" (or create custom policy below)
   # 4. Download credentials CSV (contains ACCESS_KEY_ID and SECRET_ACCESS_KEY)
   ```

   **Recommended Custom Policy** (Least Privilege):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:PutObject",
           "s3:GetObject",
           "s3:DeleteObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::sevabot-documents-prod",
           "arn:aws:s3:::sevabot-documents-prod/*"
         ]
       }
     ]
   }
   ```

### Step 2: Configure Environment Variables

Add these to your `.env` file (if not already present):

```bash
# S3 Configuration (REQUIRED for archival)
USE_S3_STORAGE=true
AWS_ACCESS_KEY_ID=your-access-key-here
AWS_SECRET_ACCESS_KEY=your-secret-key-here
AWS_REGION=ap-south-1
S3_BUCKET_NAME=sevabot-documents-prod

# Existing Supabase config (should already be present)
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### Step 3: Install Dependencies

The required dependency `boto3` should already be in `requirements.txt`. If not:

```bash
pip install boto3
```

### Step 4: Test the Setup

```python
# Run this in Python console to test S3 connection
from s3_archive_service import s3_archive_service

# Check if enabled
print(f"S3 Archive Enabled: {s3_archive_service.is_enabled()}")

# Test connection (this will attempt to list objects)
try:
    s3_archive_service.s3_client.head_bucket(Bucket=s3_archive_service.bucket_name)
    print("✅ S3 connection successful!")
except Exception as e:
    print(f"❌ S3 connection failed: {e}")
```

### Step 5: Deploy and Use

1. **Restart your application** to load new environment variables
2. **Delete a conversation** from the UI
3. **Check S3 bucket** for archived conversation:
   ```bash
   # Using AWS CLI
   aws s3 ls s3://sevabot-documents-prod/archived_conversations/ --recursive
   ```

---

## API Usage (Optional)

If you want to programmatically retrieve archived conversations, you can use the FastAPI endpoints.

### Enable API Endpoints

Add to your `main.py` or `app.py`:

```python
from archive_api import archive_router

app.include_router(archive_router)
```

### API Endpoints

1. **Check Archive Status**
   ```bash
   GET /api/archive/status
   ```

2. **List Archived Conversations**
   ```bash
   GET /api/archive/conversations
   ```

3. **Get Specific Archived Conversation**
   ```bash
   GET /api/archive/conversations/{conversation_id}
   ```

4. **Permanently Delete Archived Conversation**
   ```bash
   DELETE /api/archive/conversations/{conversation_id}
   ```

### Example API Usage

```python
import requests

# Assuming you're authenticated
headers = {"Authorization": "Bearer your-token"}

# List archived conversations
response = requests.get("http://localhost:8001/api/archive/conversations", headers=headers)
archived_convs = response.json()
print(f"Found {len(archived_convs)} archived conversations")

# Get specific conversation
conv_id = "uuid-here"
response = requests.get(f"http://localhost:8001/api/archive/conversations/{conv_id}", headers=headers)
conversation_data = response.json()
print(f"Messages: {len(conversation_data['messages'])}")
```

---

## Monitoring & Maintenance

### Check S3 Usage

```bash
# AWS Console > S3 > Bucket > Metrics
# Or use AWS CLI:
aws s3 ls s3://sevabot-documents-prod/archived_conversations/ --recursive --summarize --human-readable
```

### Monitor Costs

- **AWS Billing Dashboard**: https://console.aws.amazon.com/billing/
- **Set up billing alerts**: Get notified if costs exceed free tier
- **Free tier usage**: https://console.aws.amazon.com/billing/home#/freetier

### Storage Estimates

| Conversations | Avg Messages/Conv | Storage per Conv | Total Storage |
|---------------|-------------------|------------------|---------------|
| 100 | 10 | ~10KB | ~1MB |
| 1,000 | 10 | ~10KB | ~10MB |
| 10,000 | 10 | ~10KB | ~100MB |
| 50,000 | 10 | ~10KB | ~500MB |

**Conclusion**: You can archive ~50,000 conversations before reaching the 5GB free tier limit!

---

## Troubleshooting

### Issue: "S3 archival disabled"

**Solution**: Check your `.env` file:
- Ensure `USE_S3_STORAGE=true`
- Verify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set
- Restart application after changing `.env`

### Issue: "Access Denied" when archiving

**Possible causes**:
1. IAM user doesn't have S3 permissions
2. Bucket name is incorrect
3. Credentials are invalid

**Solution**:
```bash
# Test AWS credentials
aws sts get-caller-identity

# Test bucket access
aws s3 ls s3://sevabot-documents-prod/
```

### Issue: Archival fails but deletion succeeds

**Impact**: Conversation deleted without backup (data loss)

**Prevention**: The code continues deletion even if archival fails (by design to prevent blocking user actions)

**Solution**: Monitor logs for archival failures and fix S3 issues promptly

### Issue: Can't find archived conversations

**Solution**:
```bash
# Check S3 bucket structure
aws s3 ls s3://sevabot-documents-prod/archived_conversations/ --recursive

# Check specific user's archives
aws s3 ls s3://sevabot-documents-prod/archived_conversations/user_at_example_com/
```

---

## Security Best Practices

1. **Never commit `.env` file** to git (already in `.gitignore`)
2. **Use IAM roles** instead of access keys when deploying on AWS EC2
3. **Enable S3 bucket encryption** (AWS Console > S3 > Bucket > Properties > Default encryption)
4. **Enable versioning** for accidental deletion protection
5. **Set lifecycle policies** to move old archives to Glacier for even cheaper storage

### Example: Enable S3 Encryption

```bash
aws s3api put-bucket-encryption \
  --bucket sevabot-documents-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

---

## Advanced: Restore Archived Conversation

If you need to restore an archived conversation back to Supabase:

```python
from s3_archive_service import s3_archive_service
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

# Retrieve from S3
archive_data = s3_archive_service.get_archived_conversation(conversation_id, user_email)

if archive_data:
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    # Restore conversation
    conv = archive_data["conversation"]
    supabase.table("conversations").insert(conv).execute()

    # Restore messages
    messages = archive_data["messages"]
    supabase.table("messages").insert(messages).execute()

    print(f"✅ Restored conversation {conversation_id}")
```

---

## Cost Optimization Tips

1. **Use S3 Lifecycle Policies**: Automatically move old archives to S3 Glacier (even cheaper)
   ```bash
   # Archives older than 90 days → Glacier (~$0.004/GB/month)
   ```

2. **Compress JSON files**: Use gzip compression before uploading
   ```python
   import gzip
   compressed_data = gzip.compress(json.dumps(archive_data).encode())
   ```

3. **Batch deletions**: If deleting multiple conversations, batch the S3 operations

4. **Monitor free tier usage**: Set up AWS budgets to alert before exceeding free tier

---

## Support

For issues or questions:
1. Check logs for detailed error messages
2. Verify S3 credentials and bucket access
3. Consult AWS S3 documentation: https://docs.aws.amazon.com/s3/
4. Contact your development team

---

## Summary

**What you get:**
- ✅ Automatic backup of deleted conversations to S3
- ✅ Same database schema preserved in JSON format
- ✅ Free for up to 5GB storage (12 months)
- ✅ 5x cheaper than Supabase storage after free tier
- ✅ Easy retrieval via API endpoints
- ✅ Maintains data integrity with metadata indexing

**Setup time:** ~15 minutes

**Monthly cost (after free tier):** ~$0.10 for 5GB storage

**Database storage saved:** Unlimited (as you delete conversations)
