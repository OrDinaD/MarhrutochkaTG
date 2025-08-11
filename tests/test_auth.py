import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.auth.bot_auth_manager import BotAuthManager

class TestAuthManager(unittest.TestCase):

    def setUp(self):
        """Set up a new BotAuthManager for each test."""
        # Patch the dependency 'ImprovedWebAuth' to avoid actual web requests
        self.mock_web_auth_patch = patch('src.auth.bot_auth_manager.ImprovedWebAuth')
        self.MockImprovedWebAuth = self.mock_web_auth_patch.start()
        self.addCleanup(self.mock_web_auth_patch.stop)

        self.auth_manager = BotAuthManager()
        self.user_id = 12345

    def test_login_success(self):
        """Test successful user login."""
        # Configure the mock to simulate a successful login
        mock_auth_instance = self.MockImprovedWebAuth.return_value
        mock_auth_instance.login.return_value = True
        mock_auth_instance.save_session.return_value = True

        # Attempt to log in
        success = self.auth_manager.login(self.user_id, 'test_phone', 'test_password')

        self.assertTrue(success)
        self.assertTrue(self.auth_manager.is_authenticated(self.user_id))
        mock_auth_instance.login.assert_called_once_with('test_phone', 'test_password')
        mock_auth_instance.save_session.assert_called_once()

    def test_login_failure(self):
        """Test failed user login."""
        # Configure the mock to simulate a failed login
        mock_auth_instance = self.MockImprovedWebAuth.return_value
        mock_auth_instance.login.return_value = False

        # Attempt to log in
        success = self.auth_manager.login(self.user_id, 'wrong_phone', 'wrong_password')

        self.assertFalse(success)
        self.assertFalse(self.auth_manager.is_authenticated(self.user_id))
        mock_auth_instance.login.assert_called_once_with('wrong_phone', 'wrong_password')

    def test_logout(self):
        """Test user logout."""
        # First, simulate a logged-in user
        mock_auth_instance = self.MockImprovedWebAuth.return_value
        mock_auth_instance.login.return_value = True
        self.auth_manager.login(self.user_id, 'test_phone', 'test_password')
        self.assertIn(self.user_id, self.auth_manager.sessions)

        # Configure the mock for logout and session file removal
        with patch('os.path.exists', return_value=True) as mock_exists, \
             patch('os.remove') as mock_remove:
            
            # Attempt to log out
            logout_success = self.auth_manager.logout(self.user_id)

            self.assertTrue(logout_success)
            # Check that the session was removed from the in-memory dictionary
            self.assertNotIn(self.user_id, self.auth_manager.sessions)
            mock_auth_instance.logout.assert_called_once()
            mock_exists.assert_called_once()
            mock_remove.assert_called_once()

    def test_get_user_profile_when_authenticated(self):
        """Test getting user profile for an authenticated user."""
        # Simulate a logged-in user
        mock_auth_instance = self.MockImprovedWebAuth.return_value
        mock_auth_instance.login.return_value = True
        self.auth_manager.login(self.user_id, 'test_phone', 'test_password')

        # Configure the mock to return a dummy profile
        dummy_profile = MagicMock()
        dummy_profile.name = 'Test'
        dummy_profile.surname = 'User'
        mock_auth_instance.get_user_profile.return_value = dummy_profile

        # Get the profile
        profile = self.auth_manager.get_user_profile(self.user_id)

        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, 'Test')
        mock_auth_instance.get_user_profile.assert_called_once()

    def test_get_user_profile_when_not_authenticated(self):
        """Test getting user profile for a non-authenticated user."""
        profile = self.auth_manager.get_user_profile(self.user_id)

        self.assertIsNone(profile)

if __name__ == '__main__':
    unittest.main()
