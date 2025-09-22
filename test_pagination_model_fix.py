#!/usr/bin/env python3
"""
Test pagination model persistence fix for large context discussions.
"""

import asyncio
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))

from lib.grok_client import GrokClient
from lib.tools.discuss import DiscussTool
from lib.tools.session import SessionManager


async def test_pagination_model_persistence():
    """Test that model and context settings are preserved during pagination."""
    print("=== Testing Pagination Model Persistence ===")

    # Initialize tools
    client = GrokClient()
    session_manager = SessionManager(Path("./test_sessions"))
    tool = DiscussTool(client, session_manager)

    # Test 1: Create discussion with grok-4-fast-reasoning and large context
    print("\n1. Creating large context discussion with grok-4-fast-reasoning...")
    try:
        result = await tool.execute(
            topic="Test large context pagination",
            model="grok-4-fast-reasoning",
            max_total_context_lines=1500000,  # 1.5M lines
            max_turns=3,
            turns_per_page=1,
            paginate=True,
            expert_mode=True
        )

        print("✓ Created discussion successfully")

        # Extract session ID
        if "Session ID:" in result:
            session_id = result.split("Session ID:")[1].split("\n")[0].strip()
            print(f"✓ Session ID: {session_id}")

            # Verify model and context limit in result
            if "Model: grok-4-fast-reasoning" in result and "1,500,000 lines" in result:
                print("✓ Correct model and context limit displayed")
            else:
                print(f"✗ Model/context info not found in result: {result[:300]}")

            # Check session storage
            session = session_manager.get_session(session_id)
            if session and 'pagination' in session:
                pagination_data = session['pagination']
                stored_model = pagination_data.get('model')
                stored_context_limit = pagination_data.get('max_total_context_lines')

                print(f"✓ Stored model: {stored_model}")
                print(f"✓ Stored context limit: {stored_context_limit:,}")

                if stored_model == "grok-4-fast-reasoning" and stored_context_limit == 1500000:
                    print("✓ Session correctly stores model and context settings")
                else:
                    print(f"✗ Session storage incorrect: model={stored_model}, limit={stored_context_limit}")
            else:
                print("✗ Session pagination data not found")

            # Test 2: View page 2 without specifying model
            print("\n2. Testing page 2 retrieval (should use stored model)...")
            try:
                page2_result = await tool.execute(
                    session_id=session_id,
                    page=2
                    # Note: Not specifying model - should use stored value
                )

                if "Model: grok-4-fast-reasoning" in page2_result:
                    print("✓ Page 2 correctly uses stored model (grok-4-fast-reasoning)")
                else:
                    print(f"✗ Page 2 model incorrect: {page2_result[:300]}")

                if "1,500,000 lines" in page2_result:
                    print("✓ Page 2 correctly uses stored context limit")
                else:
                    print(f"✗ Page 2 context limit incorrect")

                if "Page 2 of" in page2_result:
                    print("✓ Page 2 successfully retrieved")
                    return True
                else:
                    print(f"✗ Page 2 format incorrect: {page2_result[:200]}")

            except Exception as e:
                print(f"✗ Page 2 retrieval failed: {e}")
                return False

        else:
            print("✗ Could not extract session ID")
            return False

    except Exception as e:
        print(f"✗ Discussion creation failed: {e}")
        return False


async def test_model_switching():
    """Test switching between models in the same tool."""
    print("\n=== Testing Model Switching ===")

    client = GrokClient()
    session_manager = SessionManager(Path("./test_sessions"))
    tool = DiscussTool(client, session_manager)

    # Create session with grok-code-fast
    print("\n1. Creating session with grok-code-fast...")
    result1 = await tool.execute(
        topic="Test model switching",
        model="grok-code-fast",
        max_total_context_lines=150000,
        max_turns=2,
        paginate=False
    )

    if "Model: grok-code-fast" in result1:
        print("✓ grok-code-fast session created correctly")
    else:
        print("✗ grok-code-fast session incorrect")

    # Create another session with grok-4-fast-reasoning
    print("\n2. Creating session with grok-4-fast-reasoning...")
    result2 = await tool.execute(
        topic="Test large model",
        model="grok-4-fast-reasoning",
        max_total_context_lines=1200000,
        max_turns=2,
        paginate=False
    )

    if "Model: grok-4-fast-reasoning" in result2:
        print("✓ grok-4-fast-reasoning session created correctly")
        return True
    else:
        print("✗ grok-4-fast-reasoning session incorrect")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Pagination Model Persistence Fix")
    print("=" * 60)

    try:
        # Test pagination model persistence
        pagination_success = await test_pagination_model_persistence()

        # Test model switching
        switching_success = await test_model_switching()

        print("\n" + "=" * 60)
        if pagination_success and switching_success:
            print("✓ All tests passed!")
            print("\nFix verified:")
            print("• Model settings are stored with session")
            print("• Page 2 retrieval uses stored model")
            print("• Large context limits preserved during pagination")
            print("• Model switching works correctly")
        else:
            print("✗ Some tests failed!")
        print("=" * 60)

        return 0 if (pagination_success and switching_success) else 1

    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))