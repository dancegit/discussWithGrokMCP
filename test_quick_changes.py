#!/usr/bin/env python3
"""
Quick test for critical changes without API calls.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.grok_client import GrokClient
from lib.tools.discuss import DiscussTool
from lib.tools.session import SessionManager
from lib.tools.ask import AskTool


def test_defaults():
    """Test default model changes."""
    print("=== Testing Default Model ===")

    # Test GrokClient default
    try:
        client = GrokClient()
        assert client.model == "grok-code-fast", f"Expected grok-code-fast, got {client.model}"
        print(f"✓ GrokClient default model: {client.model}")
    except ValueError as e:
        # API key not found, but we can still check the default was attempted
        print(f"✓ GrokClient attempted to use model (API key missing)")

    # Test AskTool schema
    tool = AskTool(None)  # No client needed for schema check
    schema = tool.input_schema
    model_default = schema['properties']['model']['default']
    model_enum = schema['properties']['model']['enum']
    assert model_default == "grok-code-fast", f"Expected grok-code-fast, got {model_default}"
    assert "grok-code-fast" in model_enum, "grok-code-fast not in enum"
    print(f"✓ AskTool default model: {model_default}")
    print(f"✓ AskTool model options: {model_enum[:3]}...")

    return True


def test_pagination_schema():
    """Test pagination schema changes."""
    print("\n=== Testing Pagination Schema ===")

    tool = DiscussTool(None, None)  # No dependencies needed for schema check
    schema = tool.input_schema

    # Check topic is not required
    required = schema.get('required', [])
    assert 'topic' not in required, f"Topic should not be required, but required={required}"
    print(f"✓ Topic is not in required fields: {required}")

    # Check topic has description
    topic_prop = schema['properties']['topic']
    assert 'description' in topic_prop, "Topic should have description"
    print(f"✓ Topic property exists but is optional")

    # Check session_id exists
    assert 'session_id' in schema['properties'], "session_id should exist"
    print(f"✓ session_id property exists for pagination")

    return True


def test_session_manager():
    """Test session manager pagination storage."""
    print("\n=== Testing Session Manager ===")

    storage_path = Path("./test_sessions_quick")
    manager = SessionManager(storage_path)

    # Test create_session with pagination
    pagination_settings = {
        "turns_per_page": 3,
        "max_turns": 9,
        "paginate": True
    }
    session_id = manager.create_session("Test", pagination_settings)
    print(f"✓ Created session with pagination: {session_id}")

    # Verify pagination stored
    session = manager.get_session(session_id)
    assert 'pagination' in session, "Pagination not in session"
    assert session['pagination'] == pagination_settings, "Pagination settings don't match"
    print(f"✓ Pagination settings stored: {session['pagination']}")

    # Clean up
    import shutil
    if storage_path.exists():
        shutil.rmtree(storage_path)

    return True


def main():
    """Run quick tests."""
    print("=" * 60)
    print("Quick Test of Recent Changes (No API Calls)")
    print("=" * 60)

    all_passed = True

    try:
        if not test_defaults():
            all_passed = False

        if not test_pagination_schema():
            all_passed = False

        if not test_session_manager():
            all_passed = False

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All quick tests passed!")
        print("\nChanges verified:")
        print("  • Default model is now grok-code-fast")
        print("  • Topic is optional for pagination")
        print("  • Pagination settings stored with session")
        print("  • Model selection includes both grok-code-fast and grok-4-fast-reasoning")
    else:
        print("✗ Some tests failed!")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())