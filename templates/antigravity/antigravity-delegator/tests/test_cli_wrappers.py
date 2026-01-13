import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from pathlib import Path

# Adjust path so we can import modules from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import codex_cli
import gemini_cli

class TestCodexCLI(unittest.TestCase):
    @patch('codex_cli.subprocess.run')
    @patch('codex_cli.load_usage')
    @patch('codex_cli.save_usage')
    @patch('codex_cli.append_call_log')
    @patch('codex_cli.resolve_codex_path')
    @patch('sys.stderr') # Silence stderr
    def test_tty_bypass(self, mock_stderr, mock_resolve, mock_append, mock_save, mock_load, mock_run):
        """Test that input='' is passed to force non-interactive mode"""
        mock_resolve.return_value = '/path/to/codex'
        mock_load.return_value = {}
        
        # Mock successful run
        mock_run.return_value = MagicMock(returncode=0, stdout="help text", stderr="")
        
        # Simulate main running with basic args
        with patch.object(sys, 'argv', ['codex_cli.py', 'exec']):
            try:
                codex_cli.main()
            except SystemExit as e:
                pass # Expected exit code from sys.exit(returncode) but we mocked run
        
        # Verify subprocess.run was called with input=""
        args, kwargs = mock_run.call_args
        self.assertEqual(kwargs.get('input'), "", "Should pass empty input to bypass TTY check")
        self.assertEqual(kwargs.get('text'), True)

    @patch('codex_cli.subprocess.run')
    @patch('codex_cli.load_usage')
    @patch('codex_cli.save_usage')
    @patch('codex_cli.append_call_log')
    @patch('codex_cli.resolve_codex_path')
    @patch('codex_cli.iter_recent_session_logs')
    @patch('sys.stderr')
    def test_usage_increment(self, mock_stderr, mock_iter_logs, mock_resolve, mock_append, mock_save, mock_load, mock_run):
        """Test that usage counts increment"""
        mock_resolve.return_value = '/path/to/codex'
        mock_load.return_value = {"codex": {"calls": 10, "used": 100}}
        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")
        mock_iter_logs.return_value = [] # No logs found
        
        with patch.object(sys, 'argv', ['codex_cli.py', 'prompt']):
            try:
                codex_cli.main()
            except SystemExit:
                pass
        
        # Check save_usage was called with incremented values
        args, _ = mock_save.call_args
        usage_data = args[0]
        self.assertEqual(usage_data["codex"]["calls"], 11)
        self.assertGreater(usage_data["codex"]["used"], 100)

class TestGeminiCLI(unittest.TestCase):
    @patch('gemini_cli.subprocess.run')
    @patch('gemini_cli.load_usage')
    @patch('gemini_cli.save_usage')
    @patch('gemini_cli.append_call_log')
    @patch('gemini_cli.resolve_gemini_path')
    @patch('sys.stderr')
    def test_model_injection(self, mock_stderr, mock_resolve, mock_append, mock_save, mock_load, mock_run):
        """Test that default model is injected if missing"""
        mock_resolve.return_value = '/path/to/gemini'
        mock_load.return_value = {}
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Run without model arg
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GEMINI_DEFAULT_MODEL", None)
            os.environ.pop("GEMINI_MODEL", None)
            with patch.object(sys, 'argv', ['gemini_cli.py', 'prompt']):
                try:
                    gemini_cli.main()
                except SystemExit:
                    pass

        # Verify call args contained --model flash
        args, _ = mock_run.call_args
        cmd_list = args[0]
        self.assertIn('--model', cmd_list)
        self.assertIn('flash', cmd_list)

    @patch('gemini_cli.subprocess.run')
    @patch('gemini_cli.load_usage')
    @patch('gemini_cli.save_usage')
    @patch('gemini_cli.append_call_log')
    @patch('gemini_cli.resolve_gemini_path')
    @patch('sys.stderr')
    def test_model_env_override(self, mock_stderr, mock_resolve, mock_append, mock_save, mock_load, mock_run):
        """Test that GEMINI_DEFAULT_MODEL overrides the default injection"""
        mock_resolve.return_value = '/path/to/gemini'
        mock_load.return_value = {}
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch.dict(os.environ, {"GEMINI_DEFAULT_MODEL": "gemini-1.5-pro"}, clear=False):
            with patch.object(sys, 'argv', ['gemini_cli.py', 'prompt']):
                try:
                    gemini_cli.main()
                except SystemExit:
                    pass

        args, _ = mock_run.call_args
        cmd_list = args[0]
        self.assertIn('--model', cmd_list)
        self.assertIn('gemini-1.5-pro', cmd_list)
        self.assertNotIn('flash', cmd_list)

    @patch('gemini_cli.subprocess.run')
    @patch('gemini_cli.load_usage')
    @patch('gemini_cli.save_usage')
    @patch('gemini_cli.append_call_log')
    @patch('gemini_cli.resolve_gemini_path')
    @patch('sys.stderr')
    def test_no_double_injection(self, mock_stderr, mock_resolve, mock_append, mock_save, mock_load, mock_run):
        """Test that default model is NOT injected if user provides one"""
        mock_resolve.return_value = '/path/to/gemini'
        mock_load.return_value = {}
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Run with explicit model
        with patch.dict(os.environ, {"GEMINI_DEFAULT_MODEL": "flash"}, clear=False):
            with patch.object(sys, 'argv', ['gemini_cli.py', '--model', 'gemini-1.5-flash', 'prompt']):
                try:
                    gemini_cli.main()
                except SystemExit:
                    pass

        # Verify we didn't add the default one
        args, _ = mock_run.call_args
        cmd_list = args[0]
        # Should contain the user's model
        self.assertIn('gemini-1.5-flash', cmd_list)
        self.assertNotIn('flash', cmd_list)


if __name__ == '__main__':
    unittest.main()
