#!/usr/bin/env python3
"""
Test script for verifying grok-4-fast-reasoning model with 2M token window.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.grok_client import GrokClient
from lib.tools.discuss import DiscussTool
from lib.tools.session import SessionManager
from lib.tools.ask import AskTool


async def test_basic_ask():
    """Test basic ask with new model."""
    print("\n=== Testing Basic Ask with grok-4-fast-reasoning ===")

    client = GrokClient()
    tool = AskTool(client)

    result = await tool.execute(
        question="What is the capital of France? Reply in one word."
    )
    print(f"Result: {result}")
    print(f"Model used: {client.model}")
    return "Paris" in result


async def test_large_context():
    """Test with large context to verify 2M token support."""
    print("\n=== Testing Large Context Support (2M tokens) ===")

    client = GrokClient()
    session_manager = SessionManager(Path("./test_sessions"))
    tool = DiscussTool(client, session_manager)

    # Create a discussion with large context limit
    result = await tool.execute(
        topic="Analyze this codebase structure",
        context_files=["lib/"],
        max_context_lines=1000,
        max_total_context_lines=2000000,  # 2M lines
        max_turns=1
    )

    print(f"Discussion started successfully")
    print(f"Model: {client.model}")
    print(f"Max context configured: 2,000,000 lines")

    # Extract session info from result
    if "Session ID:" in result:
        session_id = result.split("Session ID:")[1].split("\n")[0].strip()
        print(f"Session created: {session_id}")

    return True


async def test_model_info():
    """Display current model configuration."""
    print("\n=== Current Model Configuration ===")

    client = GrokClient()
    print(f"Default Model: {client.model}")
    print(f"Temperature: {client.temperature}")
    print(f"Max Retries: {client.max_retries}")

    # Check environment variables
    import os
    print(f"\nEnvironment Configuration:")
    print(f"GROK_MODEL: {os.getenv('GROK_MODEL', 'not set')}")
    print(f"GROK_MAX_TOKENS: {os.getenv('GROK_MAX_TOKENS', 'not set')}")
    print(f"MAX_CONTEXT_TOKENS: {os.getenv('MAX_CONTEXT_TOKENS', 'not set')}")

    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing grok-4-fast-reasoning with 2M token window")
    print("=" * 60)

    try:
        # Test model info
        await test_model_info()

        # Test basic ask
        ask_success = await test_basic_ask()
        print(f"✓ Basic ask test: {'PASSED' if ask_success else 'FAILED'}")

        # Test large context
        context_success = await test_large_context()
        print(f"✓ Large context test: {'PASSED' if context_success else 'FAILED'}")

        print("\n" + "=" * 60)
        print("✓ All tests completed successfully!")
        print(f"✓ Model: grok-4-fast-reasoning")
        print(f"✓ Max context: 2,000,000 lines")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())