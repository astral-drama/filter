"""Workspace functor for systematic transformations between workspace contexts.

This module implements the WorkspaceFunctor that enables mapping between
different workspace states and contexts while preserving structure.
"""

from typing import TypeVar, Generic, Callable, Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from ..types import (
    Workspace, WorkspaceState, 
    Created, Running, Stopped, Destroyed,
    CreatedWorkspace, RunningWorkspace, StoppedWorkspace
)
from ..command_algebra import FilterCommand, Effect, EffectType
from ..logging_config import get_logger

logger = get_logger(__name__)

# Type variables for functor operations
WS1 = TypeVar('WS1', bound=WorkspaceState)
WS2 = TypeVar('WS2', bound=WorkspaceState)
T = TypeVar('T')
U = TypeVar('U')


class WorkspaceFunctor(Generic[WS1]):
    """Functor for workspace transformations.
    
    Enables systematic mapping between workspace contexts while preserving
    the categorical structure of workspace operations.
    
    Satisfies functor laws:
    1. fmap(id) = id (identity preservation)
    2. fmap(g ∘ f) = fmap(g) ∘ fmap(f) (composition preservation)
    """
    
    def __init__(self, workspace: Workspace[WS1]):
        self.workspace = workspace
    
    def fmap(self, f: Callable[[Workspace[WS1]], Workspace[WS2]]) -> 'WorkspaceFunctor[WS2]':
        """Map a function over the workspace while preserving structure.
        
        This is the core functor operation that enables systematic
        transformation between workspace contexts.
        """
        transformed = f(self.workspace)
        return WorkspaceFunctor(transformed)
    
    def map_template(self, new_template: str) -> 'WorkspaceFunctor[WS1]':
        """Transform workspace to use a different template."""
        def transform(ws: Workspace[WS1]) -> Workspace[WS1]:
            return Workspace(
                name=ws.name,
                path=ws.path,
                template=new_template,
                story_name=ws.story_name,
                repository=ws.repository,
                ports=ws.ports,
                environment=ws.environment,
                created_at=ws.created_at
            )
        
        return self.fmap(transform)
    
    def map_environment(self, env_transform: Callable[[Dict[str, str]], Dict[str, str]]) -> 'WorkspaceFunctor[WS1]':
        """Transform workspace environment variables."""
        def transform(ws: Workspace[WS1]) -> Workspace[WS1]:
            new_env = env_transform(ws.environment)
            return Workspace(
                name=ws.name,
                path=ws.path,
                template=ws.template,
                story_name=ws.story_name,
                repository=ws.repository,
                ports=ws.ports,
                environment=new_env,
                created_at=ws.created_at
            )
        
        return self.fmap(transform)
    
    def map_ports(self, port_transform: Callable[[Dict[str, int]], Dict[str, int]]) -> 'WorkspaceFunctor[WS1]':
        """Transform workspace port mappings."""
        def transform(ws: Workspace[WS1]) -> Workspace[WS1]:
            new_ports = port_transform(ws.ports)
            return Workspace(
                name=ws.name,
                path=ws.path,
                template=ws.template,
                story_name=ws.story_name,
                repository=ws.repository,
                ports=new_ports,
                environment=ws.environment,
                created_at=ws.created_at
            )
        
        return self.fmap(transform)
    
    def bind(self, f: Callable[[Workspace[WS1]], 'WorkspaceFunctor[WS2]']) -> 'WorkspaceFunctor[WS2]':
        """Monadic bind operation for workspace transformations."""
        return f(self.workspace)
    
    def apply(self, f_functor: 'WorkspaceFunctor[Callable[[Workspace[WS1]], Workspace[WS2]]]') -> 'WorkspaceFunctor[WS2]':
        """Applicative apply operation."""
        f = f_functor.workspace
        return WorkspaceFunctor(f(self.workspace))
    
    def value(self) -> Workspace[WS1]:
        """Extract the workspace value."""
        return self.workspace
    
    def __repr__(self) -> str:
        return f"WorkspaceFunctor({self.workspace})"


# Workspace-specific transformation functions

def create_workspace_command(name: str, path: Path, template: str) -> FilterCommand[None, CreatedWorkspace]:
    """Command to create a new workspace in Created state."""
    def create_action(_: None) -> CreatedWorkspace:
        # Create directory structure
        path.mkdir(parents=True, exist_ok=True)
        workspace_dir = path / "workspace"
        workspace_dir.mkdir(exist_ok=True)
        
        logger.info(f"Created workspace directory structure at {path}")
        
        return Workspace[Created](
            name=name,
            path=path,
            template=template,
            created_at=datetime.now()
        )
    
    return FilterCommand(
        name="create_workspace",
        action=create_action,
        effects=[
            Effect(EffectType.FILESYSTEM, f"Create workspace directory at {path}"),
            Effect(EffectType.AUDIT, f"Workspace {name} created")
        ],
        description=f"Create workspace {name} with template {template}"
    )


