#!/usr/bin/env python3
"""
Test the repaired session for page retrieval.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.grok_client import GrokClient
from lib.tools.discuss import DiscussTool
from lib.tools.session import SessionManager


async def test_repaired_session():
    """Test page retrieval for the repaired session."""
    session_id = "8a215ddd-99ae-416c-9e7e-450f02e4667b"

    print("=== Testing Repaired Session Page Retrieval ===")
    print(f"Session ID: {session_id}")

    # Initialize tools
    client = GrokClient()
    session_manager = SessionManager(Path("./sessions"))
    tool = DiscussTool(client, session_manager)

    # Test 1: Verify session exists and has correct settings
    print("\n1. Verifying session exists with correct settings...")
    session = session_manager.get_session(session_id)

    if not session:
        print("✗ Session not found")
        return False

    pagination = session.get('pagination', {})
    model = pagination.get('model')
    context_limit = pagination.get('max_total_context_lines')

    print(f"✓ Session found")
    print(f"✓ Model: {model}")
    print(f"✓ Context limit: {context_limit:,} lines")

    if model != "grok-4-fast-reasoning":
        print(f"✗ Expected grok-4-fast-reasoning, got {model}")
        return False

    if context_limit != 1800000:
        print(f"✗ Expected 1,800,000, got {context_limit}")
        return False

    # Test 2: Try to retrieve page 1 (should work)
    print("\n2. Testing page 1 retrieval...")
    try:
        page1_result = await tool.execute(
            session_id=session_id,
            page=1
        )

        if "Model: grok-4-fast-reasoning" in page1_result:
            print("✓ Page 1 shows correct model")
        else:
            print(f"✗ Page 1 model incorrect: {page1_result[:200]}")

        if "1,800,000 lines" in page1_result:
            print("✓ Page 1 shows correct context limit")
        else:
            print(f"✗ Page 1 context limit incorrect")

        print("✓ Page 1 retrieved successfully")

    except Exception as e:
        print(f"✗ Page 1 retrieval failed: {e}")
        return False

    # Test 3: Try to retrieve page 2 (this was failing before)
    print("\n3. Testing page 2 retrieval...")
    try:
        page2_result = await tool.execute(
            session_id=session_id,
            page=2
        )

        if "Model: grok-4-fast-reasoning" in page2_result:
            print("✓ Page 2 shows correct model")
        else:
            print(f"✗ Page 2 model incorrect: {page2_result[:200]}")

        if "1,800,000 lines" in page2_result:
            print("✓ Page 2 shows correct context limit")
        else:
            print(f"✗ Page 2 context limit incorrect")

        if "Page 2 of" in page2_result:
            print("✓ Page 2 retrieved successfully")
            return True
        else:
            print(f"✗ Page 2 format incorrect: {page2_result[:200]}")
            return False

    except Exception as e:
        print(f"✗ Page 2 retrieval failed: {e}")
        # This is the error we were trying to fix
        if "maximum prompt length is 256000" in str(e):
            print("✗ Still getting 256K token limit error - fix incomplete")
        return False


def test_session_schema():
    """Test the session data schema."""
    session_id = "8a215ddd-99ae-416c-9e7e-450f02e4667b"

    print("\n=== Verifying Session Schema ===")

    session_manager = SessionManager(Path("./sessions"))
    session = session_manager.get_session(session_id)

    if not session:
        print("✗ Session not found")
        return False

    # Check required fields
    required_fields = ['id', 'topic', 'created_at', 'updated_at', 'messages', 'status', 'pagination']
    for field in required_fields:
        if field in session:
            print(f"✓ {field}: present")
        else:
            print(f"✗ {field}: missing")

    # Check pagination fields
    pagination = session.get('pagination', {})
    pagination_fields = ['model', 'max_total_context_lines', 'turns_per_page', 'max_turns', 'paginate']
    for field in pagination_fields:
        if field in pagination:
            print(f"✓ pagination.{field}: {pagination[field]}")
        else:
            print(f"✗ pagination.{field}: missing")

    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Repaired Session")
    print("=" * 60)

    # Test schema first
    schema_success = test_session_schema()

    # Test page retrieval
    if schema_success:
        retrieval_success = await test_repaired_session()
    else:
        retrieval_success = False

    print("\n" + "=" * 60)
    if schema_success and retrieval_success:
        print("✓ All tests passed!")
        print("\nSession 8a215ddd-99ae-416c-9e7e-450f02e4667b is now fully functional:")
        print("  • Page 1 retrieval: ✓")
        print("  • Page 2 retrieval: ✓")
        print("  • Model: grok-4-fast-reasoning")
        print("  • Context: 1,800,000 lines")
    else:
        print("✗ Some tests failed!")
    print("=" * 60)

    return 0 if (schema_success and retrieval_success) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))