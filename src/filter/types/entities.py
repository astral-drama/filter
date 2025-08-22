"""Type-safe entity definitions with phantom states.

This module defines the core Filter entities (Repository, Workspace, Story, Project)
with phantom type parameters that encode their state at the type level.
"""

from typing import TypeVar, Generic, Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

from .phantom import Phantom, PhantomType, StateTransition
from .states import *

# Type variables for phantom states
RepoState = TypeVar('RepoState', bound=PhantomType)
WorkspaceState = TypeVar('WorkspaceState', bound=PhantomType) 
StoryState = TypeVar('StoryState', bound=PhantomType)
ProjectState = TypeVar('ProjectState', bound=PhantomType)


@dataclass(frozen=True)
class Repository(Generic[RepoState]):
    """A git repository with Filter integration.
    
    The phantom type parameter encodes the repository's state:
    - Repository[Uninitialised]: No Filter metadata
    - Repository[Initialised]: Has .filter directory  
    - Repository[Cloned]: Cloned from remote
    - Repository[Configured]: Fully configured
    """
    
    path: Path
    url: Optional[str] = None
    branch: str = "main"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def name(self) -> str:
        """Get the repository name (directory name)."""
        return self.path.name
    
    @property
    def git_dir(self) -> Path:
        """Get the .git directory path."""
        return self.path / ".git"
    
    @property
    def filter_dir(self) -> Path:
        """Get the .filter directory path."""
        return self.path / ".filter"
    
    def exists(self) -> bool:
        """Check if the repository directory exists."""
        return self.path.exists() and self.path.is_dir()
    
    def is_git_repo(self) -> bool:
        """Check if this is a valid git repository."""
        return self.git_dir.exists() and self.git_dir.is_dir()
    
    def has_filter(self) -> bool:
        """Check if Filter is initialized in this repository."""
        return self.filter_dir.exists() and self.filter_dir.is_dir()
    
    def with_metadata(self, **kwargs) -> 'Repository[RepoState]':
        """Create a new repository with updated metadata.
        
        This maintains immutability by creating a new instance with
        a new metadata dictionary rather than modifying the existing one.
        """
        # Create new dict to maintain immutability
        new_metadata = {**self.metadata, **kwargs}
        return Repository(
            path=self.path,
            url=self.url,
            branch=self.branch,
            metadata=new_metadata
        )


@dataclass(frozen=True)
class Workspace(Generic[WorkspaceState]):
    """A development workspace for a specific story.
    
    The phantom type parameter encodes the workspace state:
    - Workspace[Created]: Directory structure exists
    - Workspace[Running]: Containers are active
    - Workspace[Stopped]: Containers are stopped
    - Workspace[Destroyed]: Workspace cleaned up
    """
    
    name: str
    path: Path
    template: str
    story_name: Optional[str] = None
    repository: Optional[Path] = None
    ports: Dict[str, int] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)
    created_at: Optional[datetime] = field(default_factory=lambda: datetime.now())
    
    @property
    def docker_compose_file(self) -> Path:
        """Get the docker-compose.yml file path."""
        return self.path / "docker-compose.yml"
    
    @property
    def workspace_dir(self) -> Path:
        """Get the workspace subdirectory path."""
        return self.path / "workspace"
    
    @property
    def kanban_dir(self) -> Path:
        """Get the kanban directory path."""
        return self.workspace_dir / "kanban"
    
    @property
    def repo_dir(self) -> Path:
        """Get the cloned repository directory path."""
        return self.workspace_dir / "repo"
    
    def exists(self) -> bool:
        """Check if the workspace directory exists."""
        return self.path.exists() and self.path.is_dir()
    
    def has_containers(self) -> bool:
        """Check if docker-compose configuration exists."""
        return self.docker_compose_file.exists()
    
    def with_story(self, story_name: str) -> 'Workspace[WorkspaceState]':
        """Create a new workspace associated with a story."""
        return Workspace(
            name=self.name,
            path=self.path,
            template=self.template,
            story_name=story_name,
            repository=self.repository,
            ports=self.ports,
            environment=self.environment,
            created_at=self.created_at
        )


@dataclass(frozen=True)
class Story(Generic[StoryState]):
    """A development story/task with kanban tracking.
    
    The phantom type parameter encodes the story state:
    - Story[Draft]: Being written
    - Story[Ready]: Ready for development
    - Story[InProgress]: Being worked on
    - Story[Testing]: In testing phase
    - Story[Complete]: Finished
    """
    
    name: str
    title: str
    description: str
    file_path: Path
    project_name: Optional[str] = None
    assignee: Optional[str] = None
    priority: str = "Medium"
    effort: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = field(default_factory=lambda: datetime.now())
    
    @property
    def id(self) -> str:
        """Get the story ID (same as name)."""
        return self.name
    
    @property
    def prefix(self) -> str:
        """Get the story prefix (part before the number)."""
        parts = self.name.split('-')
        if len(parts) >= 2:
            return parts[0]
        return ""
    
    @property
    def number(self) -> Optional[int]:
        """Get the story number."""
        parts = self.name.split('-')
        if len(parts) >= 2:
            try:
                return int(parts[1])
            except ValueError:
                pass
        return None
    
    def exists(self) -> bool:
        """Check if the story file exists."""
        return self.file_path.exists() and self.file_path.is_file()
    
    def with_tags(self, *tags: str) -> 'Story[StoryState]':
        """Create a new story with additional tags."""
        new_tags = list(self.tags) + list(tags)
        return Story(
            name=self.name,
            title=self.title,
            description=self.description,
            file_path=self.file_path,
            project_name=self.project_name,
            assignee=self.assignee,
            priority=self.priority,
            effort=self.effort,
            tags=new_tags,
            created_at=self.created_at
        )