def start_workspace_command() -> FilterCommand[CreatedWorkspace, RunningWorkspace]:
    """Command to start workspace containers (Created -> Running)."""
    def start_action(workspace: CreatedWorkspace) -> RunningWorkspace:
        # In real implementation, would start Docker containers
        logger.info(f"Starting workspace {workspace.name}")
        
        # Simulate port assignment
        ports = {
            "claude": 8001,
            "postgres": 5433
        }
        
        return Workspace[Running](
            name=workspace.name,
            path=workspace.path,
            template=workspace.template,
            story_name=workspace.story_name,
            repository=workspace.repository,
            ports=ports,
            environment=workspace.environment,
            created_at=workspace.created_at
        )
    
    return FilterCommand(
        name="start_workspace",
        action=start_action,
        effects=[
            Effect(EffectType.DOCKER, "Start workspace containers"),
            Effect(EffectType.NETWORK, "Allocate container ports"),
            Effect(EffectType.AUDIT, "Workspace started")
        ],
        description="Start workspace containers and allocate resources"
    )


def stop_workspace_command() -> FilterCommand[RunningWorkspace, StoppedWorkspace]:
    """Command to stop workspace containers (Running -> Stopped)."""
    def stop_action(workspace: RunningWorkspace) -> StoppedWorkspace:
        logger.info(f"Stopping workspace {workspace.name}")
        
        return Workspace[Stopped](
            name=workspace.name,
            path=workspace.path,
            template=workspace.template,
            story_name=workspace.story_name,
            repository=workspace.repository,
            ports={},  # Ports released
            environment=workspace.environment,
            created_at=workspace.created_at
        )
    
    return FilterCommand(
        name="stop_workspace",
        action=stop_action,
        effects=[
            Effect(EffectType.DOCKER, "Stop workspace containers"),
            Effect(EffectType.NETWORK, "Release container ports"),
            Effect(EffectType.AUDIT, "Workspace stopped")
        ],
        description="Stop workspace containers and release resources"
    )


# Functor utility functions

def workspace_functor(workspace: Workspace[WS1]) -> WorkspaceFunctor[WS1]:
    """Lift a workspace into the WorkspaceFunctor."""
    return WorkspaceFunctor(workspace)


def pure_workspace(workspace: Workspace[WS1]) -> WorkspaceFunctor[WS1]:
    """Applicative pure operation for workspaces."""
    return WorkspaceFunctor(workspace)


def sequence_workspace_transforms(*transforms: Callable[[Workspace], Workspace]) -> Callable[[Workspace], Workspace]:
    """Compose a sequence of workspace transformations."""
    def composed_transform(workspace: Workspace) -> Workspace:
        result = workspace
        for transform in transforms:
            result = transform(result)
        return result
    
    return composed_transform


# Example workspace transformation patterns

def add_story_context(story_name: str) -> Callable[[Workspace[WS1]], Workspace[WS1]]:
    """Add story context to a workspace."""
    def transform(workspace: Workspace[WS1]) -> Workspace[WS1]:
        return workspace.with_story(story_name)
    
    return transform


def add_environment_vars(**kwargs: str) -> Callable[[Workspace[WS1]], Workspace[WS1]]:
    """Add environment variables to a workspace."""
    def transform(workspace: Workspace[WS1]) -> Workspace[WS1]:
        new_env = {**workspace.environment, **kwargs}
        return Workspace(
            name=workspace.name,
            path=workspace.path,
            template=workspace.template,
            story_name=workspace.story_name,
            repository=workspace.repository,
            ports=workspace.ports,
            environment=new_env,
            created_at=workspace.created_at
        )
    
    return transform


# Testing and validation

def validate_functor_laws():
    """Validate that WorkspaceFunctor satisfies functor laws."""
    from pathlib import Path
    
    # Create test workspace
    test_workspace = Workspace[Created](
        name="test",
        path=Path("/tmp/test"),
        template="default"
    )
    
    functor = WorkspaceFunctor(test_workspace)
    
    # Test identity law: fmap(id) = id
    identity = lambda x: x
    identity_mapped = functor.fmap(identity)
    assert identity_mapped.workspace == functor.workspace, "Identity law violated"
    
    # Test composition law: fmap(g ∘ f) = fmap(g) ∘ fmap(f)
    f = add_story_context("test-story")
    g = add_environment_vars(TEST="true")
    
    # Direct composition
    composed = lambda ws: g(f(ws))
    direct_result = functor.fmap(composed)
    
    # Functor composition
    functor_result = functor.fmap(f).fmap(g)
    
    # Results should be equivalent
    assert direct_result.workspace.story_name == functor_result.workspace.story_name
    assert direct_result.workspace.environment == functor_result.workspace.environment
    
    logger.info("WorkspaceFunctor laws validated successfully")


if __name__ == "__main__":
    validate_functor_laws()
    print("WorkspaceFunctor module working correctly!")