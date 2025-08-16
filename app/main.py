#!/usr/bin/env python3
"""
FreqTrade Hyperparameter Optimization Automation - CLI Version
Main entry point for command-line interface.
"""

import sys
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from modules.freqtrade_optimizer import FreqTradeOptimizer


def main():
    """Main entry point of the CLI application."""
    print("FreqTrade Hyperparameter Optimization Automation")
    print("=" * 50)

    optimizer = FreqTradeOptimizer()
    exit_code = 1  # Default to failure

    try:
        if optimizer.run():
            print("\n✓ Optimization workflow completed successfully!")
            exit_code = 0
        else:
            print("\n✗ Optimization workflow completed with errors.")

    except Exception as e:
        print(f"\nFatal error: {e}")
    finally:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()