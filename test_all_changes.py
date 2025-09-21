#!/usr/bin/env python3
"""
Test script for verifying all recent changes:
1. Pagination stores settings with session
2. Default model is grok-code-fast
3. Model selection works correctly
"""

import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.grok_client import GrokClient
from lib.tools.discuss import DiscussTool
from lib.tools.session import SessionManager
from lib.tools.ask import AskTool


async def test_default_model():
    """Test that default model is now grok-code-fast."""
    print("\n=== Testing Default Model ===")

    # Test GrokClient default
    client = GrokClient()
    assert client.model == "grok-code-fast", f"Expected grok-code-fast, got {client.model}"
    print(f"✓ GrokClient default model: {client.model}")

    # Test AskTool default
    tool = AskTool(client)
    schema = tool.input_schema
    model_default = schema['properties']['model']['default']
    assert model_default == "grok-code-fast", f"Expected grok-code-fast, got {model_default}"
    print(f"✓ AskTool default model: {model_default}")

    return True


async def test_pagination_settings_storage():
    """Test that pagination settings are stored and retrieved."""
    print("\n=== Testing Pagination Settings Storage ===")

    client = GrokClient()
    session_manager = SessionManager(Path("./test_sessions"))
    tool = DiscussTool(client, session_manager)

    # Create discussion with specific pagination settings
    print("Creating discussion with turns_per_page=3, max_turns=9...")
    result = await tool.execute(
        topic="Test pagination storage",
        max_turns=9,
        turns_per_page=3,
        paginate=True
    )

    # Extract session ID
    if "Session ID:" in result:
        session_id = result.split("Session ID:")[1].split("\n")[0].strip()
        print(f"✓ Created session: {session_id}")

        # Get session data
        session = session_manager.get_session(session_id)
        assert session is not None, "Session not found"

        # Check pagination settings are stored
        assert 'pagination' in session, "Pagination settings not stored"
        pagination = session['pagination']
        assert pagination['turns_per_page'] == 3, f"Expected 3, got {pagination.get('turns_per_page')}"
        assert pagination['max_turns'] == 9, f"Expected 9, got {pagination.get('max_turns')}"
        assert pagination['paginate'] == True, f"Expected True, got {pagination.get('paginate')}"
        print(f"✓ Pagination settings stored correctly: {pagination}")

        # Test viewing page 2 without specifying pagination settings
        print("\nViewing page 2 without specifying pagination settings...")
        page2_result = await tool.execute(
            session_id=session_id,
            page=2
        )

        # Verify page 2 was accessed correctly
        assert "Page 2 of" in page2_result, "Page 2 not accessed correctly"
        assert "Turns 4-6 of 9" in page2_result or "Turns 4-" in page2_result, "Wrong turn range"
        print(f"✓ Page 2 accessed successfully using stored settings")

        return True
    else:
        print("✗ Could not extract session ID")
        return False


async def test_model_selection():
    """Test that different models can be selected."""
    print("\n=== Testing Model Selection ===")

    # Test grok-code-fast (default)
    client1 = GrokClient()
    assert client1.model == "grok-code-fast"
    print(f"✓ Default: {client1.model}")

    # Test grok-4-fast-reasoning
    client2 = GrokClient(model="grok-4-fast-reasoning")
    assert client2.model == "grok-4-fast-reasoning"
    print(f"✓ Custom: {client2.model}")

    # Test with AskTool
    tool = AskTool(client1)
    result = await tool.execute(
        question="What is 2+2? Reply with just the number.",
        model="grok-4-fast-reasoning"
    )
    print(f"✓ AskTool can use different models")

    return True


async def test_pagination_without_topic():
    """Test that pagination works without requiring topic."""
    print("\n=== Testing Pagination Without Topic ===")

    client = GrokClient()
    session_manager = SessionManager(Path("./test_sessions"))
    tool = DiscussTool(client, session_manager)

    # Create initial discussion
    result = await tool.execute(
        topic="Test pagination without topic",
        max_turns=3,
        turns_per_page=1,
        paginate=True
    )

    # Extract session ID
    if "Session ID:" in result:
        session_id = result.split("Session ID:")[1].split("\n")[0].strip()
        print(f"✓ Created session: {session_id}")

        # Test viewing page 2 without topic
        try:
            page2_result = await tool.execute(
                session_id=session_id,
                page=2
                # No topic parameter!
            )
            print(f"✓ Page 2 accessed without topic parameter")
            return True
        except Exception as e:
            print(f"✗ Failed to access page 2 without topic: {e}")
            return False
    else:
        print("✗ Could not extract session ID")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing All Recent Changes")
    print("=" * 60)

    all_passed = True

    try:
        # Test 1: Default model
        if not await test_default_model():
            all_passed = False

        # Test 2: Pagination settings storage
        if not await test_pagination_settings_storage():
            all_passed = False

        # Test 3: Model selection
        if not await test_model_selection():
            all_passed = False

        # Test 4: Pagination without topic
        if not await test_pagination_without_topic():
            all_passed = False

    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed successfully!")
        print("Summary of changes verified:")
        print("  1. Default model is now grok-code-fast")
        print("  2. Pagination settings are stored with session")
        print("  3. Topic parameter not required for pagination")
        print("  4. Model selection works correctly")
    else:
        print("✗ Some tests failed!")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))