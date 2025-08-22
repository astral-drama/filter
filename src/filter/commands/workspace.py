"""Categorical workspace commands extracted from CLI.

This module provides composable workspace commands that follow
categorical composition laws and type safety.
"""

import os
import shutil
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..command_algebra import FilterCommand, Effect, EffectType, sequence
from ..command_utils import run_command, run_docker_command
from ..types import (
    Workspace, Created, Running, Stopped, Destroyed,
    CreatedWorkspace, RunningWorkspace, StoppedWorkspace
)
from ..functors.workspace import workspace_functor
from ..logging_config import get_logger
from ..validation import (
    validate_workspace_name, validate_workspace_path, 
    InputValidator, ValidationError
)
from ..operations import (
    WorkspaceFileOperations, WorkspaceDockerOperations,
    WorkspaceValidator, WorkspaceResourceManager
)

logger = get_logger(__name__)


@dataclass
class WorkspaceCreateArgs:
    """Arguments for workspace creation."""
    name: str
    template: str = "default"
    base_dir: Optional[Path] = None
    story_name: Optional[str] = None


@dataclass  
class WorkspaceConfig:
    """Workspace configuration data."""
    name: str
    ports: Dict[str, int]
    environment: Dict[str, str]
    template: str


class WorkspaceCommands:
    """Categorical workspace commands extracted from CLI."""
    
    @staticmethod
    def create() -> FilterCommand[WorkspaceCreateArgs, CreatedWorkspace]:
        """Create a new workspace in Created state."""
        def create_action(args: WorkspaceCreateArgs) -> CreatedWorkspace:
            # Validate inputs
            try:
                validated_name = validate_workspace_name(args.name)
                validated_template = InputValidator.validate_template(args.template)
                
                # Validate base directory if provided
                if args.base_dir:
                    validated_base_dir = validate_workspace_path(args.base_dir)
                else:
                    validated_base_dir = Path.cwd() / "workspaces"
                
                workspace_path = validated_base_dir / validated_name
                
                # Check if workspace already exists
                if workspace_path.exists():
                    raise ValidationError("workspace_path", str(workspace_path), "already exists")
                
                # Validate workspace requirements
                WorkspaceValidator.validate_workspace_requirements(workspace_path, validated_template)
                
            except ValidationError as e:
                logger.error(f"Validation failed for workspace creation: {e}")
                raise
            
            logger.info(f"Creating workspace: {validated_name}")
            
            # Use resource manager for automatic cleanup on failure
            with WorkspaceResourceManager() as resource_manager:
                try:
                    # Create directory structure
                    paths = WorkspaceFileOperations.create_directory_structure(workspace_path)
                    resource_manager.track_paths(paths)
                    
                    workspace_dir = workspace_path / "workspace"
                    
                    # Copy kanban structure
                    kanban_paths = WorkspaceFileOperations.copy_kanban_structure(workspace_dir)
                    resource_manager.track_paths(kanban_paths)
                    
                    # Generate Docker configuration
                    WorkspaceDockerOperations.create_docker_config(workspace_path, validated_template)
                    
                    # Create environment file
                    WorkspaceFileOperations.create_environment_file(
                        workspace_dir, validated_name, validated_template, args.story_name
                    )
                    
                    logger.info(f"Workspace {validated_name} created at {workspace_path}")
                    
                    # Success - don't cleanup
                    resource_manager.created_paths.clear()
                    
                except Exception as e:
                    logger.error(f"Workspace creation failed: {e}")
                    raise
            
            return Workspace[Created](
                name=validated_name,
                path=workspace_path,
                template=validated_template,
                story_name=args.story_name
            )
        
        return FilterCommand(
            name="workspace_create",
            action=create_action,
            effects=[
                Effect(EffectType.FILESYSTEM, "Create workspace directory structure"),
                Effect(EffectType.CONFIG, "Generate Docker configuration"),
                Effect(EffectType.AUDIT, "Workspace created")
            ],
            description="Create a new workspace with the specified template"
        )
    
    @staticmethod
    def start() -> FilterCommand[CreatedWorkspace, RunningWorkspace]:
        """Start workspace containers (Created -> Running)."""
        def start_action(workspace: CreatedWorkspace) -> RunningWorkspace:
            logger.info(f"Starting workspace: {workspace.name}")
            
            try:
                # Find available ports
                ports = WorkspaceDockerOperations.allocate_ports(workspace.template)
                
                # Update docker-compose with ports
                try:
                    WorkspaceDockerOperations.update_docker_ports(workspace.path, ports)
                except Exception as e:
                    logger.error(f"Failed to update Docker ports: {e}")
                    raise RuntimeError(f"Port configuration failed: {e}") from e
                
                # Start Docker containers
                try:
                    result = run_docker_command(
                        ["compose", "up", "-d"],
                        cwd=workspace.path
                    )
                    
                    if not result.success:
                        # Try to get more detailed error information
                        logs_result = run_docker_command(
                            ["compose", "logs"], 
                            cwd=workspace.path, 
                            check=False
                        )
                        error_details = logs_result.stdout if logs_result.success else "No logs available"
                        
                        raise RuntimeError(
                            f"Failed to start workspace containers: {result.stderr}\n"
                            f"Container logs: {error_details}"
                        )
                
                except Exception as e:
                    logger.error(f"Docker startup failed: {e}")
                    # Try to cleanup any partially started containers
                    try:
                        cleanup_result = run_docker_command(
                            ["compose", "down"], 
                            cwd=workspace.path, 
                            check=False
                        )
                        if cleanup_result.success:
                            logger.info("Cleaned up partial container startup")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup containers: {cleanup_error}")
                    raise
                
                logger.info(f"Workspace {workspace.name} started successfully")
                
            except Exception as e:
                logger.error(f"Failed to start workspace {workspace.name}: {e}")
                raise
            
            return Workspace[Running](
                name=workspace.name,
                path=workspace.path,
                template=workspace.template,
                story_name=workspace.story_name,
                ports=ports,
                environment=workspace.environment,
                created_at=workspace.created_at
            )
        
        return FilterCommand(
            name="workspace_start",
            action=start_action,
            effects=[
                Effect(EffectType.DOCKER, "Start workspace containers"),
                Effect(EffectType.NETWORK, "Allocate container ports"),
                Effect(EffectType.AUDIT, "Workspace started")
            ],
            description="Start workspace containers and allocate resources"
        )
    
    @staticmethod
    def stop() -> FilterCommand[RunningWorkspace, StoppedWorkspace]:
        """Stop workspace containers (Running -> Stopped)."""
        def stop_action(workspace: RunningWorkspace) -> StoppedWorkspace:
            logger.info(f"Stopping workspace: {workspace.name}")
            
            # Stop Docker containers
            result = run_docker_command(
                ["compose", "down"],
                cwd=workspace.path
            )
            
            if not result.success:
                logger.warning(f"Error stopping workspace: {result.stderr}")
            
            logger.info(f"Workspace {workspace.name} stopped")
            
            return Workspace[Stopped](
                name=workspace.name,
                path=workspace.path,
                template=workspace.template,
                story_name=workspace.story_name,
                ports={},  # Ports released
                environment=workspace.environment,
                created_at=workspace.created_at
            )
        
        return FilterCommand(
            name="workspace_stop",
            action=stop_action,
            effects=[
                Effect(EffectType.DOCKER, "Stop workspace containers"),
                Effect(EffectType.NETWORK, "Release container ports"),
                Effect(EffectType.AUDIT, "Workspace stopped")
            ],
            description="Stop workspace containers and release resources"
        )
    
    @staticmethod
    def delete() -> FilterCommand[StoppedWorkspace, None]:
        """Delete a stopped workspace."""
        def delete_action(workspace: StoppedWorkspace) -> None:
            logger.info(f"Deleting workspace: {workspace.name}")
            
            # Remove workspace directory
            if workspace.path.exists():
                shutil.rmtree(workspace.path)
            
            logger.info(f"Workspace {workspace.name} deleted")
            return None
        
        return FilterCommand(
            name="workspace_delete",
            action=delete_action,
            effects=[
                Effect(EffectType.FILESYSTEM, "Remove workspace directory"),
                Effect(EffectType.AUDIT, "Workspace deleted")
            ],
            description="Delete workspace directory and all contents"
        )
    
    @staticmethod
    def force_delete() -> FilterCommand[Workspace, None]:
        """Force delete a workspace in any state."""
        def force_delete_action(workspace: Workspace) -> None:
            logger.info(f"Force deleting workspace: {workspace.name}")
            
            # Try to stop containers first
            try:
                run_docker_command(
                    ["compose", "down", "-v"],
                    cwd=workspace.path,
                    check=False
                )
            except Exception as e:
                logger.warning(f"Error stopping containers during force delete: {e}")
            
            # Remove workspace directory
            if workspace.path.exists():
                shutil.rmtree(workspace.path)
            
            logger.info(f"Workspace {workspace.name} force deleted")
            return None
        
        return FilterCommand(
            name="workspace_force_delete",
            action=force_delete_action,
            effects=[
                Effect(EffectType.DOCKER, "Force stop containers"),
                Effect(EffectType.FILESYSTEM, "Remove workspace directory"),
                Effect(EffectType.AUDIT, "Workspace force deleted")
            ],
            description="Force delete workspace regardless of state"
        )
    
    # Note: Helper methods moved to operations.workspace_operations module
    # for better separation of concerns and maintainability


