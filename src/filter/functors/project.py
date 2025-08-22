"""Project functor for systematic transformations between project contexts.

This module implements the ProjectFunctor that enables mapping between
different project states and contexts while preserving structure.
"""

from typing import TypeVar, Generic, Callable, List
from pathlib import Path

from ..types import (
    Project, ProjectState,
    Empty, Populated, Active,
    EmptyProject, PopulatedProject, ActiveProject
)
from ..command_algebra import FilterCommand, Effect, EffectType
from ..logging_config import get_logger

logger = get_logger(__name__)

# Type variables for functor operations
PS1 = TypeVar('PS1', bound=ProjectState)
PS2 = TypeVar('PS2', bound=ProjectState)
T = TypeVar('T')
U = TypeVar('U')


class ProjectFunctor(Generic[PS1]):
    """Functor for project transformations.
    
    Enables systematic mapping between project contexts while preserving
    the categorical structure of project operations.
    
    Satisfies functor laws:
    1. fmap(id) = id (identity preservation)
    2. fmap(g ∘ f) = fmap(g) ∘ fmap(f) (composition preservation)
    """
    
    def __init__(self, project: Project[PS1]):
        self.project = project
    
    def fmap(self, f: Callable[[Project[PS1]], Project[PS2]]) -> 'ProjectFunctor[PS2]':
        """Map a function over the project while preserving structure.
        
        This is the core functor operation that enables systematic
        transformation between project contexts.
        """
        transformed = f(self.project)
        return ProjectFunctor(transformed)
    
    def map_description(self, new_description: str) -> 'ProjectFunctor[PS1]':
        """Transform project description."""
        def transform(project: Project[PS1]) -> Project[PS1]:
            return Project(
                name=project.name,
                path=project.path,
                prefix=project.prefix,
                description=new_description,
                git_url=project.git_url,
                maintainers=project.maintainers,
                created_at=project.created_at
            )
        
        return self.fmap(transform)
    
    def map_git_url(self, git_url: str) -> 'ProjectFunctor[PS1]':
        """Transform project git URL."""
        def transform(project: Project[PS1]) -> Project[PS1]:
            return Project(
                name=project.name,
                path=project.path,
                prefix=project.prefix,
                description=project.description,
                git_url=git_url,
                maintainers=project.maintainers,
                created_at=project.created_at
            )
        
        return self.fmap(transform)
    
    def map_maintainers(self, maintainer_transform: Callable[[List[str]], List[str]]) -> 'ProjectFunctor[PS1]':
        """Transform project maintainers."""
        def transform(project: Project[PS1]) -> Project[PS1]:
            new_maintainers = maintainer_transform(project.maintainers)
            return Project(
                name=project.name,
                path=project.path,
                prefix=project.prefix,
                description=project.description,
                git_url=project.git_url,
                maintainers=new_maintainers,
                created_at=project.created_at
            )
        
        return self.fmap(transform)
    
    def bind(self, f: Callable[[Project[PS1]], 'ProjectFunctor[PS2]']) -> 'ProjectFunctor[PS2]':
        """Monadic bind operation for project transformations."""
        return f(self.project)
    
    def apply(self, f_functor: 'ProjectFunctor[Callable[[Project[PS1]], Project[PS2]]]') -> 'ProjectFunctor[PS2]':
        """Applicative apply operation."""
        f = f_functor.project
        return ProjectFunctor(f(self.project))
    
    def value(self) -> Project[PS1]:
        """Extract the project value."""
        return self.project
    
    def __repr__(self) -> str:
        return f"ProjectFunctor({self.project})"


# Project-specific transformation commands

def create_project_command(name: str, path: Path, prefix: str, description: str = "") -> FilterCommand[None, EmptyProject]:
    """Command to create a new project in Empty state."""
    def create_action(_: None) -> EmptyProject:
        # Create project directory
        path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created project directory at {path}")
        
        return Project[Empty](
            name=name,
            path=path,
            prefix=prefix,
            description=description
        )
    
    return FilterCommand(
        name="create_project",
        action=create_action,
        effects=[
            Effect(EffectType.FILESYSTEM, f"Create project directory at {path}"),
            Effect(EffectType.AUDIT, f"Project {name} created")
        ],
        description=f"Create project {name} with prefix {prefix}"
    )


def populate_project_command() -> FilterCommand[EmptyProject, PopulatedProject]:
    """Command to populate project with kanban structure (Empty -> Populated)."""
    def populate_action(project: EmptyProject) -> PopulatedProject:
        # Create kanban directory structure
        kanban_dir = project.kanban_dir
        kanban_dir.mkdir(exist_ok=True)
        
        # Create kanban subdirectories
        for subdir in ["stories", "planning", "in-progress", "testing", "pr", "complete", "prompts"]:
            (kanban_dir / subdir).mkdir(exist_ok=True)
        
        # Create project configuration
        config_content = f"""
name: {project.name}
prefix: {project.prefix}
description: {project.description}
git_url: {project.git_url or ''}
maintainers: {project.maintainers}
created_at: {project.created_at}
version: '1.0'
"""
        project.config_file.write_text(config_content)
        
        logger.info(f"Populated project {project.name} with kanban structure")
        
        return Project[Populated](
            name=project.name,
            path=project.path,
            prefix=project.prefix,
            description=project.description,
            git_url=project.git_url,
            maintainers=project.maintainers,
            created_at=project.created_at
        )
    
    return FilterCommand(
        name="populate_project",
        action=populate_action,
        effects=[
            Effect(EffectType.FILESYSTEM, "Create kanban directory structure"),
            Effect(EffectType.CONFIG, "Write project configuration"),
            Effect(EffectType.AUDIT, "Project populated with kanban")
        ],
        description="Populate project with kanban structure and configuration"
    )


