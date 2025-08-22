"""Input validation utilities for Filter operations.

This module provides validation functions for ensuring inputs are safe
and valid before being processed by categorical commands.
"""

import re
import urllib.parse
from pathlib import Path
from typing import List, Optional, Union


class ValidationError(Exception):
    """Raised when input validation fails."""
    
    def __init__(self, field: str, value: str, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Invalid {field} '{value}': {reason}")


class InputValidator:
    """Comprehensive input validation for Filter operations."""
    
    @staticmethod
    def validate_name(name: str, field: str = "name") -> str:
        """Validate a name field (alphanumeric, hyphens, underscores only).
        
        Args:
            name: The name to validate
            field: The field name for error messages
            
        Returns:
            The validated name
            
        Raises:
            ValidationError: If the name is invalid
        """
        if not name:
            raise ValidationError(field, name, "cannot be empty")
        
        if len(name) > 100:
            raise ValidationError(field, name, "cannot exceed 100 characters")
        
        # Allow alphanumeric, hyphens, and underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValidationError(
                field, name, 
                "must contain only alphanumeric characters, hyphens, and underscores"
            )
        
        # Must start with alphanumeric
        if not re.match(r'^[a-zA-Z0-9]', name):
            raise ValidationError(field, name, "must start with an alphanumeric character")
        
        return name
    
    @staticmethod
    def validate_path(path: Union[str, Path], field: str = "path", must_exist: bool = False) -> Path:
        """Validate a file path.
        
        Args:
            path: The path to validate
            field: The field name for error messages
            must_exist: Whether the path must already exist
            
        Returns:
            The validated Path object
            
        Raises:
            ValidationError: If the path is invalid
        """
        if isinstance(path, str):
            path = Path(path)
        
        # Check for dangerous path components
        path_str = str(path)
        if '..' in path_str:
            raise ValidationError(field, path_str, "cannot contain '..' (path traversal)")
        
        # Check for absolute paths when they shouldn't be
        if path.is_absolute() and not path_str.startswith(('/tmp', '/var/tmp')):
            # Only allow absolute paths for temp directories
            if not path_str.startswith(str(Path.cwd())):
                raise ValidationError(field, path_str, "absolute paths not allowed outside current directory")
        
        if must_exist and not path.exists():
            raise ValidationError(field, path_str, "must exist")
        
        # Check parent directory exists if creating new file/directory
        if not must_exist and path.parent != Path('.'):
            if not path.parent.exists():
                raise ValidationError(field, path_str, f"parent directory {path.parent} does not exist")
        
        return path
    
    @staticmethod
    def validate_url(url: str, field: str = "url") -> str:
        """Validate a URL.
        
        Args:
            url: The URL to validate
            field: The field name for error messages
            
        Returns:
            The validated URL
            
        Raises:
            ValidationError: If the URL is invalid
        """
        if not url:
            raise ValidationError(field, url, "cannot be empty")
        
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception:
            raise ValidationError(field, url, "invalid URL format")
        
        if not parsed.scheme:
            raise ValidationError(field, url, "must include scheme (http/https)")
        
        if parsed.scheme not in ['http', 'https']:
            raise ValidationError(field, url, "scheme must be http or https")
        
        if not parsed.netloc:
            raise ValidationError(field, url, "must include hostname")
        
        return url
    
    @staticmethod
    def validate_git_url(url: str, field: str = "git_url") -> str:
        """Validate a Git repository URL.
        
        Args:
            url: The Git URL to validate
            field: The field name for error messages
            
        Returns:
            The validated Git URL
            
        Raises:
            ValidationError: If the Git URL is invalid
        """
        if not url:
            raise ValidationError(field, url, "cannot be empty")
        
        # Handle different Git URL formats
        if url.startswith('git@'):
            # SSH format: git@github.com:user/repo.git
            if not re.match(r'^git@[a-zA-Z0-9.-]+:[a-zA-Z0-9._/-]+\.git$', url):
                raise ValidationError(field, url, "invalid SSH Git URL format")
        elif url.startswith(('http://', 'https://')):
            # HTTPS format: https://github.com/user/repo.git
            InputValidator.validate_url(url, field)
            if not (url.endswith('.git') or '/tree/' in url or '/blob/' in url):
                # Allow URLs without .git if they're GitHub/GitLab style
                if not re.search(r'github\.com|gitlab\.com|bitbucket\.org', url):
                    raise ValidationError(field, url, "Git URL should end with .git or be from a known Git host")
        else:
            raise ValidationError(field, url, "Git URL must use https:// or git@ format")
        
        return url
    
    @staticmethod
    def validate_priority(priority: str, field: str = "priority") -> str:
        """Validate a priority value.
        
        Args:
            priority: The priority to validate
            field: The field name for error messages
            
        Returns:
            The validated priority
            
        Raises:
            ValidationError: If the priority is invalid
        """
        valid_priorities = ['Low', 'Medium', 'High', 'Critical']
        
        if priority not in valid_priorities:
            raise ValidationError(
                field, priority, 
                f"must be one of: {', '.join(valid_priorities)}"
            )
        
        return priority
    
    @staticmethod
    def validate_template(template: str, field: str = "template") -> str:
        """Validate a workspace template name.
        
        Args:
            template: The template to validate
            field: The field name for error messages
            
        Returns:
            The validated template
            
        Raises:
            ValidationError: If the template is invalid
        """
        valid_templates = ['default', 'minimal', 'python']
        
        if template not in valid_templates:
            raise ValidationError(
                field, template,
                f"must be one of: {', '.join(valid_templates)}"
            )
        
        return template
    
    @staticmethod
    def validate_tags(tags: List[str], field: str = "tags") -> List[str]:
        """Validate a list of tags.
        
        Args:
            tags: The tags to validate
            field: The field name for error messages
            
        Returns:
            The validated tags
            
        Raises:
            ValidationError: If any tag is invalid
        """
        validated_tags = []
        
        for i, tag in enumerate(tags):
            if not tag:
                raise ValidationError(f"{field}[{i}]", tag, "cannot be empty")
            
            if len(tag) > 50:
                raise ValidationError(f"{field}[{i}]", tag, "cannot exceed 50 characters")
            
            # Allow alphanumeric, hyphens, and underscores
            if not re.match(r'^[a-zA-Z0-9_-]+$', tag):
                raise ValidationError(
                    f"{field}[{i}]", tag,
                    "must contain only alphanumeric characters, hyphens, and underscores"
                )
            
            validated_tags.append(tag)
        
        return validated_tags
    
    @staticmethod
    def validate_email(email: str, field: str = "email") -> str:
        """Validate an email address.
        
        Args:
            email: The email to validate
            field: The field name for error messages
            
        Returns:
            The validated email
            
        Raises:
            ValidationError: If the email is invalid
        """
        if not email:
            raise ValidationError(field, email, "cannot be empty")
        
        # Basic email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError(field, email, "invalid email format")
        
        return email


# Convenience functions for common validations

def validate_workspace_name(name: str) -> str:
    """Validate a workspace name."""
    return InputValidator.validate_name(name, "workspace_name")


def validate_story_name(name: str) -> str:
    """Validate a story name."""
    return InputValidator.validate_name(name, "story_name")


def validate_project_name(name: str) -> str:
    """Validate a project name."""
    return InputValidator.validate_name(name, "project_name")


def validate_workspace_path(path: Union[str, Path]) -> Path:
    """Validate a workspace path."""
    return InputValidator.validate_path(path, "workspace_path", must_exist=False)


def validate_story_path(path: Union[str, Path]) -> Path:
    """Validate a story file path."""
    return InputValidator.validate_path(path, "story_path", must_exist=False)