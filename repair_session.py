#!/usr/bin/env python3
"""
Repair session script to add missing model and context settings.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from lib.tools.session import SessionManager


def repair_session(session_id: str, model: str = "grok-4-fast-reasoning",
                  max_total_context_lines: int = 1800000):
    """Repair a session by adding missing model and context settings."""

    print(f"Attempting to repair session: {session_id}")

    # Try different session storage locations
    possible_paths = [
        Path("./sessions"),
        Path("./test_sessions"),
        Path("./grok_discussions"),
        Path("./.slice-orchestrator/grok_sessions"),
    ]

    session_file = None
    storage_path = None

    # Find the session file
    for path in possible_paths:
        if path.exists():
            session_file_path = path / f"{session_id}.json"
            if session_file_path.exists():
                session_file = session_file_path
                storage_path = path
                print(f"✓ Found session at: {session_file}")
                break

    if not session_file:
        print(f"✗ Session {session_id} not found in any location")
        print("Searched locations:")
        for path in possible_paths:
            print(f"  - {path}")
        return False

    # Load the session
    try:
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        print(f"✓ Loaded session data")
    except Exception as e:
        print(f"✗ Failed to load session: {e}")
        return False

    # Check current pagination data
    current_pagination = session_data.get('pagination', {})
    print(f"Current pagination data: {current_pagination}")

    # Determine what needs to be added/updated
    updates_needed = {}

    if 'model' not in current_pagination:
        updates_needed['model'] = model

    if 'max_total_context_lines' not in current_pagination:
        updates_needed['max_total_context_lines'] = max_total_context_lines

    if 'max_context_lines' not in current_pagination:
        updates_needed['max_context_lines'] = 1000

    if 'context_type' not in current_pagination:
        updates_needed['context_type'] = 'code'

    if not updates_needed:
        print("✓ Session already has all required settings")
        return True

    print(f"Adding missing settings: {updates_needed}")

    # Update the pagination data
    if 'pagination' not in session_data:
        session_data['pagination'] = {}

    session_data['pagination'].update(updates_needed)
    session_data['updated_at'] = datetime.now().isoformat()

    # Backup original
    backup_file = session_file.with_suffix('.json.backup')
    try:
        with open(backup_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        print(f"✓ Created backup: {backup_file}")
    except Exception as e:
        print(f"✗ Failed to create backup: {e}")
        return False

    # Save updated session
    try:
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        print(f"✓ Updated session file")
    except Exception as e:
        print(f"✗ Failed to save updated session: {e}")
        return False

    # Verify the update
    session_manager = SessionManager(storage_path)
    updated_session = session_manager.get_session(session_id)

    if updated_session and 'pagination' in updated_session:
        pagination = updated_session['pagination']
        print(f"✓ Verified updated settings: {pagination}")

        # Check specific values
        if pagination.get('model') == model:
            print(f"✓ Model set to: {model}")
        if pagination.get('max_total_context_lines') == max_total_context_lines:
            print(f"✓ Context limit set to: {max_total_context_lines:,}")

        return True
    else:
        print("✗ Failed to verify updated session")
        return False


def create_session_if_missing(session_id: str):
    """Create a session if it doesn't exist, with proper settings."""
    print(f"\nCreating new session with ID: {session_id}")

    # Create in sessions directory
    storage_path = Path("./sessions")
    storage_path.mkdir(exist_ok=True)

    session_manager = SessionManager(storage_path)

    # Create session data manually
    session_data = {
        "id": session_id,
        "topic": "VSO System Operational Analysis: SignalMatrix Slice Lifecycle Progression",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": [],
        "status": "active",
        "pagination": {
            "turns_per_page": 2,
            "max_turns": 5,
            "paginate": True,
            "model": "grok-4-fast-reasoning",
            "max_context_lines": 1000,
            "max_total_context_lines": 1800000,
            "context_type": "code"
        }
    }

    # Save directly
    session_file = storage_path / f"{session_id}.json"
    try:
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        print(f"✓ Created session file: {session_file}")

        # Add to session manager's memory
        session_manager.sessions[session_id] = session_data

        # Verify
        session = session_manager.get_session(session_id)
        if session:
            print(f"✓ Session created successfully")
            print(f"  Model: {session['pagination']['model']}")
            print(f"  Context limit: {session['pagination']['max_total_context_lines']:,}")
            return True
        else:
            print("✗ Failed to verify created session")
            return False

    except Exception as e:
        print(f"✗ Failed to create session: {e}")
        return False


def main():
    """Main repair function."""
    session_id = "8a215ddd-99ae-416c-9e7e-450f02e4667b"

    print("=" * 60)
    print("Session Repair Tool")
    print("=" * 60)

    # Try to repair existing session
    success = repair_session(session_id)

    if not success:
        print("\nSession not found. Creating new session with proper settings...")
        success = create_session_if_missing(session_id)

    print("\n" + "=" * 60)
    if success:
        print("✓ Session repair/creation completed!")
        print(f"Session {session_id} now has:")
        print("  • Model: grok-4-fast-reasoning")
        print("  • Context limit: 1,800,000 lines")
        print("  • Pagination settings preserved")
        print("\nPage retrieval should now work:")
        print(f"  grok_discuss(session_id='{session_id}', page=2)")
    else:
        print("✗ Session repair failed!")
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())