# Composable workspace workflows

def create_and_start_workspace() -> FilterCommand[WorkspaceCreateArgs, RunningWorkspace]:
    """Composite command to create and start a workspace."""
    create_cmd = WorkspaceCommands.create()
    start_cmd = WorkspaceCommands.start()
    
    return create_cmd.compose(start_cmd)


def stop_and_delete_workspace() -> FilterCommand[RunningWorkspace, None]:
    """Composite command to stop and delete a workspace.""" 
    stop_cmd = WorkspaceCommands.stop()
    delete_cmd = WorkspaceCommands.delete()
    
    return stop_cmd.compose(delete_cmd)


# Command pipeline for workspace lifecycle
def workspace_lifecycle_pipeline(create_args: WorkspaceCreateArgs) -> FilterCommand[None, None]:
    """Full workspace lifecycle: create -> start -> stop -> delete."""
    create_cmd = WorkspaceCommands.create().map_input(lambda _: create_args)
    start_cmd = WorkspaceCommands.start()
    stop_cmd = WorkspaceCommands.stop()
    delete_cmd = WorkspaceCommands.delete()
    
    pipeline = sequence(create_cmd, start_cmd, stop_cmd, delete_cmd)
    return pipeline.compose()


if __name__ == "__main__":
    # Test workspace commands
    from pathlib import Path
    
    args = WorkspaceCreateArgs(
        name="test-workspace",
        template="minimal",
        base_dir=Path("/tmp/test-workspaces")
    )
    
    # Test command composition
    create_cmd = WorkspaceCommands.create()
    workspace = create_cmd(args)
    
    print(f"Created workspace: {workspace.name} at {workspace.path}")
    print("Workspace commands module working correctly!")