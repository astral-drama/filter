"""Project management for Filter."""

import logging
import re
import shutil
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from .config import get_projects_directory, get_kanban_directory

logger = logging.getLogger(__name__)


def generate_project_prefix(project_name: str, target_length: int = 5) -> str:
    """Generate a short prefix from project name for story naming.
    
    Args:
        project_name: Full project name (e.g., 'ib-stream', 'marketbridge')
        target_length: Target length for prefix (default: 5)
        
    Returns:
        Short prefix suitable for story names (e.g., 'ibstr', 'mktbr')
        
    Examples:
        >>> generate_project_prefix('ib-stream')
        'ibstr'
        >>> generate_project_prefix('marketbridge')
        'mktbr'
        >>> generate_project_prefix('simple')
        'simpl'
    """
    # Remove special characters and convert to lowercase
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', project_name.lower())
    
    if len(clean_name) <= target_length:
        return clean_name
    
    # Try to use first letters of "words" (separated by hyphens, underscores, camelCase)
    words = re.findall(r'[a-z]+|[A-Z][a-z]*', project_name.lower())
    
    if len(words) > 1:
        # Use first 1-2 letters from each word
        letters_per_word = max(1, target_length // len(words))
        prefix_parts = []
        
        for word in words:
            prefix_parts.append(word[:letters_per_word])
        
        prefix = ''.join(prefix_parts)
        
        # If still too long, truncate
        if len(prefix) > target_length:
            prefix = prefix[:target_length]
        
        # If too short, pad with remaining letters from original
        if len(prefix) < target_length:
            remaining = target_length - len(prefix)
            for char in clean_name:
                if char not in prefix and remaining > 0:
                    prefix += char
                    remaining -= 1
                    
        return prefix[:target_length]
    
    # Single word or no word separation - just truncate
    return clean_name[:target_length]


def create_project_config(
    project_name: str,
    project_dir: Path,
    description: str = "",
    git_url: str = "",
    maintainers: List[str] = None
) -> Dict[str, Any]:
    """Create a project configuration file.
    
    Args:
        project_name: Name of the project
        project_dir: Path to project directory
        description: Project description
        git_url: Git repository URL
        maintainers: List of maintainer names/emails
        
    Returns:
        Dictionary containing the project configuration
    """
    if maintainers is None:
        maintainers = []
    
    config = {
        'name': project_name,
        'prefix': generate_project_prefix(project_name),
        'description': description,
        'git_url': git_url,
        'maintainers': maintainers,
        'created_at': None,  # Will be filled by YAML with timestamp
        'version': '1.0'
    }
    
    # Write config file
    config_file = project_dir / 'project.yaml'
    with open(config_file, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
    
    logger.info(f"Created project config at {config_file}")
    return config


def load_project_config(project_dir: Path) -> Optional[Dict[str, Any]]:
    """Load project configuration from project.yaml.
    
    Args:
        project_dir: Path to project directory
        
    Returns:
        Project configuration dictionary or None if not found
    """
    config_file = project_dir / 'project.yaml'
    
    if not config_file.exists():
        return None
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except yaml.YAMLError as e:
        logger.error(f"Error loading project config from {config_file}: {e}")
        return None


def list_projects(base_dir: Optional[Path] = None) -> List[str]:
    """List existing projects.
    
    Args:
        base_dir: Projects directory (defaults to configured projects directory)
        
    Returns:
        List of project names
    """
    if base_dir is None:
        base_dir = get_projects_directory()
    
    if not base_dir.exists():
        return []
    
    projects = []
    for item in base_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            projects.append(item.name)
    
    return sorted(projects)


def create_project(
    project_name: str,
    base_dir: Optional[Path] = None,
    copy_kanban: bool = True,
    description: str = "",
    git_url: str = "",
    maintainers: List[str] = None
) -> Path:
    """Create a new project with kanban structure.
    
    Args:
        project_name: Name of the project (e.g., 'ib-stream', 'marketbridge')
        base_dir: Projects directory (defaults to configured projects directory)
        copy_kanban: Whether to copy the base kanban structure
        description: Project description
        git_url: Git repository URL
        maintainers: List of maintainer names/emails
        
    Returns:
        Path to the created project directory
        
    Raises:
        RuntimeError: If project already exists or creation fails
    """
    if base_dir is None:
        base_dir = get_projects_directory()
    
    project_dir = base_dir / project_name
    
    if project_dir.exists():
        raise RuntimeError(f"Project '{project_name}' already exists at {project_dir}")
    
    # Create projects directory if it doesn't exist
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Create project directory
    project_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created project directory: {project_dir}")
    
    # Create project configuration file
    create_project_config(project_name, project_dir, description, git_url, maintainers)
    
    if copy_kanban:
        # Copy base kanban structure to project
        base_kanban = get_kanban_directory()
        project_kanban = project_dir / "kanban"
        
        if base_kanban.exists():
            shutil.copytree(base_kanban, project_kanban)
            logger.info(f"Copied kanban structure to {project_kanban}")
        else:
            # Create basic kanban structure if base doesn't exist
            create_basic_kanban_structure(project_kanban)
            logger.info(f"Created basic kanban structure at {project_kanban}")
    
    logger.info(f"Project '{project_name}' created successfully at {project_dir}")
    return project_dir


def create_basic_kanban_structure(kanban_dir: Path) -> None:
    """Create basic kanban directory structure.
    
    Args:
        kanban_dir: Path where kanban structure should be created
    """
    directories = [
        "planning",
        "in-progress", 
        "testing",
        "pr",
        "complete",
        "prompts",
        "stories"
    ]
    
    for dir_name in directories:
        dir_path = kanban_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Add .gitkeep files to keep empty directories in git
        gitkeep = dir_path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()


def delete_project(
    project_name: str,
    base_dir: Optional[Path] = None,
    force: bool = False
) -> None:
    """Delete a project and its contents.
    
    Args:
        project_name: Name of the project to delete
        base_dir: Projects directory (defaults to configured projects directory)
        force: If True, delete without confirmation prompts
        
    Raises:
        RuntimeError: If project doesn't exist or deletion fails
    """
    if base_dir is None:
        base_dir = get_projects_directory()
    
    project_dir = base_dir / project_name
    
    if not project_dir.exists():
        raise RuntimeError(f"Project '{project_name}' does not exist at {project_dir}")
    
    if not project_dir.is_dir():
        raise RuntimeError(f"'{project_name}' is not a directory")
    
    # Remove project directory and all contents
    shutil.rmtree(project_dir)
    logger.info(f"Deleted project '{project_name}' at {project_dir}")


def get_project_path(
    project_name: str,
    base_dir: Optional[Path] = None
) -> Path:
    """Get the path to a specific project.
    
    Args:
        project_name: Name of the project
        base_dir: Projects directory (defaults to configured projects directory)
        
    Returns:
        Path to the project directory
        
    Raises:
        RuntimeError: If project doesn't exist
    """
    if base_dir is None:
        base_dir = get_projects_directory()
    
    project_dir = base_dir / project_name
    
    if not project_dir.exists():
        raise RuntimeError(f"Project '{project_name}' does not exist at {project_dir}")
    
    return project_dir


def get_project_kanban_path(
    project_name: str,
    base_dir: Optional[Path] = None
) -> Path:
    """Get the path to a project's kanban directory.
    
    Args:
        project_name: Name of the project
        base_dir: Projects directory (defaults to configured projects directory)
        
    Returns:
        Path to the project's kanban directory
        
    Raises:
        RuntimeError: If project doesn't exist
    """
    project_dir = get_project_path(project_name, base_dir)
    return project_dir / "kanban"