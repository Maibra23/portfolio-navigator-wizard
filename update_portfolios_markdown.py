#!/usr/bin/env python3
"""Auto-update PORTFOLIOS_IN_REDIS.md when portfolios change"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from generate_all_portfolios import update_portfolios_markdown

if __name__ == '__main__':
    try:
        update_portfolios_markdown()
        print("✅ PORTFOLIOS_IN_REDIS.md updated successfully")
    except Exception as e:
        print(f"❌ Failed to update markdown: {e}")
