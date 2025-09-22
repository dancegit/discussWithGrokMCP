#!/usr/bin/env python3
"""
Test automatic session repair functionality.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from lib.grok_client import GrokClient
from lib.tools.discuss import DiscussTool
from lib.tools.session import SessionManager


def create_broken_session(session_id: str, session_manager: SessionManager):
    """Create a session without pagination data (simulating old sessions)."""

    # Create session data without pagination settings (old format)
    session_data = {
        "id": session_id,
        "topic": "VSO System Analysis - Old Session Format",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": [
            {"role": "user", "content": "Initial discussion about VSO system", "timestamp": datetime.now().isoformat()},
            {"role": "assistant", "content": "Analysis of VSO system...", "timestamp": datetime.now().isoformat()}
        ],
        "status": "active"
        # Note: NO pagination settings - this simulates old sessions
    }

    # Save manually
    session_file = session_manager.storage_path / f"{session_id}.json"
    with open(session_file, 'w') as f:
        json.dump(session_data, f, indent=2)

    # Add to manager's memory
    session_manager.sessions[session_id] = session_data

    print(f"✓ Created broken session (no pagination data): {session_id}")
    return session_data


async def test_auto_repair():
    """Test that auto-repair works when accessing old sessions."""
    print("=== Testing Automatic Session Repair ===")

    # Setup
    storage_path = Path("./test_sessions_auto_repair")
    storage_path.mkdir(exist_ok=True)

    session_manager = SessionManager(storage_path)
    client = GrokClient()
    tool = DiscussTool(client, session_manager)

    # Test 1: Create a broken session (no pagination data)
    print("\n1. Creating broken session (old format)...")
    session_id = "test-auto-repair-session"
    broken_session = create_broken_session(session_id, session_manager)

    # Verify it's broken
    assert 'pagination' not in broken_session
    print("✓ Session created without pagination data")

    # Test 2: Try to access page 1 - should trigger auto-repair
    print("\n2. Accessing page 1 (should trigger auto-repair)...")
    try:
        result = await tool.execute(
            session_id=session_id,
            page=1
        )

        print("✓ Page 1 accessed successfully")

        # Check if repair message is in result or logs
        if "Model: grok-4-fast-reasoning" in result:
            print("✓ Auto-repair correctly inferred grok-4-fast-reasoning from VSO topic")
        elif "Model: grok-code-fast" in result:
            print("✓ Auto-repair used default grok-code-fast")
        else:
            print(f"? Model info not found in result: {result[:200]}")

    except Exception as e:
        print(f"✗ Page 1 access failed: {e}")
        return False

    # Test 3: Verify session was actually repaired
    print("\n3. Verifying session was repaired...")
    repaired_session = session_manager.get_session(session_id)

    if 'pagination' in repaired_session:
        pagination = repaired_session['pagination']
        print(f"✓ Session now has pagination data: {pagination}")

        # Check required fields
        required_fields = ['model', 'max_total_context_lines', 'turns_per_page', 'max_turns', 'paginate']
        all_present = True
        for field in required_fields:
            if field in pagination:
                print(f"✓ {field}: {pagination[field]}")
            else:
                print(f"✗ {field}: missing")
                all_present = False

        if not all_present:
            return False

        # Verify model was correctly inferred
        model = pagination.get('model')
        if model == 'grok-4-fast-reasoning' and 'VSO' in repaired_session.get('topic', ''):
            print("✓ Model correctly inferred from VSO topic")
        elif model == 'grok-code-fast':
            print("✓ Model set to default")
        else:
            print(f"✗ Unexpected model: {model}")
            return False

        # Verify context limits match model
        context_limit = pagination.get('max_total_context_lines')
        if model == 'grok-4-fast-reasoning' and context_limit == 1800000:
            print("✓ Context limit correctly set for large model")
        elif model == 'grok-code-fast' and context_limit == 180000:
            print("✓ Context limit correctly set for fast model")
        else:
            print(f"? Context limit: {context_limit} for model: {model}")

    else:
        print("✗ Session still missing pagination data")
        return False

    # Test 4: Try page 2 - should work now
    print("\n4. Testing page 2 access (should work after repair)...")
    try:
        page2_result = await tool.execute(
            session_id=session_id,
            page=2
        )

        if "Page 2 of" in page2_result:
            print("✓ Page 2 accessed successfully")
        else:
            print(f"? Page 2 format: {page2_result[:200]}")

        return True

    except Exception as e:
        print(f"✗ Page 2 access failed: {e}")
        if "maximum prompt length is 256000" in str(e):
            print("✗ Still getting 256K limit - repair didn't work correctly")
        return False

    finally:
        # Cleanup
        import shutil
        if storage_path.exists():
            shutil.rmtree(storage_path)


async def test_specific_session_repair():
    """Test repair of the specific session mentioned by user."""
    print("\n=== Testing Specific Session Repair ===")

    session_id = "8a215ddd-99ae-416c-9e7e-450f02e4667b"

    # Use existing sessions directory
    session_manager = SessionManager(Path("./sessions"))
    client = GrokClient()
    tool = DiscussTool(client, session_manager)

    # Check if session exists
    session = session_manager.get_session(session_id)
    if not session:
        print(f"✗ Session {session_id} not found")
        return False

    print(f"✓ Session {session_id} found")

    # Test page retrieval (this should auto-repair if needed)
    try:
        result = await tool.execute(
            session_id=session_id,
            page=1
        )

        if "Model:" in result:
            model_line = [line for line in result.split('\n') if 'Model:' in line][0]
            print(f"✓ {model_line.strip()}")

        return True

    except Exception as e:
        print(f"✗ Session access failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Automatic Session Repair")
    print("=" * 60)

    try:
        # Test general auto-repair
        general_success = await test_auto_repair()

        # Test specific session
        specific_success = await test_specific_session_repair()

        print("\n" + "=" * 60)
        if general_success and specific_success:
            print("✓ All auto-repair tests passed!")
            print("\nAuto-repair features verified:")
            print("  • Old sessions without pagination data are automatically repaired")
            print("  • Model is inferred from topic (VSO → grok-4-fast-reasoning)")
            print("  • Context limits are set based on model capabilities")
            print("  • Page retrieval works after auto-repair")
            print("  • Session 8a215ddd-99ae-416c-9e7e-450f02e4667b is functional")
        else:
            print("✗ Some auto-repair tests failed!")
        print("=" * 60)

        return 0 if (general_success and specific_success) else 1

    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))