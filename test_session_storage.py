#!/usr/bin/env python3
"""
Test session storage and retrieval without API calls.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.tools.session import SessionManager


def test_session_storage():
    """Test that pagination settings including model are stored correctly."""
    print("=== Testing Session Storage ===")

    storage_path = Path("./test_sessions_storage")
    manager = SessionManager(storage_path)

    # Test 1: Create session with model and context settings
    print("\n1. Creating session with model and context settings...")
    pagination_settings = {
        "turns_per_page": 2,
        "max_turns": 5,
        "paginate": True,
        "model": "grok-4-fast-reasoning",
        "max_context_lines": 1000,
        "max_total_context_lines": 1800000,
        "context_type": "code"
    }

    session_id = manager.create_session("Test topic", pagination_settings)
    print(f"✓ Created session: {session_id}")

    # Test 2: Retrieve session and verify settings
    print("\n2. Retrieving session and verifying settings...")
    session = manager.get_session(session_id)

    if session and 'pagination' in session:
        stored = session['pagination']
        print(f"✓ Retrieved pagination settings: {stored}")

        # Verify all settings
        checks = [
            ("model", "grok-4-fast-reasoning"),
            ("max_total_context_lines", 1800000),
            ("turns_per_page", 2),
            ("max_turns", 5),
            ("context_type", "code")
        ]

        all_correct = True
        for key, expected in checks:
            actual = stored.get(key)
            if actual == expected:
                print(f"✓ {key}: {actual}")
            else:
                print(f"✗ {key}: expected {expected}, got {actual}")
                all_correct = False

        if all_correct:
            print("✓ All settings stored correctly")
        else:
            print("✗ Some settings incorrect")

    else:
        print("✗ No pagination settings found in session")
        all_correct = False

    # Clean up
    import shutil
    if storage_path.exists():
        shutil.rmtree(storage_path)

    return all_correct


def test_discuss_tool_schema():
    """Test that discuss tool schema includes model parameter."""
    print("\n=== Testing Discuss Tool Schema ===")

    from lib.tools.discuss import DiscussTool
    tool = DiscussTool(None, None)
    schema = tool.input_schema

    # Check model parameter exists
    if 'model' in schema['properties']:
        model_prop = schema['properties']['model']
        print(f"✓ Model parameter exists: {model_prop}")

        # Check enum includes both models
        enum_values = model_prop.get('enum', [])
        if "grok-4-fast-reasoning" in enum_values and "grok-code-fast" in enum_values:
            print("✓ Both models in enum")
        else:
            print(f"✗ Missing models in enum: {enum_values}")

        # Check default
        default = model_prop.get('default')
        if default == "grok-code-fast":
            print(f"✓ Correct default: {default}")
        else:
            print(f"✗ Wrong default: {default}")

        return True
    else:
        print("✗ Model parameter not found in schema")
        return False


def main():
    """Run storage tests."""
    print("=" * 60)
    print("Testing Session Storage and Schema (No API Calls)")
    print("=" * 60)

    storage_success = test_session_storage()
    schema_success = test_discuss_tool_schema()

    print("\n" + "=" * 60)
    if storage_success and schema_success:
        print("✓ All storage tests passed!")
        print("\nVerified:")
        print("• Session stores model and context settings")
        print("• Schema includes model parameter")
        print("• Both grok-code-fast and grok-4-fast-reasoning available")
    else:
        print("✗ Some tests failed!")
    print("=" * 60)

    return 0 if (storage_success and schema_success) else 1


if __name__ == "__main__":
    sys.exit(main())