"""Story functor for systematic transformations between story contexts.

This module implements the StoryFunctor that enables mapping between
different story states and contexts while preserving structure.
"""

from typing import TypeVar, Generic, Callable, Optional, List
from pathlib import Path
from datetime import datetime

from ..types import (
    Story, StoryState,
    Draft, Ready, InProgress, Testing, Complete,
    DraftStory, ReadyStory, InProgressStory, TestingStory, CompleteStory
)
from ..command_algebra import FilterCommand, Effect, EffectType
from ..logging_config import get_logger

logger = get_logger(__name__)

# Type variables for functor operations
SS1 = TypeVar('SS1', bound=StoryState)
SS2 = TypeVar('SS2', bound=StoryState)
T = TypeVar('T')
U = TypeVar('U')


class StoryFunctor(Generic[SS1]):
    """Functor for story transformations.
    
    Enables systematic mapping between story contexts while preserving
    the categorical structure of story operations.
    
    Satisfies functor laws:
    1. fmap(id) = id (identity preservation)
    2. fmap(g ∘ f) = fmap(g) ∘ fmap(f) (composition preservation)
    """
    
    def __init__(self, story: Story[SS1]):
        self.story = story
    
    def fmap(self, f: Callable[[Story[SS1]], Story[SS2]]) -> 'StoryFunctor[SS2]':
        """Map a function over the story while preserving structure.
        
        This is the core functor operation that enables systematic
        transformation between story contexts.
        """
        transformed = f(self.story)
        return StoryFunctor(transformed)
    
    def map_title(self, new_title: str) -> 'StoryFunctor[SS1]':
        """Transform story title."""
        def transform(story: Story[SS1]) -> Story[SS1]:
            return Story(
                name=story.name,
                title=new_title,
                description=story.description,
                file_path=story.file_path,
                project_name=story.project_name,
                assignee=story.assignee,
                priority=story.priority,
                effort=story.effort,
                tags=story.tags,
                created_at=story.created_at
            )
        
        return self.fmap(transform)
    
    def map_description(self, new_description: str) -> 'StoryFunctor[SS1]':
        """Transform story description."""
        def transform(story: Story[SS1]) -> Story[SS1]:
            return Story(
                name=story.name,
                title=story.title,
                description=new_description,
                file_path=story.file_path,
                project_name=story.project_name,
                assignee=story.assignee,
                priority=story.priority,
                effort=story.effort,
                tags=story.tags,
                created_at=story.created_at
            )
        
        return self.fmap(transform)
    
    def map_assignee(self, assignee: Optional[str]) -> 'StoryFunctor[SS1]':
        """Transform story assignee."""
        def transform(story: Story[SS1]) -> Story[SS1]:
            return Story(
                name=story.name,
                title=story.title,
                description=story.description,
                file_path=story.file_path,
                project_name=story.project_name,
                assignee=assignee,
                priority=story.priority,
                effort=story.effort,
                tags=story.tags,
                created_at=story.created_at
            )
        
        return self.fmap(transform)
    
    def map_priority(self, priority: str) -> 'StoryFunctor[SS1]':
        """Transform story priority."""
        def transform(story: Story[SS1]) -> Story[SS1]:
            return Story(
                name=story.name,
                title=story.title,
                description=story.description,
                file_path=story.file_path,
                project_name=story.project_name,
                assignee=story.assignee,
                priority=priority,
                effort=story.effort,
                tags=story.tags,
                created_at=story.created_at
            )
        
        return self.fmap(transform)
    
    def map_tags(self, tag_transform: Callable[[List[str]], List[str]]) -> 'StoryFunctor[SS1]':
        """Transform story tags."""
        def transform(story: Story[SS1]) -> Story[SS1]:
            new_tags = tag_transform(story.tags)
            return Story(
                name=story.name,
                title=story.title,
                description=story.description,
                file_path=story.file_path,
                project_name=story.project_name,
                assignee=story.assignee,
                priority=story.priority,
                effort=story.effort,
                tags=new_tags,
                created_at=story.created_at
            )
        
        return self.fmap(transform)
    
    def bind(self, f: Callable[[Story[SS1]], 'StoryFunctor[SS2]']) -> 'StoryFunctor[SS2]':
        """Monadic bind operation for story transformations."""
        return f(self.story)
    
    def apply(self, f_functor: 'StoryFunctor[Callable[[Story[SS1]], Story[SS2]]]') -> 'StoryFunctor[SS2]':
        """Applicative apply operation."""
        f = f_functor.story
        return StoryFunctor(f(self.story))
    
    def value(self) -> Story[SS1]:
        """Extract the story value."""
        return self.story
    
    def __repr__(self) -> str:
        return f"StoryFunctor({self.story})"