@dataclass(frozen=True)
class Project(Generic[ProjectState]):
    """A Filter project containing stories and kanban boards.
    
    The phantom type parameter encodes the project state:
    - Project[Empty]: Directory exists but empty
    - Project[Populated]: Has kanban structure
    - Project[Active]: Has active stories and workspaces
    """
    
    name: str
    path: Path
    prefix: str
    description: str = ""
    git_url: Optional[str] = None
    maintainers: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = field(default_factory=lambda: datetime.now())
    
    @property
    def kanban_dir(self) -> Path:
        """Get the kanban directory path."""
        return self.path / "kanban"
    
    @property
    def config_file(self) -> Path:
        """Get the project configuration file path."""
        return self.path / "project.yaml"
    
    @property
    def stories_dir(self) -> Path:
        """Get the stories directory path."""
        return self.kanban_dir / "stories"
    
    def exists(self) -> bool:
        """Check if the project directory exists."""
        return self.path.exists() and self.path.is_dir()
    
    def has_kanban(self) -> bool:
        """Check if the project has kanban structure."""
        return self.kanban_dir.exists() and self.kanban_dir.is_dir()
    
    def has_config(self) -> bool:
        """Check if the project has configuration."""
        return self.config_file.exists()
    
    def with_maintainer(self, maintainer: str) -> 'Project[ProjectState]':
        """Create a new project with an additional maintainer."""
        new_maintainers = list(self.maintainers) + [maintainer]
        return Project(
            name=self.name,
            path=self.path,
            prefix=self.prefix,
            description=self.description,
            git_url=self.git_url,
            maintainers=new_maintainers,
            created_at=self.created_at
        )


# Type aliases for common entity states

# Repository type aliases
UninitRepo = Repository[Uninitialised]
InitRepo = Repository[Initialised]
ClonedRepo = Repository[Cloned]
ConfiguredRepo = Repository[Configured]

# Workspace type aliases
CreatedWorkspace = Workspace[Created]
RunningWorkspace = Workspace[Running]
StoppedWorkspace = Workspace[Stopped]
DestroyedWorkspace = Workspace[Destroyed]

# Story type aliases
DraftStory = Story[Draft]
ReadyStory = Story[Ready]
InProgressStory = Story[InProgress]
TestingStory = Story[Testing]
CompleteStory = Story[Complete]

# Project type aliases
EmptyProject = Project[Empty]
PopulatedProject = Project[Populated]
ActiveProject = Project[Active]


# State transition definitions for entities

# Repository transitions
INIT_REPO = StateTransition(Uninitialised, Initialised, "Initialize Filter in repository")
CLONE_REPO = StateTransition(Uninitialised, Cloned, "Clone repository from remote")
CONFIGURE_REPO = StateTransition(Initialised, Configured, "Complete repository configuration")
CONFIGURE_CLONED = StateTransition(Cloned, Configured, "Configure cloned repository")

# Workspace transitions
START_WORKSPACE = StateTransition(Created, Running, "Start workspace containers")
STOP_WORKSPACE = StateTransition(Running, Stopped, "Stop workspace containers")
RESTART_WORKSPACE = StateTransition(Stopped, Running, "Restart workspace containers")
DESTROY_WORKSPACE = StateTransition(Created, Destroyed, "Destroy workspace")
DESTROY_RUNNING = StateTransition(Running, Destroyed, "Destroy running workspace")
DESTROY_STOPPED = StateTransition(Stopped, Destroyed, "Destroy stopped workspace")

# Story transitions
READY_STORY = StateTransition(Draft, Ready, "Mark story as ready for development")
START_STORY = StateTransition(Ready, InProgress, "Start working on story")
TEST_STORY = StateTransition(InProgress, Testing, "Move story to testing")
COMPLETE_STORY = StateTransition(Testing, Complete, "Complete story")
REOPEN_STORY = StateTransition(Testing, InProgress, "Reopen story for more work")
UNREADY_STORY = StateTransition(InProgress, Ready, "Move story back to ready")

# Project transitions
POPULATE_PROJECT = StateTransition(Empty, Populated, "Add kanban structure to project")
ACTIVATE_PROJECT = StateTransition(Populated, Active, "Project becomes active")
DEACTIVATE_PROJECT = StateTransition(Active, Populated, "Project becomes inactive")


# Utility functions for working with typed entities

def repository_from_path(path: Path) -> UninitRepo:
    """Create an uninitialised repository from a path."""
    return Repository[Uninitialised](path=path)


def workspace_from_name(name: str, path: Path, template: str) -> CreatedWorkspace:
    """Create a workspace in the Created state."""
    return Workspace[Created](name=name, path=path, template=template)


def story_from_file(name: str, file_path: Path) -> DraftStory:
    """Create a story in Draft state from a file."""
    return Story[Draft](
        name=name,
        title=f"Story: {name}",
        description="",
        file_path=file_path
    )


def project_from_path(name: str, path: Path, prefix: str) -> EmptyProject:
    """Create an empty project from a path."""
    return Project[Empty](name=name, path=path, prefix=prefix)