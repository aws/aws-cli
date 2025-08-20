#!/usr/bin/env python3
"""
Shell Redirection Parser for AWS CLI v2 Auto-Prompt Mode

This module provides functionality to detect and handle shell redirection
operators in auto-prompt mode, allowing output redirection to work as expected.
"""

import re
import shlex
import subprocess
import sys
from typing import List, Tuple, Optional, Dict


class ShellRedirectionParser:
    """
    Parses command input to separate AWS CLI commands from shell redirection operators.
    """
    
    # Shell redirection operators to detect
    REDIRECTION_PATTERNS = [
        r'(?<!\\)>>?',      # > or >> (stdout redirect)
        r'(?<!\\)2>>?',     # 2> or 2>> (stderr redirect)
        r'(?<!\\)&>>?',     # &> or &>> (both stdout and stderr)
        r'(?<!\\)\|',       # | (pipe)
    ]
    
    def __init__(self):
        self.redirection_regex = re.compile('|'.join(self.REDIRECTION_PATTERNS))
    
    def parse_command(self, command_input: str) -> Tuple[str, Optional[Dict]]:
        """
        Parse command input to separate AWS CLI command from shell redirections.
        
        Args:
            command_input: Raw command input from user
            
        Returns:
            Tuple of (aws_command, redirection_info)
            redirection_info is None if no redirection detected
        """
        # Check if we have any redirection operators
        if not self._has_redirection(command_input):
            return command_input.strip(), None
        
        try:
            # Parse the command carefully, respecting quotes
            return self._parse_with_quotes(command_input)
        except Exception as e:
            # Fall back to simple parsing if complex parsing fails
            return self._simple_parse(command_input)
    
    def _has_redirection(self, command: str) -> bool:
        """Check if command contains shell redirection operators."""
        # First pass: simple regex check
        if not self.redirection_regex.search(command):
            return False
        
        # Second pass: check if it's inside quotes
        try:
            tokens = shlex.split(command)
            # Reconstruct without quotes and check again
            unquoted = ' '.join(tokens)
            return self.redirection_regex.search(unquoted) is not None
        except ValueError:
            # If shlex fails, be conservative and assume redirection exists
            return True
    
    def _parse_with_quotes(self, command: str) -> Tuple[str, Optional[Dict]]:
        """
        Parse command while respecting quoted strings.
        """
        # Find redirection operators that are not inside quotes
        in_quotes = False
        quote_char = None
        redirection_pos = None
        
        i = 0
        while i < len(command):
            char = command[i]
            
            # Handle quotes
            if char in ['"', "'"] and (i == 0 or command[i-1] != '\\'):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
            
            # Look for redirection operators outside quotes
            elif not in_quotes:
                match = self.redirection_regex.match(command, i)
                if match:
                    redirection_pos = i
                    break
            
            i += 1
        
        if redirection_pos is None:
            return command.strip(), None
        
        # Split at the redirection operator
        aws_command = command[:redirection_pos].strip()
        redirection_part = command[redirection_pos:].strip()
        
        # Parse the redirection part
        redirection_info = self._parse_redirection(redirection_part)
        
        return aws_command, redirection_info
    
    def _simple_parse(self, command: str) -> Tuple[str, Optional[Dict]]:
        """
        Simple parsing fallback for when complex parsing fails.
        """
        # Find the first redirection operator
        match = self.redirection_regex.search(command)
        if not match:
            return command.strip(), None
        
        split_pos = match.start()
        aws_command = command[:split_pos].strip()
        redirection_part = command[split_pos:].strip()
        
        redirection_info = self._parse_redirection(redirection_part)
        
        return aws_command, redirection_info
    
    def _parse_redirection(self, redirection: str) -> Dict:
        """
        Parse redirection operators and their targets.
        """
        redirection_info = {
            'type': None,
            'target': None,
            'append': False,
            'stderr': False,
            'both': False
        }
        
        # Determine redirection type
        if redirection.startswith('>>'):
            redirection_info['type'] = 'redirect'
            redirection_info['append'] = True
            redirection_info['target'] = redirection[2:].strip()
        elif redirection.startswith('>'):
            redirection_info['type'] = 'redirect'
            redirection_info['target'] = redirection[1:].strip()
        elif redirection.startswith('2>>'):
            redirection_info['type'] = 'redirect'
            redirection_info['stderr'] = True
            redirection_info['append'] = True
            redirection_info['target'] = redirection[3:].strip()
        elif redirection.startswith('2>'):
            redirection_info['type'] = 'redirect'
            redirection_info['stderr'] = True
            redirection_info['target'] = redirection[2:].strip()
        elif redirection.startswith('&>>'):
            redirection_info['type'] = 'redirect'
            redirection_info['both'] = True
            redirection_info['append'] = True
            redirection_info['target'] = redirection[3:].strip()
        elif redirection.startswith('&>'):
            redirection_info['type'] = 'redirect'
            redirection_info['both'] = True
            redirection_info['target'] = redirection[2:].strip()
        elif redirection.startswith('|'):
            redirection_info['type'] = 'pipe'
            redirection_info['target'] = redirection[1:].strip()
        
        return redirection_info


