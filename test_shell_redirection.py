#!/usr/bin/env python3
"""
Test suite for Shell Redirection Parser

This module contains tests to verify the shell redirection parsing
functionality works correctly for various input scenarios.
"""

import unittest
import tempfile
import os
from shell_redirection_parser import ShellRedirectionParser, AutoPromptExecutor


class TestShellRedirectionParser(unittest.TestCase):
    """Test cases for ShellRedirectionParser class."""
    
    def setUp(self):
        self.parser = ShellRedirectionParser()
    
    def test_no_redirection(self):
        """Test commands without redirection."""
        cmd = "aws ec2 describe-instances"
        aws_cmd, redirection = self.parser.parse_command(cmd)
        
        self.assertEqual(aws_cmd, cmd)
        self.assertIsNone(redirection)
    
    def test_simple_stdout_redirect(self):
        """Test simple stdout redirection."""
        cmd = "aws ec2 describe-instances >output.json"
        aws_cmd, redirection = self.parser.parse_command(cmd)
        
        self.assertEqual(aws_cmd, "aws ec2 describe-instances")
        self.assertIsNotNone(redirection)
        self.assertEqual(redirection['type'], 'redirect')
        self.assertEqual(redirection['target'], 'output.json')
        self.assertFalse(redirection['append'])
        self.assertFalse(redirection['stderr'])
    
    def test_append_redirect(self):
        """Test append redirection."""
        cmd = "aws s3 ls >>bucket-list.txt"
        aws_cmd, redirection = self.parser.parse_command(cmd)
        
        self.assertEqual(aws_cmd, "aws s3 ls")
        self.assertEqual(redirection['type'], 'redirect')
        self.assertEqual(redirection['target'], 'bucket-list.txt')
        self.assertTrue(redirection['append'])
    
    def test_stderr_redirect(self):
        """Test stderr redirection."""
        cmd = "aws ec2 describe-instances 2>errors.log"
        aws_cmd, redirection = self.parser.parse_command(cmd)
        
        self.assertEqual(aws_cmd, "aws ec2 describe-instances")
        self.assertEqual(redirection['type'], 'redirect')
        self.assertEqual(redirection['target'], 'errors.log')
        self.assertTrue(redirection['stderr'])
        self.assertFalse(redirection['append'])
    
    def test_both_redirect(self):
        """Test redirecting both stdout and stderr."""
        cmd = "aws ec2 describe-instances &>combined.log"
        aws_cmd, redirection = self.parser.parse_command(cmd)
        
        self.assertEqual(aws_cmd, "aws ec2 describe-instances")
        self.assertEqual(redirection['type'], 'redirect')
        self.assertEqual(redirection['target'], 'combined.log')
        self.assertTrue(redirection['both'])
    
    def test_pipe_redirect(self):
        """Test pipe redirection."""
        cmd = "aws ec2 describe-instances | jq '.Reservations[0]'"
        aws_cmd, redirection = self.parser.parse_command(cmd)
        
        self.assertEqual(aws_cmd, "aws ec2 describe-instances")
        self.assertEqual(redirection['type'], 'pipe')
        self.assertEqual(redirection['target'], "jq '.Reservations[0]'")
    
    def test_quoted_redirection_not_parsed(self):
        """Test that redirection inside quotes is not parsed."""
        cmd = 'aws s3 cp file.txt s3://bucket/key --metadata "description=>not a redirection"'
        aws_cmd, redirection = self.parser.parse_command(cmd)
        
        self.assertEqual(aws_cmd, cmd)
        self.assertIsNone(redirection)
    
    def test_complex_command_with_redirection(self):
        """Test complex command with filters and redirection."""
        cmd = 'aws ec2 describe-instances --filters "Name=tag:Environment,Values=prod" >prod-instances.json'
        aws_cmd, redirection = self.parser.parse_command(cmd)
        
        self.assertEqual(aws_cmd, 'aws ec2 describe-instances --filters "Name=tag:Environment,Values=prod"')
        self.assertEqual(redirection['type'], 'redirect')
        self.assertEqual(redirection['target'], 'prod-instances.json')
    
    def test_multiple_spaces_around_redirect(self):
        """Test redirection with multiple spaces."""
        cmd = "aws ec2 describe-instances    >    output.json"
        aws_cmd, redirection = self.parser.parse_command(cmd)
        
        self.assertEqual(aws_cmd, "aws ec2 describe-instances")
        self.assertEqual(redirection['target'], 'output.json')


class TestAutoPromptExecutor(unittest.TestCase):
    """Test cases for AutoPromptExecutor class."""
    
    def setUp(self):
        self.executor = AutoPromptExecutor()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_command_parsing_integration(self):
        """Test that the executor correctly parses commands."""
        cmd = "aws ec2 describe-instances >output.json"
        aws_cmd, redirection = self.executor.parser.parse_command(cmd)
        
        self.assertEqual(aws_cmd, "aws ec2 describe-instances")
        self.assertIsNotNone(redirection)
        self.assertEqual(redirection['type'], 'redirect')


def run_demo():
    """Run a demonstration of the shell redirection parser."""
    print("AWS CLI v2 Auto-Prompt Shell Redirection Demo")
    print("=" * 50)
    
    parser = ShellRedirectionParser()
    
    test_commands = [
        "aws ec2 describe-instances",
        "aws ec2 describe-instances >output.json",
        "aws ec2 describe-instances >>output.json", 
        "aws s3 ls 2>errors.log",
        "aws ec2 describe-instances &>combined.log",
        "aws ec2 describe-instances | jq '.Reservations[0]'",
        'aws s3 cp file.txt s3://bucket/key --metadata "description=>not a redirection"',
        'aws ec2 describe-instances --query "Reservations[*].Instances[*].InstanceId" --output text | head -5'
    ]
    
    for cmd in test_commands:
        print(f"\nInput Command:")
        print(f"  {cmd}")
        
        aws_cmd, redirection = parser.parse_command(cmd)
        
        print(f"Parsed AWS Command:")
        print(f"  {aws_cmd}")
        
        if redirection:
            print(f"Shell Redirection:")
            print(f"  Type: {redirection['type']}")
            print(f"  Target: {redirection['target']}")
            if redirection.get('append'):
                print(f"  Mode: append")
            if redirection.get('stderr'):
                print(f"  Stream: stderr")
            if redirection.get('both'):
                print(f"  Stream: both stdout and stderr")
        else:
            print("Shell Redirection: None")
        
        print("-" * 40)


if __name__ == "__main__":
    print("Running demonstration...")
    run_demo()
    
    print("\n\nRunning unit tests...")
    unittest.main(argv=[''], verbosity=2, exit=False)