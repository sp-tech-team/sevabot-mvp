#!/usr/bin/env python3
"""
Test script for S3 Archive Service
Run this to verify S3 archival is working correctly
"""

import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from s3_archive_service import s3_archive_service
from supabase_client import get_supabase_client


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def test_s3_connection():
    """Test S3 service initialization"""
    print_header("Test 1: S3 Service Initialization")

    is_enabled = s3_archive_service.is_enabled()
    print(f"S3 Archive Enabled: {'✅ YES' if is_enabled else '❌ NO'}")

    if is_enabled:
        print(f"Bucket Name: {s3_archive_service.bucket_name}")
        print(f"Archive Prefix: {s3_archive_service.archive_prefix}")

        # Test bucket access
        try:
            s3_archive_service.s3_client.head_bucket(Bucket=s3_archive_service.bucket_name)
            print("✅ S3 bucket connection successful!")
            return True
        except Exception as e:
            print(f"❌ S3 bucket connection failed: {e}")
            return False
    else:
        print("⚠️  S3 archival is disabled. Check your environment variables:")
        print("   - USE_S3_STORAGE=true")
        print("   - AWS_ACCESS_KEY_ID=your-key")
        print("   - AWS_SECRET_ACCESS_KEY=your-secret")
        return False


def test_list_conversations():
    """Test listing conversations from Supabase"""
    print_header("Test 2: List Conversations from Supabase")

    try:
        supabase = get_supabase_client(use_service_role=True)

        # Get recent conversations
        result = supabase.table("conversations")\
            .select("id, user_id, title, created_at")\
            .order("created_at", desc=True)\
            .limit(5)\
            .execute()

        if result.data and len(result.data) > 0:
            print(f"✅ Found {len(result.data)} recent conversations:")
            for i, conv in enumerate(result.data, 1):
                print(f"\n{i}. {conv['title']}")
                print(f"   ID: {conv['id']}")
                print(f"   User: {conv['user_id']}")
                print(f"   Created: {conv['created_at']}")
            return result.data
        else:
            print("⚠️  No conversations found in database")
            return []

    except Exception as e:
        print(f"❌ Error listing conversations: {e}")
        return []


def test_archive_conversation(conversation_id: str, user_email: str):
    """Test archiving a specific conversation"""
    print_header(f"Test 3: Archive Conversation {conversation_id[:8]}...")

    if not s3_archive_service.is_enabled():
        print("❌ S3 archival is disabled, cannot test archiving")
        return False

    try:
        # Test fetching conversation data
        print("\n1. Fetching conversation data from Supabase...")
        archive_data = s3_archive_service.fetch_conversation_data(conversation_id, user_email)

        if not archive_data:
            print("❌ Failed to fetch conversation data")
            return False

        print(f"✅ Fetched conversation: {archive_data['conversation']['title']}")
        print(f"   Messages: {len(archive_data['messages'])}")

        # Test archiving to S3
        print("\n2. Archiving to S3...")
        success, message = s3_archive_service.archive_to_s3(conversation_id, user_email)

        if success:
            print(f"✅ {message}")
            return True
        else:
            print(f"❌ {message}")
            return False

    except Exception as e:
        print(f"❌ Error during archival test: {e}")
        return False


def test_retrieve_archived(conversation_id: str, user_email: str):
    """Test retrieving an archived conversation"""
    print_header(f"Test 4: Retrieve Archived Conversation {conversation_id[:8]}...")

    if not s3_archive_service.is_enabled():
        print("❌ S3 archival is disabled, cannot test retrieval")
        return False

    try:
        archive_data = s3_archive_service.get_archived_conversation(conversation_id, user_email)

        if archive_data:
            print("✅ Successfully retrieved archived conversation!")
            print(f"\nConversation: {archive_data['conversation']['title']}")
            print(f"Messages: {len(archive_data['messages'])}")
            print(f"Archived at: {archive_data['archive_metadata']['archived_at']}")

            # Show first 2 messages
            if archive_data['messages']:
                print("\nFirst messages:")
                for msg in archive_data['messages'][:2]:
                    content_preview = msg['content'][:80] + "..." if len(msg['content']) > 80 else msg['content']
                    print(f"  [{msg['role']}]: {content_preview}")

            return True
        else:
            print("❌ Archived conversation not found")
            return False

    except Exception as e:
        print(f"❌ Error retrieving archived conversation: {e}")
        return False


def test_list_archived(user_email: str):
    """Test listing all archived conversations for a user"""
    print_header(f"Test 5: List Archived Conversations for {user_email}")

    if not s3_archive_service.is_enabled():
        print("❌ S3 archival is disabled, cannot test listing")
        return False

    try:
        archived_convs = s3_archive_service.list_archived_conversations(user_email)

        if archived_convs:
            print(f"✅ Found {len(archived_convs)} archived conversations:")
            for i, conv in enumerate(archived_convs[:5], 1):
                print(f"\n{i}. {conv['title']}")
                print(f"   ID: {conv['conversation_id']}")
                print(f"   Messages: {conv['message_count']}")
                print(f"   Archived: {conv['archived_at']}")
            return True
        else:
            print("⚠️  No archived conversations found for this user")
            return False

    except Exception as e:
        print(f"❌ Error listing archived conversations: {e}")
        return False


def main():
    """Run all tests"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║         S3 Archive Service - Test Suite                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Test 1: S3 Connection
    s3_ok = test_s3_connection()

    if not s3_ok:
        print("\n⚠️  S3 is not properly configured. Please check S3_ARCHIVE_SETUP.md")
        return

    # Test 2: List conversations
    conversations = test_list_conversations()

    if not conversations:
        print("\n⚠️  No conversations available to test archival")
        print("Create a conversation in the app first, then run this test again")
        return

    # Ask user which conversation to test with
    print("\n" + "=" * 60)
    print("Select a conversation to test archival (or 'q' to quit):")
    print("=" * 60)

    for i, conv in enumerate(conversations, 1):
        print(f"{i}. {conv['title'][:50]}")

    try:
        choice = input("\nEnter number (1-5) or 'q' to quit: ").strip()

        if choice.lower() == 'q':
            print("\n👋 Test cancelled by user")
            return

        idx = int(choice) - 1
        if idx < 0 or idx >= len(conversations):
            print("❌ Invalid selection")
            return

        selected_conv = conversations[idx]
        conversation_id = selected_conv['id']
        user_email = selected_conv['user_id']

        # Test 3: Archive conversation
        archive_ok = test_archive_conversation(conversation_id, user_email)

        if not archive_ok:
            print("\n❌ Archival test failed")
            return

        # Test 4: Retrieve archived conversation
        retrieve_ok = test_retrieve_archived(conversation_id, user_email)

        # Test 5: List archived conversations
        list_ok = test_list_archived(user_email)

        # Summary
        print_header("Test Summary")
        print(f"✅ S3 Connection: {'PASS' if s3_ok else 'FAIL'}")
        print(f"✅ Archive to S3: {'PASS' if archive_ok else 'FAIL'}")
        print(f"✅ Retrieve from S3: {'PASS' if retrieve_ok else 'FAIL'}")
        print(f"✅ List archived: {'PASS' if list_ok else 'FAIL'}")

        if archive_ok and retrieve_ok and list_ok:
            print("\n🎉 All tests passed! S3 archival is working correctly.")
            print("\n⚠️  Note: The conversation was ARCHIVED but NOT DELETED from Supabase.")
            print("To test full deletion flow, delete a conversation from the UI.")
        else:
            print("\n⚠️  Some tests failed. Check the errors above.")

    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled by user")
    except ValueError:
        print("❌ Invalid input. Please enter a number.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
