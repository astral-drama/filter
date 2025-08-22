"""Workspace file and Docker operations.

This module contains the actual implementation of workspace operations,
separated from the command interface for better maintainability.
"""

import shutil
import yaml
from pathlib import Path
from typing import Dict, List

from ..logging_config import get_logger

logger = get_logger(__name__)


class WorkspaceFileOperations:
    """Handles file system operations for workspaces."""
    
    @staticmethod
    def create_directory_structure(workspace_path: Path) -> List[Path]:
        """Create workspace directory structure.
        
        Returns:
            List of created paths for cleanup on failure
        """
        created_paths = []
        
        workspace_path.mkdir(parents=True, exist_ok=True)
        created_paths.append(workspace_path)
        
        workspace_dir = workspace_path / "workspace"
        workspace_dir.mkdir(exist_ok=True)
        created_paths.append(workspace_dir)
        
        return created_paths
    
    @staticmethod
    def copy_kanban_structure(workspace_dir: Path) -> List[Path]:
        """Copy kanban structure to workspace.
        
        Returns:
            List of copied paths for cleanup on failure
        """
        created_paths = []
        
        kanban_dir = workspace_dir / "kanban"
        kanban_dir.mkdir(exist_ok=True)
        created_paths.append(kanban_dir)
        
        # Copy kanban structure from source
        source_kanban = Path.cwd() / "kanban"
        if source_kanban.exists():
            for item in source_kanban.iterdir():
                target_path = kanban_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, target_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target_path)
                created_paths.append(target_path)
        
        return created_paths
    
    @staticmethod
    def create_environment_file(workspace_dir: Path, workspace_name: str, template: str, story_name: str = None) -> None:
        """Create environment file for the workspace."""
        env_vars = {
            "WORKSPACE_NAME": workspace_name,
            "WORKSPACE_TEMPLATE": template
        }
        
        if story_name:
            env_vars["STORY_NAME"] = story_name
        
        env_content = "\n".join(f"{k}={v}" for k, v in env_vars.items())
        (workspace_dir / ".env").write_text(env_content)
    
    @staticmethod
    def cleanup_paths(paths: List[Path]) -> None:
        """Clean up created paths in reverse order."""
        for path in reversed(paths):
            try:
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    logger.debug(f"Cleaned up: {path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup {path}: {cleanup_error}")


class WorkspaceDockerOperations:
    """Handles Docker-related operations for workspaces."""
    
    @staticmethod
    def create_docker_config(workspace_path: Path, template: str) -> None:
        """Create Docker configuration files for the workspace."""
        docker_dir = Path(__file__).parent.parent.parent.parent / "docker"
        template_dir = docker_dir / "templates" / template
        
        if not template_dir.exists():
            logger.warning(f"Template {template} not found, using default")
            template_dir = docker_dir / "templates" / "default"
        
        # Copy template files
        for template_file in template_dir.glob("*"):
            if template_file.is_file():
                shutil.copy2(template_file, workspace_path / template_file.name)
    
    @staticmethod
    def allocate_ports(template: str) -> Dict[str, int]:
        """Allocate available ports for the workspace."""
        # Simple port allocation - in production, this would check for conflicts
        base_port = 8000
        
        ports = {"claude": base_port + 1}
        
        if template in ["default", "python"]:
            ports["postgres"] = 5433
        
        if template == "python":
            ports["jupyter"] = 8888
        
        return ports
    
    @staticmethod
    def update_docker_ports(workspace_path: Path, ports: Dict[str, int]) -> None:
        """Update docker-compose.yml with allocated ports."""
        compose_file = workspace_path / "docker-compose.yml"
        
        if not compose_file.exists():
            return
        
        # Read and update docker-compose configuration
        with open(compose_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Update port mappings
        if 'services' in config:
            for service_name, port in ports.items():
                if service_name in config['services']:
                    service = config['services'][service_name]
                    if 'ports' in service:
                        # Update the host port while keeping container port
                        original_ports = service['ports'][0] if service['ports'] else "8000:8000"
                        container_port = original_ports.split(':')[1] if ':' in original_ports else "8000"
                        service['ports'] = [f"{port}:{container_port}"]
        
        # Write updated configuration
        with open(compose_file, 'w') as f:
            yaml.safe_dump(config, f, default_flow_style=False)


class WorkspaceValidator:
    """Validates workspace-specific requirements."""
    
    @staticmethod
    def validate_workspace_requirements(workspace_path: Path, template: str) -> None:
        """Validate workspace-specific requirements."""
        # Check if Docker is available
        docker_check = shutil.which('docker')
        if not docker_check:
            raise RuntimeError("Docker is required but not found in PATH")
        
        # Check template-specific requirements
        if template == "python":
            # Could check for Python-specific requirements
            pass
        elif template == "default":
            # Could check for default template requirements
            pass
    
    @staticmethod
    def validate_template_exists(template: str) -> bool:
        """Check if template directory exists."""
        docker_dir = Path(__file__).parent.parent.parent.parent / "docker"
        template_dir = docker_dir / "templates" / template
        return template_dir.exists()


class WorkspaceResourceManager:
    """Manages workspace resources and cleanup."""
    
    def __init__(self):
        self.created_paths: List[Path] = []
        self.allocated_ports: Dict[str, int] = {}
        self.started_containers: List[str] = []
    
    def track_path(self, path: Path) -> None:
        """Track a created path for cleanup."""
        self.created_paths.append(path)
    
    def track_paths(self, paths: List[Path]) -> None:
        """Track multiple created paths for cleanup."""
        self.created_paths.extend(paths)
    
    def track_ports(self, ports: Dict[str, int]) -> None:
        """Track allocated ports."""
        self.allocated_ports.update(ports)
    
    def track_container(self, container_name: str) -> None:
        """Track a started container."""
        self.started_containers.append(container_name)
    
    def cleanup_all(self) -> None:
        """Clean up all tracked resources."""
        # Clean up containers first
        if self.started_containers:
            logger.info(f"Stopping containers: {self.started_containers}")
            # Container cleanup would go here
        
        # Clean up files
        if self.created_paths:
            WorkspaceFileOperations.cleanup_paths(self.created_paths)
        
        # Reset tracking
        self.created_paths.clear()
        self.allocated_ports.clear()
        self.started_containers.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Cleanup on exception
            self.cleanup_all()