"""Configuration management for Filter."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


def get_default_paths() -> Dict[str, str]:
    """Get platform-appropriate default paths for Filter directories.
    
    Returns:
        Dictionary with default paths for workspaces and projects
    """
    home = Path.home()
    
    # Use user's home directory with filter subdirectory
    filter_home = home / ".filter"
    
    return {
        "workspaces_directory": str(filter_home / "workspaces"),
        "projects_directory": str(filter_home / "projects"),
        "kanban_directory": ".filter/kanban"
    }


def find_filter_directory(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Find .filter/ directory by searching up the directory tree.
    
    Args:
        start_dir: Directory to start searching from (defaults to current working directory)
        
    Returns:
        Path to .filter/ directory if found, None otherwise
    """
    if start_dir is None:
        start_dir = Path.cwd()
    
    current = Path(start_dir).resolve()
    
    # Search up the directory tree for .filter directory
    while current != current.parent:
        filter_dir = current / ".filter"
        if filter_dir.exists() and filter_dir.is_dir():
            return filter_dir
        current = current.parent
    
    return None


def find_config_file(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Find config.yaml by searching up the directory tree.
    
    Searches for configuration files in this order:
    1. .filter/config.yaml (repository-specific)
    2. config.yaml (global filter installation)
    3. ~/.filter/config.yaml (user-specific)
    
    Args:
        start_dir: Directory to start searching from (defaults to current working directory)
        
    Returns:
        Path to config.yaml if found, None otherwise
    """
    if start_dir is None:
        start_dir = Path.cwd()
    
    current = Path(start_dir).resolve()
    
    # Search up the directory tree
    while current != current.parent:
        # First check for repository-specific config
        filter_config = current / ".filter" / "config.yaml"
        if filter_config.exists():
            return filter_config
            
        # Then check for global config
        config_path = current / "config.yaml"
        if config_path.exists():
            return config_path
        current = current.parent
    
    # Finally check user's home directory
    user_config = Path.home() / ".filter" / "config.yaml"
    if user_config.exists():
        return user_config
    
    return None


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load configuration from config.yaml.
    
    Args:
        config_path: Path to config file (if None, searches for it)
        
    Returns:
        Configuration dictionary with defaults applied
        
    Raises:
        yaml.YAMLError: If config.yaml is invalid
    """
    # Start with platform-appropriate defaults
    config = get_default_paths()
    
    if config_path is None:
        config_path = find_config_file()
    
    # If we found a config file, load and merge it with defaults
    if config_path is not None:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f) or {}
                # Merge file config over defaults
                config.update(file_config)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in {config_path}: {e}")
    
    return config


def get_workspaces_directory(config: Optional[Dict[str, Any]] = None) -> Path:
    """Get the workspaces directory from configuration.
    
    Args:
        config: Configuration dictionary (loads from file if None)
        
    Returns:
        Path to workspaces directory
    """
    if config is None:
        config = load_config()
    
    workspaces_dir = config.get('workspaces_directory', './workspaces')
    return Path(workspaces_dir).expanduser().resolve()


def get_templates_directory(config: Optional[Dict[str, Any]] = None) -> Path:
    """Get the docker templates directory from configuration.
    
    Templates are always from the main Filter installation, not repository-specific.
    
    Args:
        config: Configuration dictionary (loads from file if None)
        
    Returns:
        Path to docker templates directory
    """
    if config is None:
        config = load_config()
    
    # Find Filter installation root (where global config.yaml is located)
    # Skip .filter/config.yaml and look for global config
    current = Path.cwd()
    
    while current != current.parent:
        # Look for global config.yaml (not .filter/config.yaml)
        config_path = current / "config.yaml"
        if config_path.exists():
            project_root = config_path.parent
            templates_dir = config.get('templates_directory', 'docker/templates')
            templates_path = project_root / templates_dir
            if templates_path.exists():
                return templates_path.resolve()
        current = current.parent
    
    # Fallback: use relative to current Filter installation
    # This handles the case where we're running from the Filter source directory
    filter_installation = Path(__file__).parent.parent.parent
    templates_dir = config.get('templates_directory', 'docker/templates')
    return (filter_installation / templates_dir).resolve()


