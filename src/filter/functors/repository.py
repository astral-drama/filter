"""Repository functor for systematic transformations between repository contexts.

This module implements the RepositoryFunctor that enables mapping between
different repository states and contexts while preserving structure.
"""

from typing import TypeVar, Generic, Callable, Optional, Dict, Any
from pathlib import Path

from ..types import (
    Repository, RepoState,
    Uninitialised, Initialised, Cloned, Configured,
    UninitRepo, InitRepo, ClonedRepo, ConfiguredRepo
)
from ..command_algebra import FilterCommand, Effect, EffectType
from ..logging_config import get_logger

logger = get_logger(__name__)

# Type variables for functor operations
RS1 = TypeVar('RS1', bound=RepoState)
RS2 = TypeVar('RS2', bound=RepoState)
T = TypeVar('T')
U = TypeVar('U')


class RepositoryFunctor(Generic[RS1]):
    """Functor for repository transformations.
    
    Enables systematic mapping between repository contexts while preserving
    the categorical structure of repository operations.
    
    Satisfies functor laws:
    1. fmap(id) = id (identity preservation)
    2. fmap(g ∘ f) = fmap(g) ∘ fmap(f) (composition preservation)
    """
    
    def __init__(self, repository: Repository[RS1]):
        self.repository = repository
    
    def fmap(self, f: Callable[[Repository[RS1]], Repository[RS2]]) -> 'RepositoryFunctor[RS2]':
        """Map a function over the repository while preserving structure.
        
        This is the core functor operation that enables systematic
        transformation between repository contexts.
        """
        transformed = f(self.repository)
        return RepositoryFunctor(transformed)
    
    def map_url(self, new_url: Optional[str]) -> 'RepositoryFunctor[RS1]':
        """Transform repository URL."""
        def transform(repo: Repository[RS1]) -> Repository[RS1]:
            return Repository(
                path=repo.path,
                url=new_url,
                branch=repo.branch,
                metadata=repo.metadata
            )
        
        return self.fmap(transform)
    
    def map_branch(self, new_branch: str) -> 'RepositoryFunctor[RS1]':
        """Transform repository branch."""
        def transform(repo: Repository[RS1]) -> Repository[RS1]:
            return Repository(
                path=repo.path,
                url=repo.url,
                branch=new_branch,
                metadata=repo.metadata
            )
        
        return self.fmap(transform)
    
    def map_metadata(self, metadata_transform: Callable[[Dict[str, Any]], Dict[str, Any]]) -> 'RepositoryFunctor[RS1]':
        """Transform repository metadata."""
        def transform(repo: Repository[RS1]) -> Repository[RS1]:
            new_metadata = metadata_transform(repo.metadata)
            return Repository(
                path=repo.path,
                url=repo.url,
                branch=repo.branch,
                metadata=new_metadata
            )
        
        return self.fmap(transform)
    
    def bind(self, f: Callable[[Repository[RS1]], 'RepositoryFunctor[RS2]']) -> 'RepositoryFunctor[RS2]':
        """Monadic bind operation for repository transformations."""
        return f(self.repository)
    
    def apply(self, f_functor: 'RepositoryFunctor[Callable[[Repository[RS1]], Repository[RS2]]]') -> 'RepositoryFunctor[RS2]':
        """Applicative apply operation."""
        f = f_functor.repository
        return RepositoryFunctor(f(self.repository))
    
    def value(self) -> Repository[RS1]:
        """Extract the repository value."""
        return self.repository
    
    def __repr__(self) -> str:
        return f"RepositoryFunctor({self.repository})"


# Repository-specific transformation commands

def init_repository_command() -> FilterCommand[UninitRepo, InitRepo]:
    """Command to initialize repository with Filter (Uninitialised -> Initialised)."""
    def init_action(repo: UninitRepo) -> InitRepo:
        # Create .filter directory structure
        filter_dir = repo.filter_dir
        filter_dir.mkdir(exist_ok=True)
        
        # Create basic Filter structure
        (filter_dir / "config.yaml").touch()
        (filter_dir / "kanban").mkdir(exist_ok=True)
        (filter_dir / "kanban" / "stories").mkdir(exist_ok=True)
        (filter_dir / "kanban" / "planning").mkdir(exist_ok=True)
        (filter_dir / "kanban" / "in-progress").mkdir(exist_ok=True)
        (filter_dir / "kanban" / "testing").mkdir(exist_ok=True)
        (filter_dir / "kanban" / "complete").mkdir(exist_ok=True)
        
        logger.info(f"Initialized Filter in repository at {repo.path}")
        
        return Repository[Initialised](
            path=repo.path,
            url=repo.url,
            branch=repo.branch,
            metadata=repo.with_metadata(filter_initialized=True).metadata
        )
    
    return FilterCommand(
        name="init_repository",
        action=init_action,
        effects=[
            Effect(EffectType.FILESYSTEM, "Create .filter directory structure"),
            Effect(EffectType.CONFIG, "Initialize Filter configuration"),
            Effect(EffectType.AUDIT, "Repository initialized with Filter")
        ],
        description="Initialize repository with Filter metadata and structure"
    )


