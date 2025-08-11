import unittest
from unittest.mock import MagicMock, AsyncMock
import sys
import os
import asyncio

# Ensure the src directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from bot import start, help_command

class TestBot(unittest.TestCase):

    def test_start_command(self):
        """Test the start command handler."""
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        
        # Run the async function
        asyncio.run(start(update, context))
        
        update.message.reply_text.assert_called_once()

    def test_help_command_response(self):
        """Check if the help command sends the correct message."""
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        
        # Run the async function
        asyncio.run(help_command(update, context))
        
        update.message.reply_text.assert_called_once()

if __name__ == '__main__':
    unittest.main()