def get_projects_directory(config: Optional[Dict[str, Any]] = None) -> Path:
    """Get the projects directory from configuration.
    
    Args:
        config: Configuration dictionary (loads from file if None)
        
    Returns:
        Path to projects directory
    """
    if config is None:
        config = load_config()
    
    projects_dir = config.get('projects_directory', './projects')
    return Path(projects_dir).expanduser().resolve()


def get_kanban_directory(config: Optional[Dict[str, Any]] = None) -> Path:
    """Get the kanban directory from configuration.
    
    Searches for kanban directory in this order:
    1. .filter/kanban (repository-specific)
    2. ./kanban (legacy support)
    3. Configured kanban_directory
    
    Args:
        config: Configuration dictionary (loads from file if None)
        
    Returns:
        Path to kanban directory
    """
    if config is None:
        config = load_config()
    
    # First check for .filter/kanban in current repository
    filter_dir = find_filter_directory()
    if filter_dir:
        filter_kanban = filter_dir / "kanban"
        if filter_kanban.exists():
            return filter_kanban
    
    # Find project root (where config.yaml is located)
    config_path = find_config_file()
    if config_path is not None:
        project_root = config_path.parent
        kanban_dir = config.get('kanban_directory', './kanban')
        resolved_kanban = (project_root / kanban_dir).resolve()
        if resolved_kanban.exists():
            return resolved_kanban
    
    # Fallback to current directory kanban
    current_kanban = Path.cwd() / "kanban"
    if current_kanban.exists():
        return current_kanban
    
    # If no kanban directory exists, return the preferred .filter/kanban location
    if filter_dir:
        return filter_dir / "kanban"
    
    # Final fallback
    return Path.cwd() / ".filter" / "kanban"


def create_filter_directory(repo_path: Path, project_name: str = None, prefix: str = None) -> Path:
    """Create .filter directory structure in a repository.
    
    Args:
        repo_path: Path to the repository root
        project_name: Name of the project (defaults to repository directory name)
        prefix: Story prefix (auto-generated if not provided)
        
    Returns:
        Path to the created .filter directory
    """
    filter_dir = repo_path / ".filter"
    filter_dir.mkdir(exist_ok=True)
    
    # Create kanban structure
    kanban_dir = filter_dir / "kanban"
    create_kanban_structure(kanban_dir)
    
    # Create metadata file
    if project_name is None:
        project_name = repo_path.name
    
    if prefix is None:
        # Import here to avoid circular imports
        from .projects import generate_project_prefix
        prefix = generate_project_prefix(project_name)
    
    metadata = {
        "name": project_name,
        "prefix": prefix,
        "created_at": None,  # Will be filled by YAML
        "version": "1.0"
    }
    
    metadata_file = filter_dir / "metadata.yaml"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        yaml.safe_dump(metadata, f, default_flow_style=False, sort_keys=False)
    
    # Create basic repository-specific config
    repo_config = {
        "kanban_directory": ".filter/kanban",
        "git": {
            "auto_commit_stories": True,
            "branch_naming": f"{prefix}-{{story_number}}"
        }
    }
    
    config_file = filter_dir / "config.yaml"
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.safe_dump(repo_config, f, default_flow_style=False, sort_keys=False)
    
    return filter_dir


def create_kanban_structure(kanban_dir: Path) -> None:
    """Create standard kanban directory structure.
    
    Args:
        kanban_dir: Path where kanban structure should be created
    """
    directories = [
        "stories",
        "planning",
        "in-progress",
        "testing",
        "pr",
        "complete",
        "prompts"
    ]
    
    kanban_dir.mkdir(parents=True, exist_ok=True)
    
    for dir_name in directories:
        dir_path = kanban_dir / dir_name
        dir_path.mkdir(exist_ok=True)
        
        # Add .gitkeep files to keep empty directories in git
        gitkeep = dir_path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()


def is_filter_repository(repo_path: Path = None) -> bool:
    """Check if a repository has Filter initialized.
    
    Args:
        repo_path: Path to check (defaults to current directory)
        
    Returns:
        True if .filter directory exists
    """
    if repo_path is None:
        repo_path = Path.cwd()
    
    filter_dir = repo_path / ".filter"
    return filter_dir.exists() and filter_dir.is_dir()