def clone_repository_command(url: str, path: Path) -> FilterCommand[None, ClonedRepo]:
    """Command to clone repository from remote (None -> Cloned)."""
    def clone_action(_: None) -> ClonedRepo:
        # In real implementation, would use git clone
        logger.info(f"Cloning repository from {url} to {path}")
        
        # Simulate git clone
        path.mkdir(parents=True, exist_ok=True)
        (path / ".git").mkdir(exist_ok=True)
        
        return Repository[Cloned](
            path=path,
            url=url,
            branch="main",
            metadata={"cloned_from": url}
        )
    
    return FilterCommand(
        name="clone_repository",
        action=clone_action,
        effects=[
            Effect(EffectType.GIT, f"Clone repository from {url}"),
            Effect(EffectType.FILESYSTEM, f"Create repository at {path}"),
            Effect(EffectType.AUDIT, f"Repository cloned from {url}")
        ],
        description=f"Clone repository from {url} to {path}"
    )


def configure_repository_command() -> FilterCommand[InitRepo, ConfiguredRepo]:
    """Command to complete repository configuration (Initialised -> Configured)."""
    def configure_action(repo: InitRepo) -> ConfiguredRepo:
        logger.info(f"Configuring repository at {repo.path}")
        
        # Write configuration
        config_content = """
version: '1.0'
filter:
  enabled: true
  kanban: true
  workspace: true
"""
        (repo.filter_dir / "config.yaml").write_text(config_content)
        
        return Repository[Configured](
            path=repo.path,
            url=repo.url,
            branch=repo.branch,
            metadata=repo.with_metadata(configured=True).metadata
        )
    
    return FilterCommand(
        name="configure_repository",
        action=configure_action,
        effects=[
            Effect(EffectType.CONFIG, "Write Filter configuration"),
            Effect(EffectType.AUDIT, "Repository fully configured")
        ],
        description="Complete repository configuration with Filter settings"
    )


# Functor utility functions

def repository_functor(repository: Repository[RS1]) -> RepositoryFunctor[RS1]:
    """Lift a repository into the RepositoryFunctor."""
    return RepositoryFunctor(repository)


def pure_repository(repository: Repository[RS1]) -> RepositoryFunctor[RS1]:
    """Applicative pure operation for repositories."""
    return RepositoryFunctor(repository)


def sequence_repository_transforms(*transforms: Callable[[Repository], Repository]) -> Callable[[Repository], Repository]:
    """Compose a sequence of repository transformations."""
    def composed_transform(repository: Repository) -> Repository:
        result = repository
        for transform in transforms:
            result = transform(result)
        return result
    
    return composed_transform


# Example repository transformation patterns

def add_metadata(**kwargs: Any) -> Callable[[Repository[RS1]], Repository[RS1]]:
    """Add metadata to a repository."""
    def transform(repo: Repository[RS1]) -> Repository[RS1]:
        return repo.with_metadata(**kwargs)
    
    return transform


def set_branch(branch: str) -> Callable[[Repository[RS1]], Repository[RS1]]:
    """Set repository branch."""
    def transform(repo: Repository[RS1]) -> Repository[RS1]:
        return Repository(
            path=repo.path,
            url=repo.url,
            branch=branch,
            metadata=repo.metadata
        )
    
    return transform


def set_url(url: str) -> Callable[[Repository[RS1]], Repository[RS1]]:
    """Set repository URL."""
    def transform(repo: Repository[RS1]) -> Repository[RS1]:
        return Repository(
            path=repo.path,
            url=url,
            branch=repo.branch,
            metadata=repo.metadata
        )
    
    return transform


# Testing and validation

def validate_functor_laws():
    """Validate that RepositoryFunctor satisfies functor laws."""
    from pathlib import Path
    
    # Create test repository
    test_repo = Repository[Uninitialised](
        path=Path("/tmp/test-repo"),
        url="https://github.com/test/repo.git"
    )
    
    functor = RepositoryFunctor(test_repo)
    
    # Test identity law: fmap(id) = id
    identity = lambda x: x
    identity_mapped = functor.fmap(identity)
    assert identity_mapped.repository == functor.repository, "Identity law violated"
    
    # Test composition law: fmap(g ∘ f) = fmap(g) ∘ fmap(f)
    f = set_branch("develop")
    g = add_metadata(team="backend")
    
    # Direct composition
    composed = lambda repo: g(f(repo))
    direct_result = functor.fmap(composed)
    
    # Functor composition
    functor_result = functor.fmap(f).fmap(g)
    
    # Results should be equivalent
    assert direct_result.repository.branch == functor_result.repository.branch
    assert direct_result.repository.metadata == functor_result.repository.metadata
    
    logger.info("RepositoryFunctor laws validated successfully")


if __name__ == "__main__":
    validate_functor_laws()
    print("RepositoryFunctor module working correctly!")