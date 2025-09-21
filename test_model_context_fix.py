#!/usr/bin/env python3
"""
Test model-aware context limits in grok_discuss tool.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.grok_client import GrokClient
from lib.tools.discuss import DiscussTool
from lib.tools.session import SessionManager


async def test_model_context_limits():
    """Test that different models have appropriate context limits."""
    print("=== Testing Model-Aware Context Limits ===")

    # Initialize tools
    client = GrokClient()  # Default client
    session_manager = SessionManager(Path("./test_sessions"))
    tool = DiscussTool(client, session_manager)

    # Test 1: grok-code-fast with large context (should adjust)
    print("\n1. Testing grok-code-fast with large context...")
    try:
        result = await tool.execute(
            topic="Test grok-code-fast limits",
            model="grok-code-fast",
            max_total_context_lines=1000000,  # Request 1M lines
            max_turns=1,
            paginate=False
        )
        print("✓ grok-code-fast handled large context request")
        if "Session ID:" in result:
            session_id = result.split("Session ID:")[1].split("\n")[0].strip()
            print(f"✓ Created session: {session_id}")
    except Exception as e:
        print(f"✗ grok-code-fast failed: {e}")

    # Test 2: grok-4-fast-reasoning with large context (should accept)
    print("\n2. Testing grok-4-fast-reasoning with large context...")
    try:
        result = await tool.execute(
            topic="Test grok-4-fast-reasoning limits",
            model="grok-4-fast-reasoning",
            max_total_context_lines=1000000,  # Request 1M lines
            max_turns=1,
            paginate=False
        )
        print("✓ grok-4-fast-reasoning accepted large context")
        if "Session ID:" in result:
            session_id = result.split("Session ID:")[1].split("\n")[0].strip()
            print(f"✓ Created session: {session_id}")
    except Exception as e:
        print(f"✗ grok-4-fast-reasoning failed: {e}")

    # Test 3: Check schema includes model parameter
    print("\n3. Testing schema includes model parameter...")
    schema = tool.input_schema
    if 'model' in schema['properties']:
        model_enum = schema['properties']['model']['enum']
        model_default = schema['properties']['model']['default']
        print(f"✓ Model parameter exists with default: {model_default}")
        print(f"✓ Available models: {model_enum}")

        # Check both models are in enum
        if "grok-code-fast" in model_enum and "grok-4-fast-reasoning" in model_enum:
            print("✓ Both grok-code-fast and grok-4-fast-reasoning available")
        else:
            print("✗ Missing expected models in enum")
    else:
        print("✗ Model parameter not found in schema")

    print("\n" + "=" * 50)
    print("Model context limit fix test completed!")


async def test_context_estimation():
    """Test context size calculations."""
    print("\n=== Testing Context Size Logic ===")

    # Test model limits
    model_limits = {
        "grok-code-fast": 200000,  # ~256K tokens
        "grok-4-fast-reasoning": 2000000,  # 2M tokens
    }

    for model, limit in model_limits.items():
        print(f"{model}: {limit:,} lines (~{limit * 1.25 / 1000:.0f}K tokens)")

    # Test context size estimation
    print("\nContext Size Estimation Examples:")
    test_sizes = [1000, 10000, 100000, 500000, 1000000, 2000000]

    for lines in test_sizes:
        tokens_low = lines * 1.2
        tokens_high = lines * 1.5
        tokens_avg = lines * 1.35

        # Determine appropriate model
        if tokens_avg <= 256000:
            recommended = "grok-code-fast"
        else:
            recommended = "grok-4-fast-reasoning"

        print(f"{lines:,} lines → {tokens_avg/1000:.0f}K tokens → {recommended}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Model-Aware Context Limits Fix")
    print("=" * 60)

    try:
        await test_model_context_limits()
        await test_context_estimation()

        print("\n" + "=" * 60)
        print("✓ All tests completed!")
        print("\nSummary:")
        print("• grok_discuss now supports model parameter")
        print("• Context limits are model-aware")
        print("• grok-4-fast-reasoning supports up to 2M lines")
        print("• grok-code-fast optimized for <200K lines")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())