def activate_project_command() -> FilterCommand[PopulatedProject, ActiveProject]:
    """Command to activate project (Populated -> Active)."""
    def activate_action(project: PopulatedProject) -> ActiveProject:
        logger.info(f"Activating project {project.name}")
        
        # In a real implementation, this might:
        # - Create initial stories
        # - Set up CI/CD
        # - Initialize git hooks
        # - Create workspaces
        
        return Project[Active](
            name=project.name,
            path=project.path,
            prefix=project.prefix,
            description=project.description,
            git_url=project.git_url,
            maintainers=project.maintainers,
            created_at=project.created_at
        )
    
    return FilterCommand(
        name="activate_project",
        action=activate_action,
        effects=[
            Effect(EffectType.AUDIT, "Project activated")
        ],
        description="Activate project for development"
    )


def deactivate_project_command() -> FilterCommand[ActiveProject, PopulatedProject]:
    """Command to deactivate project (Active -> Populated)."""
    def deactivate_action(project: ActiveProject) -> PopulatedProject:
        logger.info(f"Deactivating project {project.name}")
        
        # In a real implementation, this might:
        # - Archive active workspaces
        # - Clean up temporary resources
        # - Update project status
        
        return Project[Populated](
            name=project.name,
            path=project.path,
            prefix=project.prefix,
            description=project.description,
            git_url=project.git_url,
            maintainers=project.maintainers,
            created_at=project.created_at
        )
    
    return FilterCommand(
        name="deactivate_project",
        action=deactivate_action,
        effects=[
            Effect(EffectType.AUDIT, "Project deactivated")
        ],
        description="Deactivate project"
    )


# Functor utility functions

def project_functor(project: Project[PS1]) -> ProjectFunctor[PS1]:
    """Lift a project into the ProjectFunctor."""
    return ProjectFunctor(project)


def pure_project(project: Project[PS1]) -> ProjectFunctor[PS1]:
    """Applicative pure operation for projects."""
    return ProjectFunctor(project)


def sequence_project_transforms(*transforms: Callable[[Project], Project]) -> Callable[[Project], Project]:
    """Compose a sequence of project transformations."""
    def composed_transform(project: Project) -> Project:
        result = project
        for transform in transforms:
            result = transform(result)
        return result
    
    return composed_transform


# Example project transformation patterns

def add_maintainer(maintainer: str) -> Callable[[Project[PS1]], Project[PS1]]:
    """Add a maintainer to a project."""
    def transform(project: Project[PS1]) -> Project[PS1]:
        return project.with_maintainer(maintainer)
    
    return transform


def update_description(description: str) -> Callable[[Project[PS1]], Project[PS1]]:
    """Update project description."""
    def transform(project: Project[PS1]) -> Project[PS1]:
        return Project(
            name=project.name,
            path=project.path,
            prefix=project.prefix,
            description=description,
            git_url=project.git_url,
            maintainers=project.maintainers,
            created_at=project.created_at
        )
    
    return transform


def set_git_url(git_url: str) -> Callable[[Project[PS1]], Project[PS1]]:
    """Set project git URL."""
    def transform(project: Project[PS1]) -> Project[PS1]:
        return Project(
            name=project.name,
            path=project.path,
            prefix=project.prefix,
            description=project.description,
            git_url=git_url,
            maintainers=project.maintainers,
            created_at=project.created_at
        )
    
    return transform


def remove_maintainer(maintainer: str) -> Callable[[Project[PS1]], Project[PS1]]:
    """Remove a maintainer from a project."""
    def transform(project: Project[PS1]) -> Project[PS1]:
        new_maintainers = [m for m in project.maintainers if m != maintainer]
        return Project(
            name=project.name,
            path=project.path,
            prefix=project.prefix,
            description=project.description,
            git_url=project.git_url,
            maintainers=new_maintainers,
            created_at=project.created_at
        )
    
    return transform


# Testing and validation

def validate_functor_laws():
    """Validate that ProjectFunctor satisfies functor laws."""
    from pathlib import Path
    
    # Create test project
    test_project = Project[Empty](
        name="test-project",
        path=Path("/tmp/test-project"),
        prefix="testp"
    )
    
    functor = ProjectFunctor(test_project)
    
    # Test identity law: fmap(id) = id
    identity = lambda x: x
    identity_mapped = functor.fmap(identity)
    assert identity_mapped.project == functor.project, "Identity law violated"
    
    # Test composition law: fmap(g ∘ f) = fmap(g) ∘ fmap(f)
    f = add_maintainer("alice@example.com")
    g = update_description("Updated description")
    
    # Direct composition
    composed = lambda project: g(f(project))
    direct_result = functor.fmap(composed)
    
    # Functor composition
    functor_result = functor.fmap(f).fmap(g)
    
    # Results should be equivalent
    assert direct_result.project.maintainers == functor_result.project.maintainers
    assert direct_result.project.description == functor_result.project.description
    
    logger.info("ProjectFunctor laws validated successfully")


if __name__ == "__main__":
    validate_functor_laws()
    print("ProjectFunctor module working correctly!")