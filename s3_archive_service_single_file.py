"""
ALTERNATIVE IMPLEMENTATION: Single JSON file per user approach
⚠️ WARNING: This approach has significant drawbacks - see ARCHIVE_APPROACH_COMPARISON.md

This implementation maintains ONE JSON file per user containing ALL archived conversations.

CONS:
- Slow retrieval (must parse entire file)
- Memory intensive (loads all conversations)
- Concurrency issues (race conditions)
- File size grows unbounded
- Risk of total data loss on corruption

USE ONLY IF: You have <100 conversations per user and infrequent access
RECOMMENDED: Use s3_archive_service.py (one file per conversation)
"""

import json
import boto3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from supabase import create_client
import threading

from config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
    S3_BUCKET_NAME,
    USE_S3_STORAGE
)


class S3ArchiveServiceSingleFile:
    """
    Alternative implementation: Single JSON file per user
    ⚠️ NOT RECOMMENDED for production use
    """

    def __init__(self):
        """Initialize S3 archive service"""
        self.enabled = USE_S3_STORAGE and AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY

        # Thread locks for concurrency control (prevents race conditions)
        self._locks = {}
        self._locks_lock = threading.Lock()

        if self.enabled:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                    region_name=AWS_REGION
                )
                self.bucket_name = S3_BUCKET_NAME
                self.archive_prefix = "archived_conversations/"
                print("✅ S3 Archive Service (Single File) initialized")
            except Exception as e:
                print(f"❌ Failed to initialize S3 Archive Service: {e}")
                self.enabled = False
        else:
            print("⚠️  S3 Archive Service disabled")

        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    def is_enabled(self) -> bool:
        """Check if S3 archival is enabled"""
        return self.enabled

    def _get_user_lock(self, user_email: str) -> threading.Lock:
        """Get or create lock for user (prevents concurrent writes to same file)"""
        with self._locks_lock:
            if user_email not in self._locks:
                self._locks[user_email] = threading.Lock()
            return self._locks[user_email]

    def _get_archive_key(self, user_email: str) -> str:
        """Generate S3 key for user's archive file"""
        safe_email = user_email.replace("@", "_at_").replace(".", "_")
        return f"{self.archive_prefix}{safe_email}.json"

    def _load_user_archive(self, user_email: str) -> Dict:
        """
        Load entire user archive from S3
        ⚠️ WARNING: Loads ALL conversations into memory
        """
        s3_key = self._get_archive_key(user_email)

        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            archive = json.loads(response['Body'].read().decode('utf-8'))
            print(f"📥 Loaded archive for {user_email} ({len(archive.get('conversations', []))} conversations)")
            return archive

        except self.s3_client.exceptions.NoSuchKey:
            # No existing archive, create new structure
            return {
                "user_email": user_email,
                "conversations": [],
                "last_updated": datetime.utcnow().isoformat()
            }
        except Exception as e:
            print(f"❌ Error loading user archive: {e}")
            return {
                "user_email": user_email,
                "conversations": [],
                "last_updated": datetime.utcnow().isoformat()
            }

    def _save_user_archive(self, user_email: str, archive: Dict) -> bool:
        """
        Save entire user archive to S3
        ⚠️ WARNING: Rewrites entire file on every change
        """
        s3_key = self._get_archive_key(user_email)

        try:
            archive["last_updated"] = datetime.utcnow().isoformat()

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(archive, indent=2, default=str),
                ContentType='application/json',
                Metadata={
                    'user_email': user_email,
                    'conversation_count': str(len(archive.get('conversations', []))),
                    'last_updated': archive["last_updated"]
                }
            )

            file_size_mb = len(json.dumps(archive)) / (1024 * 1024)
            print(f"📤 Saved archive for {user_email} ({file_size_mb:.2f}MB)")
            return True

        except Exception as e:
            print(f"❌ Error saving user archive: {e}")
            return False

    def fetch_conversation_data(self, conversation_id: str, user_email: str) -> Optional[Dict]:
        """Fetch conversation and all its messages from Supabase"""
        try:
            conv_result = self.supabase.table("conversations")\
                .select("*")\
                .eq("id", conversation_id)\
                .eq("user_id", user_email)\
                .execute()

            if not conv_result.data:
                return None

            conversation = conv_result.data[0]

            msgs_result = self.supabase.table("messages")\
                .select("*")\
                .eq("conversation_id", conversation_id)\
                .order("created_at")\
                .execute()

            messages = msgs_result.data if msgs_result.data else []

            return {
                "conversation": conversation,
                "messages": messages,
                "archive_metadata": {
                    "archived_at": datetime.utcnow().isoformat(),
                    "message_count": len(messages)
                }
            }

        except Exception as e:
            print(f"❌ Error fetching conversation data: {e}")
            return None

    def archive_to_s3(self, conversation_id: str, user_email: str) -> Tuple[bool, str]:
        """
        Archive conversation to S3 (single file approach)
        ⚠️ WARNING: Uses file locking to prevent race conditions
        """
        if not self.enabled:
            return False, "S3 archival is not enabled"

        # Acquire lock for this user to prevent concurrent writes
        lock = self._get_user_lock(user_email)

        try:
            lock.acquire()

            # 1. Fetch conversation data
            archive_data = self.fetch_conversation_data(conversation_id, user_email)
            if not archive_data:
                return False, "Failed to fetch conversation data"

            # 2. Load existing user archive (reads entire file)
            user_archive = self._load_user_archive(user_email)

            # 3. Check if conversation already archived
            existing = [c for c in user_archive['conversations'] if c['conversation']['id'] == conversation_id]
            if existing:
                return True, f"Conversation {conversation_id} already archived"

            # 4. Add new conversation to archive
            user_archive['conversations'].append(archive_data)

            # 5. Save entire archive back to S3 (rewrites entire file)
            if self._save_user_archive(user_email, user_archive):
                return True, f"Successfully archived conversation {conversation_id}"
            else:
                return False, "Failed to save archive"

        except Exception as e:
            error_msg = f"Failed to archive conversation: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

        finally:
            lock.release()

    def get_archived_conversation(self, conversation_id: str, user_email: str) -> Optional[Dict]:
        """
        Retrieve a specific archived conversation
        ⚠️ WARNING: Must load and parse entire file
        """
        if not self.enabled:
            return None

        try:
            # Load entire user archive (slow!)
            user_archive = self._load_user_archive(user_email)

            # Find specific conversation
            for conv_data in user_archive.get('conversations', []):
                if conv_data['conversation']['id'] == conversation_id:
                    print(f"✅ Found archived conversation {conversation_id}")
                    return conv_data

            print(f"❌ Conversation {conversation_id} not found in archive")
            return None

        except Exception as e:
            print(f"❌ Error retrieving archived conversation: {e}")
            return None

    def list_archived_conversations(self, user_email: str) -> List[Dict]:
        """
        List all archived conversations for a user
        ⚠️ WARNING: Loads entire archive into memory
        """
        if not self.enabled:
            return []

        try:
            user_archive = self._load_user_archive(user_email)

            # Build metadata list
            metadata_list = []
            for conv_data in user_archive.get('conversations', []):
                metadata_list.append({
                    "conversation_id": conv_data['conversation']['id'],
                    "title": conv_data['conversation'].get('title', 'Untitled'),
                    "created_at": conv_data['conversation'].get('created_at'),
                    "archived_at": conv_data['archive_metadata']['archived_at'],
                    "message_count": conv_data['archive_metadata']['message_count']
                })

            return metadata_list

        except Exception as e:
            print(f"❌ Error listing archived conversations: {e}")
            return []

    def delete_archived_conversation(self, conversation_id: str, user_email: str) -> Tuple[bool, str]:
        """
        Delete a conversation from archive
        ⚠️ WARNING: Reads entire file, removes one item, rewrites entire file
        """
        if not self.enabled:
            return False, "S3 archival is not enabled"

        lock = self._get_user_lock(user_email)

        try:
            lock.acquire()

            # Load entire archive
            user_archive = self._load_user_archive(user_email)

            # Remove conversation
            original_count = len(user_archive['conversations'])
            user_archive['conversations'] = [
                c for c in user_archive['conversations']
                if c['conversation']['id'] != conversation_id
            ]

            if len(user_archive['conversations']) == original_count:
                return False, "Conversation not found in archive"

            # Save entire archive back (expensive!)
            if self._save_user_archive(user_email, user_archive):
                return True, "Successfully deleted from archive"
            else:
                return False, "Failed to save archive after deletion"

        except Exception as e:
            error_msg = f"Failed to delete archived conversation: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

        finally:
            lock.release()


# Global instance
# ⚠️ To use this implementation instead of the default:
# 1. Comment out the import in chat_service.py
# 2. Import this: from s3_archive_service_single_file import s3_archive_service_single_file as s3_archive_service
s3_archive_service_single_file = S3ArchiveServiceSingleFile()
