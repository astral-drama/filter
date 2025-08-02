"""Project management for Filter."""

import logging
import shutil
from pathlib import Path
from typing import List, Optional

from .config import get_projects_directory, get_kanban_directory

logger = logging.getLogger(__name__)


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
    copy_kanban: bool = True
) -> Path:
    """Create a new project with kanban structure.
    
    Args:
        project_name: Name of the project (e.g., 'ib-stream', 'marketbridge')
        base_dir: Projects directory (defaults to configured projects directory)
        copy_kanban: Whether to copy the base kanban structure
        
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