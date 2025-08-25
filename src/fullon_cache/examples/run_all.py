#!/usr/bin/env python3
"""
Simple script to run all cache examples in succession.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def main():
    """Run all cache examples."""

    # Get the directory of this script
    script_dir = Path(__file__).parent

    # Check if we're in a Poetry environment and poetry is available
    use_poetry = False
    if shutil.which("poetry") and (script_dir.parent.parent.parent / "pyproject.toml").exists():
        use_poetry = True
        print("📦 Detected Poetry environment, using 'poetry run'")
    else:
        print("🐍 Using direct Python execution")

    # List of example files to run
    examples = [
        "example_account_cache.py",
        "example_bot_cache.py",
        "example_tick_cache.py",
        "example_orders_cache.py",
        "example_trades_cache.py",
        "example_ohlcv_cache.py",
        # "example_process_cache.py",  # Skip for now due to API complexity
    ]

    print("🚀 Running all fullon_cache examples...\n")

    for i, example in enumerate(examples, 1):
        print(f"[{i}/{len(examples)}] Running {example}...")

        example_path = script_dir / example
        if not example_path.exists():
            print(f"❌ {example} not found, skipping...")
            continue

        try:
            # Build command based on environment
            if use_poetry:
                cmd = ["poetry", "run", "python", str(example_path), "--operations", "basic"]
            else:
                cmd = [sys.executable, str(example_path), "--operations", "basic"]

            # Run the example
            subprocess.run(cmd, check=True)

            print(f"✅ {example} completed successfully\n")

        except subprocess.CalledProcessError as e:
            print(f"❌ {example} failed with exit code {e.returncode}\n")
        except Exception as e:
            print(f"❌ {example} failed with error: {e}\n")

    print("🎉 All examples completed!")


if __name__ == "__main__":
    main()
