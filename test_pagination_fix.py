#!/usr/bin/env python3
"""
Test script for verifying pagination fix in grok_discuss tool.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.grok_client import GrokClient
from lib.tools.discuss import DiscussTool
from lib.tools.session import SessionManager


async def test_pagination_fix():
    """Test pagination functionality with the fix."""
    print("Testing pagination fix...")

    # Initialize tools
    client = GrokClient()
    session_manager = SessionManager(Path("./test_sessions"))
    tool = DiscussTool(client, session_manager)

    # Test 1: Create a new discussion (should require topic)
    print("\n1. Testing new discussion creation...")
    try:
        result = await tool.execute()  # No topic provided
        print(f"✓ Handled missing topic gracefully: {result}")
    except Exception as e:
        print(f"✗ Error handling missing topic: {e}")

    # Test 2: Create a valid new discussion with pagination
    print("\n2. Creating valid paginated discussion...")
    try:
        result = await tool.execute(
            topic="Test pagination functionality",
            max_turns=3,
            paginate=True,
            turns_per_page=1
        )
        print(f"✓ Created discussion successfully")

        # Extract session ID from result
        if "Session ID:" in result:
            session_id = result.split("Session ID:")[1].split("\n")[0].strip()
            print(f"✓ Session ID: {session_id}")

            # Test 3: View page 2 without topic (this should work now)
            print("\n3. Testing pagination without topic...")
            try:
                page2_result = await tool.execute(
                    session_id=session_id,
                    page=2,
                    paginate=True,
                    turns_per_page=1
                )
                print(f"✓ Page 2 accessed successfully!")
                print(f"Result preview: {page2_result[:200]}...")

                # Test 4: View page 3
                print("\n4. Testing page 3...")
                page3_result = await tool.execute(
                    session_id=session_id,
                    page=3,
                    paginate=True,
                    turns_per_page=1
                )
                print(f"✓ Page 3 accessed successfully!")
                print(f"Result preview: {page3_result[:200]}...")

            except Exception as e:
                print(f"✗ Pagination failed: {e}")

        else:
            print("✗ Could not extract session ID from result")

    except Exception as e:
        print(f"✗ Failed to create discussion: {e}")

    print("\n" + "="*50)
    print("Pagination fix test completed!")


if __name__ == "__main__":
    asyncio.run(test_pagination_fix())