# Story-specific transformation commands

def create_story_command(name: str, file_path: Path, title: str = "", description: str = "") -> FilterCommand[None, DraftStory]:
    """Command to create a new story in Draft state."""
    def create_action(_: None) -> DraftStory:
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create story file if it doesn't exist
        if not file_path.exists():
            content = f"# {title or name}\n\n{description}\n"
            file_path.write_text(content)
        
        logger.info(f"Created story file at {file_path}")
        
        return Story[Draft](
            name=name,
            title=title or f"Story: {name}",
            description=description,
            file_path=file_path,
            created_at=datetime.now()
        )
    
    return FilterCommand(
        name="create_story",
        action=create_action,
        effects=[
            Effect(EffectType.FILESYSTEM, f"Create story file at {file_path}"),
            Effect(EffectType.AUDIT, f"Story {name} created")
        ],
        description=f"Create story {name} in draft state"
    )


def ready_story_command() -> FilterCommand[DraftStory, ReadyStory]:
    """Command to mark story as ready (Draft -> Ready)."""
    def ready_action(story: DraftStory) -> ReadyStory:
        logger.info(f"Marking story {story.name} as ready")
        
        return Story[Ready](
            name=story.name,
            title=story.title,
            description=story.description,
            file_path=story.file_path,
            project_name=story.project_name,
            assignee=story.assignee,
            priority=story.priority,
            effort=story.effort,
            tags=story.tags,
            created_at=story.created_at
        )
    
    return FilterCommand(
        name="ready_story",
        action=ready_action,
        effects=[
            Effect(EffectType.AUDIT, "Story marked as ready")
        ],
        description="Mark story as ready for development"
    )


def start_story_command() -> FilterCommand[ReadyStory, InProgressStory]:
    """Command to start working on story (Ready -> InProgress)."""
    def start_action(story: ReadyStory) -> InProgressStory:
        logger.info(f"Starting work on story {story.name}")
        
        return Story[InProgress](
            name=story.name,
            title=story.title,
            description=story.description,
            file_path=story.file_path,
            project_name=story.project_name,
            assignee=story.assignee,
            priority=story.priority,
            effort=story.effort,
            tags=story.tags,
            created_at=story.created_at
        )
    
    return FilterCommand(
        name="start_story",
        action=start_action,
        effects=[
            Effect(EffectType.AUDIT, "Story started")
        ],
        description="Start working on story"
    )


def test_story_command() -> FilterCommand[InProgressStory, TestingStory]:
    """Command to move story to testing (InProgress -> Testing)."""
    def test_action(story: InProgressStory) -> TestingStory:
        logger.info(f"Moving story {story.name} to testing")
        
        return Story[Testing](
            name=story.name,
            title=story.title,
            description=story.description,
            file_path=story.file_path,
            project_name=story.project_name,
            assignee=story.assignee,
            priority=story.priority,
            effort=story.effort,
            tags=story.tags,
            created_at=story.created_at
        )
    
    return FilterCommand(
        name="test_story",
        action=test_action,
        effects=[
            Effect(EffectType.AUDIT, "Story moved to testing")
        ],
        description="Move story to testing phase"
    )