class AutoPromptExecutor:
    """
    Executes AWS CLI commands with shell redirection support.
    """
    
    def __init__(self):
        self.parser = ShellRedirectionParser()
    
    def execute_command(self, command_input: str) -> int:
        """
        Execute command with shell redirection support.
        
        Args:
            command_input: Raw command input from user
            
        Returns:
            Exit code (0 for success)
        """
        aws_command, redirection_info = self.parser.parse_command(command_input)
        
        if redirection_info is None:
            # No redirection, execute normally through auto-prompt
            return self._execute_aws_command(aws_command)
        
        # Handle redirection
        if redirection_info['type'] == 'redirect':
            return self._execute_with_file_redirection(aws_command, redirection_info)
        elif redirection_info['type'] == 'pipe':
            return self._execute_with_pipe(aws_command, redirection_info)
        else:
            # Unknown redirection type, fall back to normal execution
            return self._execute_aws_command(aws_command)
    
    def _execute_aws_command(self, command: str) -> int:
        """
        Execute AWS CLI command through normal auto-prompt processing.
        
        This is a placeholder - in the actual implementation, this would
        call the existing auto-prompt command execution logic.
        """
        # Placeholder implementation
        print(f"Executing AWS command: {command}")
        
        # In real implementation, this would be:
        # return auto_prompt_execute(command)
        
        # For demo purposes, simulate command execution
        try:
            # Split command into parts for subprocess
            cmd_parts = shlex.split(command)
            result = subprocess.run(cmd_parts, capture_output=True, text=True)
            return result.returncode
        except Exception as e:
            print(f"Error executing command: {e}", file=sys.stderr)
            return 1
    
    def _execute_with_file_redirection(self, aws_command: str, redirection_info: Dict) -> int:
        """
        Execute AWS command and redirect output to file.
        """
        try:
            # Execute AWS command and capture output
            cmd_parts = shlex.split(aws_command)
            result = subprocess.run(cmd_parts, capture_output=True, text=True)
            
            # Handle redirection based on type
            mode = 'a' if redirection_info['append'] else 'w'
            target_file = redirection_info['target']
            
            with open(target_file, mode) as f:
                if redirection_info['stderr'] or redirection_info['both']:
                    f.write(result.stderr)
                if not redirection_info['stderr'] or redirection_info['both']:
                    f.write(result.stdout)
            
            # Print to console if not redirecting stdout
            if redirection_info['stderr'] and not redirection_info['both']:
                print(result.stdout, end='')
            elif not redirection_info['stderr'] and not redirection_info['both']:
                print(result.stderr, end='', file=sys.stderr)
            
            return result.returncode
            
        except Exception as e:
            print(f"Error with file redirection: {e}", file=sys.stderr)
            return 1
    
    def _execute_with_pipe(self, aws_command: str, redirection_info: Dict) -> int:
        """
        Execute AWS command and pipe output to another command.
        """
        try:
            # Execute AWS command
            cmd_parts = shlex.split(aws_command)
            aws_proc = subprocess.Popen(cmd_parts, stdout=subprocess.PIPE, text=True)
            
            # Execute pipe target command
            pipe_command = redirection_info['target']
            pipe_parts = shlex.split(pipe_command)
            pipe_proc = subprocess.Popen(pipe_parts, stdin=aws_proc.stdout, text=True)
            
            # Close AWS stdout to allow pipe target to receive EOF
            aws_proc.stdout.close()
            
            # Wait for both processes to complete
            pipe_proc.wait()
            aws_proc.wait()
            
            return pipe_proc.returncode
            
        except Exception as e:
            print(f"Error with pipe: {e}", file=sys.stderr)
            return 1


def demo_usage():
    """Demonstrate the shell redirection parser."""
    executor = AutoPromptExecutor()
    
    test_commands = [
        "aws ec2 describe-instances",
        "aws ec2 describe-instances >output.json",
        "aws ec2 describe-instances >>output.json", 
        "aws s3 ls 2>errors.log",
        "aws ec2 describe-instances &>combined.log",
        "aws ec2 describe-instances | jq '.Reservations[0]'",
        'aws s3 cp file.txt s3://bucket/key --metadata "description=>not a redirection"'
    ]
    
    for cmd in test_commands:
        print(f"\nInput: {cmd}")
        aws_cmd, redirection = executor.parser.parse_command(cmd)
        print(f"AWS Command: {aws_cmd}")
        print(f"Redirection: {redirection}")


if __name__ == "__main__":
    demo_usage()