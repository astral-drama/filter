"""Logging configuration for Filter."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import yaml


class FilterLogger:
    """Centralized logging configuration for Filter."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize logging configuration.
        
        Args:
            config: Logging configuration dictionary
        """
        self.config = config or {}
        self.audit_logger = None
        self.command_logger = None
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up logging configuration."""
        # Get logging configuration
        log_config = self.config.get('logging', {})
        
        # Set default log level
        log_level = log_config.get('level', 'INFO').upper()
        numeric_level = getattr(logging, log_level, logging.INFO)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Set up console handler
        self._setup_console_handler(log_config)
        
        # Set up file handler if configured
        self._setup_file_handler(log_config)
        
        # Set up audit logging
        self._setup_audit_logging(log_config)
        
        # Set up command logging
        self._setup_command_logging(log_config)
        
        # Configure third-party loggers
        self._configure_third_party_loggers(log_config)
    
    def _setup_console_handler(self, log_config: Dict[str, Any]):
        """Set up console logging handler."""
        console_config = log_config.get('console', {'enabled': True})
        
        if not console_config.get('enabled', True):
            return
        
        # Determine console level (can be different from main level)
        console_level = console_config.get('level', log_config.get('level', 'INFO')).upper()
        numeric_level = getattr(logging, console_level, logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(numeric_level)
        
        # Set console format
        console_format = console_config.get('format', 
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_formatter = logging.Formatter(console_format)
        console_handler.setFormatter(console_formatter)
        
        # Add handler to root logger
        logging.getLogger().addHandler(console_handler)
    
    def _setup_file_handler(self, log_config: Dict[str, Any]):
        """Set up file logging handler."""
        file_config = log_config.get('file', {})
        
        if not file_config.get('enabled', False):
            return
        
        # Get log file path
        log_file = file_config.get('path', 'filter.log')
        log_path = Path(log_file).expanduser().resolve()
        
        # Ensure log directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Determine file level
        file_level = file_config.get('level', log_config.get('level', 'DEBUG')).upper()
        numeric_level = getattr(logging, file_level, logging.DEBUG)
        
        # Create rotating file handler
        max_bytes = file_config.get('max_size_mb', 10) * 1024 * 1024
        backup_count = file_config.get('backup_count', 3)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setLevel(numeric_level)
        
        # Set file format (more detailed than console)
        file_format = file_config.get('format',
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s')
        file_formatter = logging.Formatter(file_format)
        file_handler.setFormatter(file_formatter)
        
        # Add handler to root logger
        logging.getLogger().addHandler(file_handler)
    
    def _setup_audit_logging(self, log_config: Dict[str, Any]):
        """Set up audit logging for sensitive operations."""
        audit_config = log_config.get('audit', {})
        
        if not audit_config.get('enabled', True):
            return
        
        # Create audit logger
        self.audit_logger = logging.getLogger('filter.audit')
        self.audit_logger.setLevel(logging.INFO)
        
        # Prevent propagation to avoid duplicate logs
        self.audit_logger.propagate = False
        
        # Get audit log file path
        audit_file = audit_config.get('path', 'filter-audit.log')
        audit_path = Path(audit_file).expanduser().resolve()
        
        # Ensure audit log directory exists
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create audit file handler
        max_bytes = audit_config.get('max_size_mb', 50) * 1024 * 1024
        backup_count = audit_config.get('backup_count', 10)
        
        audit_handler = logging.handlers.RotatingFileHandler(
            audit_path, maxBytes=max_bytes, backupCount=backup_count
        )
        audit_handler.setLevel(logging.INFO)
        
        # Audit format includes more context
        audit_format = audit_config.get('format',
            '%(asctime)s - AUDIT - %(message)s')
        audit_formatter = logging.Formatter(audit_format)
        audit_handler.setFormatter(audit_formatter)
        
        self.audit_logger.addHandler(audit_handler)
        
        # Also log audit events to console if enabled
        if audit_config.get('console', False):
            audit_console = logging.StreamHandler(sys.stderr)
            audit_console.setLevel(logging.INFO)
            audit_console.setFormatter(logging.Formatter('AUDIT: %(message)s'))
            self.audit_logger.addHandler(audit_console)
    
    def _setup_command_logging(self, log_config: Dict[str, Any]):
        """Set up command execution logging."""
        command_config = log_config.get('commands', {})
        
        if not command_config.get('enabled', True):
            return
        
        # Create command logger
        self.command_logger = logging.getLogger('filter.commands')
        self.command_logger.setLevel(logging.INFO)
        
        # Prevent propagation to avoid duplicate logs
        self.command_logger.propagate = False
        
        # Get command log file path
        command_file = command_config.get('path', 'filter-commands.log')
        command_path = Path(command_file).expanduser().resolve()
        
        # Ensure command log directory exists
        command_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create command file handler
        max_bytes = command_config.get('max_size_mb', 20) * 1024 * 1024
        backup_count = command_config.get('backup_count', 5)
        
        command_handler = logging.handlers.RotatingFileHandler(
            command_path, maxBytes=max_bytes, backupCount=backup_count
        )
        command_handler.setLevel(logging.INFO)
        
        # Command format includes execution context
        command_format = command_config.get('format',
            '%(asctime)s - CMD - %(message)s')
        command_formatter = logging.Formatter(command_format)
        command_handler.setFormatter(command_formatter)
        
        self.command_logger.addHandler(command_handler)
    
    def _configure_third_party_loggers(self, log_config: Dict[str, Any]):
        """Configure logging levels for third-party libraries."""
        third_party_config = log_config.get('third_party', {})
        
        # Default levels for common third-party libraries
        default_levels = {
            'urllib3': 'WARNING',
            'requests': 'WARNING',
            'docker': 'WARNING',
            'git': 'WARNING'
        }
        
        # Apply configured levels
        for logger_name, level in default_levels.items():
            configured_level = third_party_config.get(logger_name, level).upper()
            numeric_level = getattr(logging, configured_level, logging.WARNING)
            logging.getLogger(logger_name).setLevel(numeric_level)
    
    def audit_log(self, message: str, **kwargs):
        """Log an audit event.
        
        Args:
            message: Audit message
            **kwargs: Additional context fields
        """
        if self.audit_logger:
            # Add context to the message
            context_parts = []
            for key, value in kwargs.items():
                context_parts.append(f"{key}={value}")
            
            if context_parts:
                full_message = f"{message} | {' | '.join(context_parts)}"
            else:
                full_message = message
            
            self.audit_logger.info(full_message)
    
    def command_log(self, command: str, cwd: Optional[str] = None, user: Optional[str] = None):
        """Log a command execution.
        
        Args:
            command: Command being executed
            cwd: Current working directory
            user: User executing the command
        """
        if self.command_logger:
            import os
            context_parts = [
                f"cmd='{command}'",
                f"cwd={cwd or os.getcwd()}",
                f"user={user or os.getenv('USER', 'unknown')}",
                f"pid={os.getpid()}"
            ]
            
            message = " | ".join(context_parts)
            self.command_logger.info(message)


def get_default_logging_config() -> Dict[str, Any]:
    """Get default logging configuration.
    
    Returns:
        Default logging configuration dictionary
    """
    return {
        'logging': {
            'level': 'INFO',
            'console': {
                'enabled': True,
                'level': 'INFO',
                'format': '%(levelname)s: %(message)s'
            },
            'file': {
                'enabled': True,
                'path': '~/.filter/logs/filter.log',
                'level': 'DEBUG',
                'max_size_mb': 10,
                'backup_count': 3,
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            },
            'audit': {
                'enabled': True,
                'path': '~/.filter/logs/filter-audit.log',
                'max_size_mb': 50,
                'backup_count': 10,
                'console': False,
                'format': '%(asctime)s - AUDIT - %(message)s'
            },
            'commands': {
                'enabled': True,
                'path': '~/.filter/logs/filter-commands.log',
                'max_size_mb': 20,
                'backup_count': 5,
                'format': '%(asctime)s - CMD - %(message)s'
            },
            'third_party': {
                'urllib3': 'WARNING',
                'requests': 'WARNING',
                'docker': 'WARNING',
                'git': 'WARNING'
            }
        }
    }


def setup_logging(config: Optional[Dict[str, Any]] = None) -> FilterLogger:
    """Set up logging for Filter.
    
    Args:
        config: Configuration dictionary containing logging settings
        
    Returns:
        Configured FilterLogger instance
    """
    # Merge with default config
    default_config = get_default_logging_config()
    if config:
        # Merge provided config with defaults
        merged_config = default_config.copy()
        if 'logging' in config:
            merged_config['logging'].update(config['logging'])
        return FilterLogger(merged_config)
    else:
        return FilterLogger(default_config)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Global logger instance
_filter_logger: Optional[FilterLogger] = None


def get_filter_logger() -> FilterLogger:
    """Get the global Filter logger instance.
    
    Returns:
        Global FilterLogger instance
    """
    global _filter_logger
    if _filter_logger is None:
        from .config import load_config
        config = load_config()
        _filter_logger = FilterLogger(config)
    return _filter_logger


def audit_log(message: str, **kwargs):
    """Convenience function for audit logging.
    
    Args:
        message: Audit message
        **kwargs: Additional context fields
    """
    get_filter_logger().audit_log(message, **kwargs)


def command_log(command: str, cwd: Optional[str] = None, user: Optional[str] = None):
    """Convenience function for command logging.
    
    Args:
        command: Command being executed
        cwd: Current working directory
        user: User executing the command
    """
    get_filter_logger().command_log(command, cwd, user)