"""Command execution utilities with auditing and logging."""

import subprocess
import os
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from .logging_config import get_logger, command_log, audit_log

logger = get_logger(__name__)


class CommandResult:
    """Result of a command execution."""
    
    def __init__(self, returncode: int, stdout: str, stderr: str, command: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.command = command
        self.success = returncode == 0
    
    def __str__(self):
        return f"CommandResult(returncode={self.returncode}, success={self.success})"
    
    def __repr__(self):
        return self.__str__()


def run_command(
    command: Union[str, List[str]],
    cwd: Optional[Union[str, Path]] = None,
    check: bool = True,
    capture_output: bool = True,
    text: bool = True,
    timeout: Optional[float] = None,
    env: Optional[Dict[str, str]] = None,
    audit: bool = True,
    sensitive: bool = False
) -> CommandResult:
    """Run a command with proper logging and auditing.
    
    Args:
        command: Command to run (string or list of arguments)
        cwd: Working directory for the command
        check: Whether to raise exception on non-zero exit code
        capture_output: Whether to capture stdout/stderr
        text: Whether to return strings (vs bytes)
        timeout: Command timeout in seconds
        env: Environment variables
        audit: Whether to log this command execution
        sensitive: Whether this command contains sensitive information
        
    Returns:
        CommandResult containing execution details
        
    Raises:
        subprocess.CalledProcessError: If check=True and command fails
        subprocess.TimeoutExpired: If command times out
    """
    # Convert command to string for logging
    if isinstance(command, list):
        command_str = ' '.join(str(arg) for arg in command)
        command_args = command
    else:
        command_str = command
        command_args = command
    
    # Determine working directory
    work_dir = str(Path(cwd).resolve()) if cwd else os.getcwd()
    
    # Log command execution (mask sensitive commands)
    if audit:
        if sensitive:
            log_command = "[SENSITIVE COMMAND REDACTED]"
            audit_log("Sensitive command executed", 
                     cwd=work_dir, 
                     user=os.getenv('USER', 'unknown'))
        else:
            log_command = command_str
            command_log(log_command, cwd=work_dir)
            audit_log("Command executed", 
                     command=log_command, 
                     cwd=work_dir, 
                     user=os.getenv('USER', 'unknown'))
    
    logger.debug(f"Executing command: {log_command if not sensitive else '[REDACTED]'}")
    logger.debug(f"Working directory: {work_dir}")
    
    try:
        # Execute the command
        result = subprocess.run(
            command_args,
            cwd=cwd,
            check=False,  # We'll handle check ourselves
            capture_output=capture_output,
            text=text,
            timeout=timeout,
            env=env
        )
        
        # Create our result object
        cmd_result = CommandResult(
            returncode=result.returncode,
            stdout=result.stdout if capture_output else "",
            stderr=result.stderr if capture_output else "",
            command=command_str
        )
        
        # Log result
        if cmd_result.success:
            logger.debug(f"Command succeeded: {log_command if not sensitive else '[REDACTED]'}")
            if audit and not sensitive:
                audit_log("Command completed successfully", 
                         command=log_command, 
                         returncode=cmd_result.returncode)
        else:
            logger.warning(f"Command failed with code {cmd_result.returncode}: {log_command if not sensitive else '[REDACTED]'}")
            if audit:
                audit_log("Command failed", 
                         command=log_command if not sensitive else '[REDACTED]', 
                         returncode=cmd_result.returncode,
                         stderr=cmd_result.stderr[:200] if not sensitive else '[REDACTED]')
        
        # Handle check flag
        if check and not cmd_result.success:
            raise subprocess.CalledProcessError(
                cmd_result.returncode, 
                command_args, 
                output=cmd_result.stdout, 
                stderr=cmd_result.stderr
            )
        
        return cmd_result
        
    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out after {timeout}s: {log_command if not sensitive else '[REDACTED]'}")
        if audit:
            audit_log("Command timed out", 
                     command=log_command if not sensitive else '[REDACTED]', 
                     timeout=timeout)
        raise
    except Exception as e:
        logger.error(f"Command execution failed: {log_command if not sensitive else '[REDACTED]'}: {e}")
        if audit:
            audit_log("Command execution error", 
                     command=log_command if not sensitive else '[REDACTED]', 
                     error=str(e))
        raise


def run_git_command(
    args: List[str],
    cwd: Optional[Union[str, Path]] = None,
    check: bool = True,
    sensitive: bool = False
) -> CommandResult:
    """Run a git command with proper logging.
    
    Args:
        args: Git command arguments (without 'git')
        cwd: Working directory for the command
        check: Whether to raise exception on non-zero exit code
        sensitive: Whether this command contains sensitive information
        
    Returns:
        CommandResult containing execution details
    """
    git_command = ['git'] + args
    return run_command(
        git_command,
        cwd=cwd,
        check=check,
        audit=True,
        sensitive=sensitive
    )


def run_docker_command(
    args: List[str],
    cwd: Optional[Union[str, Path]] = None,
    check: bool = True
) -> CommandResult:
    """Run a docker command with proper logging.
    
    Args:
        args: Docker command arguments (without 'docker')
        cwd: Working directory for the command
        check: Whether to raise exception on non-zero exit code
        
    Returns:
        CommandResult containing execution details
    """
    docker_command = ['docker'] + args
    return run_command(
        docker_command,
        cwd=cwd,
        check=check,
        audit=True
    )


def check_command_available(command: str) -> bool:
    """Check if a command is available in the system PATH.
    
    Args:
        command: Command name to check
        
    Returns:
        True if command is available, False otherwise
    """
    try:
        result = run_command(
            ['which', command],
            check=False,
            audit=False  # Don't audit availability checks
        )
        available = result.success
        logger.debug(f"Command '{command}' {'available' if available else 'not available'}")
        return available
    except Exception as e:
        logger.debug(f"Error checking command availability for '{command}': {e}")
        return False


def ensure_command_available(command: str, error_message: Optional[str] = None):
    """Ensure a command is available, raising an error if not.
    
    Args:
        command: Command name to check
        error_message: Custom error message if command not found
        
    Raises:
        RuntimeError: If command is not available
    """
    if not check_command_available(command):
        if error_message:
            raise RuntimeError(error_message)
        else:
            raise RuntimeError(f"Required command '{command}' not found. Please install {command}.")