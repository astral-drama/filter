"""Configuration management for Filter."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


def find_config_file(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Find config.yaml by searching up the directory tree.
    
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
        config_path = current / "config.yaml"
        if config_path.exists():
            return config_path
        current = current.parent
    
    return None


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load configuration from config.yaml.
    
    Args:
        config_path: Path to config file (if None, searches for it)
        
    Returns:
        Configuration dictionary
        
    Raises:
        FileNotFoundError: If config.yaml cannot be found
        yaml.YAMLError: If config.yaml is invalid
    """
    if config_path is None:
        config_path = find_config_file()
        
    if config_path is None:
        raise FileNotFoundError(
            "config.yaml not found. Please ensure you're running from within "
            "a Filter project directory or specify the config path."
        )
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
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
    
    Args:
        config: Configuration dictionary (loads from file if None)
        
    Returns:
        Path to docker templates directory
    """
    if config is None:
        config = load_config()
    
    # Find project root (where config.yaml is located)
    config_path = find_config_file()
    if config_path is None:
        raise FileNotFoundError("config.yaml not found")
    
    project_root = config_path.parent
    templates_dir = config.get('templates_directory', 'docker/templates')
    
    return (project_root / templates_dir).resolve()


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
    
    Args:
        config: Configuration dictionary (loads from file if None)
        
    Returns:
        Path to kanban directory
    """
    if config is None:
        config = load_config()
    
    # Find project root (where config.yaml is located)
    config_path = find_config_file()
    if config_path is None:
        raise FileNotFoundError("config.yaml not found")
    
    project_root = config_path.parent
    kanban_dir = config.get('kanban_directory', './kanban')
    
    return (project_root / kanban_dir).resolve()