def complete_story_command() -> FilterCommand[TestingStory, CompleteStory]:
    """Command to complete story (Testing -> Complete)."""
    def complete_action(story: TestingStory) -> CompleteStory:
        logger.info(f"Completing story {story.name}")
        
        return Story[Complete](
            name=story.name,
            title=story.title,
            description=story.description,
            file_path=story.file_path,
            project_name=story.project_name,
            assignee=story.assignee,
            priority=story.priority,
            effort=story.effort,
            tags=story.tags,
            created_at=story.created_at
        )
    
    return FilterCommand(
        name="complete_story",
        action=complete_action,
        effects=[
            Effect(EffectType.AUDIT, "Story completed")
        ],
        description="Mark story as complete"
    )


# Functor utility functions

def story_functor(story: Story[SS1]) -> StoryFunctor[SS1]:
    """Lift a story into the StoryFunctor."""
    return StoryFunctor(story)


def pure_story(story: Story[SS1]) -> StoryFunctor[SS1]:
    """Applicative pure operation for stories."""
    return StoryFunctor(story)


def sequence_story_transforms(*transforms: Callable[[Story], Story]) -> Callable[[Story], Story]:
    """Compose a sequence of story transformations."""
    def composed_transform(story: Story) -> Story:
        result = story
        for transform in transforms:
            result = transform(result)
        return result
    
    return composed_transform


# Example story transformation patterns

def add_tags(*new_tags: str) -> Callable[[Story[SS1]], Story[SS1]]:
    """Add tags to a story."""
    def transform(story: Story[SS1]) -> Story[SS1]:
        return story.with_tags(*new_tags)
    
    return transform


def set_assignee(assignee: str) -> Callable[[Story[SS1]], Story[SS1]]:
    """Set story assignee."""
    def transform(story: Story[SS1]) -> Story[SS1]:
        return Story(
            name=story.name,
            title=story.title,
            description=story.description,
            file_path=story.file_path,
            project_name=story.project_name,
            assignee=assignee,
            priority=story.priority,
            effort=story.effort,
            tags=story.tags,
            created_at=story.created_at
        )
    
    return transform


def set_priority(priority: str) -> Callable[[Story[SS1]], Story[SS1]]:
    """Set story priority."""
    def transform(story: Story[SS1]) -> Story[SS1]:
        return Story(
            name=story.name,
            title=story.title,
            description=story.description,
            file_path=story.file_path,
            project_name=story.project_name,
            assignee=story.assignee,
            priority=priority,
            effort=story.effort,
            tags=story.tags,
            created_at=story.created_at
        )
    
    return transform


def update_description(description: str) -> Callable[[Story[SS1]], Story[SS1]]:
    """Update story description."""
    def transform(story: Story[SS1]) -> Story[SS1]:
        return Story(
            name=story.name,
            title=story.title,
            description=description,
            file_path=story.file_path,
            project_name=story.project_name,
            assignee=story.assignee,
            priority=story.priority,
            effort=story.effort,
            tags=story.tags,
            created_at=story.created_at
        )
    
    return transform


# Testing and validation

def validate_functor_laws():
    """Validate that StoryFunctor satisfies functor laws."""
    from pathlib import Path
    
    # Create test story
    test_story = Story[Draft](
        name="test-1",
        title="Test Story",
        description="A test story",
        file_path=Path("/tmp/test-1.md")
    )
    
    functor = StoryFunctor(test_story)
    
    # Test identity law: fmap(id) = id
    identity = lambda x: x
    identity_mapped = functor.fmap(identity)
    assert identity_mapped.story == functor.story, "Identity law violated"
    
    # Test composition law: fmap(g ∘ f) = fmap(g) ∘ fmap(f)
    f = set_assignee("alice")
    g = add_tags("urgent", "backend")
    
    # Direct composition
    composed = lambda story: g(f(story))
    direct_result = functor.fmap(composed)
    
    # Functor composition
    functor_result = functor.fmap(f).fmap(g)
    
    # Results should be equivalent
    assert direct_result.story.assignee == functor_result.story.assignee
    assert set(direct_result.story.tags) == set(functor_result.story.tags)
    
    logger.info("StoryFunctor laws validated successfully")


if __name__ == "__main__":
    validate_functor_laws()
    print("StoryFunctor module working correctly!")