#!/usr/bin/env python3
"""Entry point for MarhrutochkaTG bot."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bot import main

if __name__ == '__main__':
    main()
