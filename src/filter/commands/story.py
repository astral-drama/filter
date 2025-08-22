"""Categorical story commands extracted from CLI.

This module provides composable story commands that follow
categorical composition laws and type safety.
"""

import re
import shutil
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from ..command_algebra import FilterCommand, Effect, EffectType, sequence
from ..command_utils import run_command
from ..types import (
    Story, Draft, Ready, InProgress, Testing, Complete,
    DraftStory, ReadyStory, InProgressStory, TestingStory, CompleteStory
)
from ..functors.story import story_functor
from ..logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class StoryCreateArgs:
    """Arguments for story creation."""
    name: str
    title: Optional[str] = None
    description: Optional[str] = ""
    project_name: Optional[str] = None
    assignee: Optional[str] = None
    priority: str = "Medium"
    effort: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class StoryWorkspaceArgs:
    """Arguments for creating story workspace."""
    story_name: str
    template: str = "default"
    base_dir: Optional[Path] = None


class StoryCommands:
    """Categorical story commands extracted from CLI."""
    
    @staticmethod
    def create() -> FilterCommand[StoryCreateArgs, DraftStory]:
        """Create a new story in Draft state."""
        def create_action(args: StoryCreateArgs) -> DraftStory:
            logger.info(f"Creating story: {args.name}")
            
            # Find or determine project
            if args.project_name:
                project_path = Path("projects") / args.project_name
            else:
                # Search for story in existing projects
                project_path = StoryCommands._find_project_for_story(args.name)
                if not project_path:
                    project_path = Path("kanban")  # Default kanban location
            
            # Determine story file path
            stories_dir = project_path / "kanban" / "stories"
            stories_dir.mkdir(parents=True, exist_ok=True)
            story_file = stories_dir / f"{args.name}.md"
            
            # Generate story content
            content = StoryCommands._generate_story_content(args)
            
            # Write story file
            story_file.write_text(content)
            
            logger.info(f"Story {args.name} created at {story_file}")
            
            return Story[Draft](
                name=args.name,
                title=args.title or f"Story: {args.name}",
                description=args.description,
                file_path=story_file,
                project_name=args.project_name,
                assignee=args.assignee,
                priority=args.priority,
                effort=args.effort,
                tags=args.tags or [],
                created_at=datetime.now()
            )
        
        return FilterCommand(
            name="story_create",
            action=create_action,
            effects=[
                Effect(EffectType.FILESYSTEM, "Create story file"),
                Effect(EffectType.AUDIT, "Story created")
            ],
            description="Create a new story in draft state"
        )
    
    @staticmethod
    def move_to_planning() -> FilterCommand[DraftStory, ReadyStory]:
        """Move story from stories/ to planning/ (Draft -> Ready)."""
        def move_action(story: DraftStory) -> ReadyStory:
            logger.info(f"Moving story {story.name} to planning")
            
            # Determine source and target paths
            planning_dir = story.file_path.parent.parent / "planning"
            planning_dir.mkdir(exist_ok=True)
            target_path = planning_dir / story.file_path.name
            
            # Move the file
            shutil.move(str(story.file_path), str(target_path))
            
            logger.info(f"Story {story.name} moved to planning")
            
            return Story[Ready](
                name=story.name,
                title=story.title,
                description=story.description,
                file_path=target_path,
                project_name=story.project_name,
                assignee=story.assignee,
                priority=story.priority,
                effort=story.effort,
                tags=story.tags,
                created_at=story.created_at
            )
        
        return FilterCommand(
            name="story_move_to_planning",
            action=move_action,
            effects=[
                Effect(EffectType.FILESYSTEM, "Move story file to planning"),
                Effect(EffectType.AUDIT, "Story moved to planning")
            ],
            description="Move story from stories to planning directory"
        )
    
    @staticmethod
    def start() -> FilterCommand[ReadyStory, InProgressStory]:
        """Start working on story (Ready -> InProgress)."""
        def start_action(story: ReadyStory) -> InProgressStory:
            logger.info(f"Starting work on story {story.name}")
            
            # Move from planning/ to in-progress/
            inprogress_dir = story.file_path.parent.parent / "in-progress"
            inprogress_dir.mkdir(exist_ok=True)
            target_path = inprogress_dir / story.file_path.name
            
            shutil.move(str(story.file_path), str(target_path))
            
            # Update story content with start date
            content = target_path.read_text()
            start_marker = f"\n\n**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            updated_content = content + start_marker
            target_path.write_text(updated_content)
            
            logger.info(f"Started work on story {story.name}")
            
            return Story[InProgress](
                name=story.name,
                title=story.title,
                description=story.description,
                file_path=target_path,
                project_name=story.project_name,
                assignee=story.assignee,
                priority=story.priority,
                effort=story.effort,
                tags=story.tags,
                created_at=story.created_at
            )
        
        return FilterCommand(
            name="story_start",
            action=start_action,
            effects=[
                Effect(EffectType.FILESYSTEM, "Move story to in-progress"),
                Effect(EffectType.AUDIT, "Story started")
            ],
            description="Start working on story"
        )
    
    @staticmethod
    def move_to_testing() -> FilterCommand[InProgressStory, TestingStory]:
        """Move story to testing (InProgress -> Testing)."""
        def testing_action(story: InProgressStory) -> TestingStory:
            logger.info(f"Moving story {story.name} to testing")
            
            # Move from in-progress/ to testing/
            testing_dir = story.file_path.parent.parent / "testing"
            testing_dir.mkdir(exist_ok=True)
            target_path = testing_dir / story.file_path.name
            
            shutil.move(str(story.file_path), str(target_path))
            
            logger.info(f"Story {story.name} moved to testing")
            
            return Story[Testing](
                name=story.name,
                title=story.title,
                description=story.description,
                file_path=target_path,
                project_name=story.project_name,
                assignee=story.assignee,
                priority=story.priority,
                effort=story.effort,
                tags=story.tags,
                created_at=story.created_at
            )
        
        return FilterCommand(
            name="story_move_to_testing",
            action=testing_action,
            effects=[
                Effect(EffectType.FILESYSTEM, "Move story to testing"),
                Effect(EffectType.AUDIT, "Story moved to testing")
            ],
            description="Move story to testing phase"
        )
    
    @staticmethod
    def complete() -> FilterCommand[TestingStory, CompleteStory]:
        """Complete story (Testing -> Complete)."""
        def complete_action(story: TestingStory) -> CompleteStory:
            logger.info(f"Completing story {story.name}")
            
            # Move from testing/ to complete/
            complete_dir = story.file_path.parent.parent / "complete"
            complete_dir.mkdir(exist_ok=True)
            target_path = complete_dir / story.file_path.name
            
            shutil.move(str(story.file_path), str(target_path))
            
            # Update story content with completion date
            content = target_path.read_text()
            complete_marker = f"\n\n**Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            updated_content = content + complete_marker
            target_path.write_text(updated_content)
            
            logger.info(f"Story {story.name} completed")
            
            return Story[Complete](
                name=story.name,
                title=story.title,
                description=story.description,
                file_path=target_path,
                project_name=story.project_name,
                assignee=story.assignee,
                priority=story.priority,
                effort=story.effort,
                tags=story.tags,
                created_at=story.created_at
            )
        
        return FilterCommand(
            name="story_complete",
            action=complete_action,
            effects=[
                Effect(EffectType.FILESYSTEM, "Move story to complete"),
                Effect(EffectType.AUDIT, "Story completed")
            ],
            description="Mark story as complete"
        )
    
    @staticmethod
    def delete() -> FilterCommand[Story, None]:
        """Delete a story file."""
        def delete_action(story: Story) -> None:
            logger.info(f"Deleting story {story.name}")
            
            if story.file_path.exists():
                story.file_path.unlink()
            
            logger.info(f"Story {story.name} deleted")
            return None
        
        return FilterCommand(
            name="story_delete",
            action=delete_action,
            effects=[
                Effect(EffectType.FILESYSTEM, "Delete story file"),
                Effect(EffectType.AUDIT, "Story deleted")
            ],
            description="Delete story file"
        )
    
    @staticmethod
    def create_workspace() -> FilterCommand[StoryWorkspaceArgs, 'CreatedWorkspace']:
        """Create a workspace for a story."""
        def workspace_action(args: StoryWorkspaceArgs):
            # Import here to avoid circular imports
            from .workspace import WorkspaceCommands, WorkspaceCreateArgs
            
            logger.info(f"Creating workspace for story {args.story_name}")
            
            # Find the story
            story_path = StoryCommands._find_story_file(args.story_name)
            if not story_path:
                raise ValueError(f"Story {args.story_name} not found")
            
            # Create workspace args
            workspace_args = WorkspaceCreateArgs(
                name=args.story_name,
                template=args.template,
                base_dir=args.base_dir,
                story_name=args.story_name
            )
            
            # Create workspace
            create_cmd = WorkspaceCommands.create()
            workspace = create_cmd(workspace_args)
            
            logger.info(f"Created workspace for story {args.story_name}")
            
            return workspace
        
        return FilterCommand(
            name="story_create_workspace",
            action=workspace_action,
            effects=[
                Effect(EffectType.FILESYSTEM, "Create story workspace"),
                Effect(EffectType.CONFIG, "Configure story environment"),
                Effect(EffectType.AUDIT, "Story workspace created")
            ],
            description="Create dedicated workspace for story development"
        )
    
    # Helper methods
    
    @staticmethod
    def _find_project_for_story(story_name: str) -> Optional[Path]:
        """Find which project contains a story."""
        # Extract prefix from story name
        prefix_match = re.match(r'^([a-zA-Z]+)', story_name)
        if not prefix_match:
            return None
        
        prefix = prefix_match.group(1)
        
        # Search projects for matching prefix
        projects_dir = Path("projects")
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if project_dir.is_dir():
                    config_file = project_dir / "project.yaml"
                    if config_file.exists():
                        # Check if project prefix matches
                        import yaml
                        try:
                            with open(config_file) as f:
                                config = yaml.safe_load(f)
                                if config.get('prefix', '').startswith(prefix):
                                    return project_dir
                        except Exception:
                            continue
        
        return None
    
    @staticmethod
    def _find_story_file(story_name: str) -> Optional[Path]:
        """Find story file by name across all projects."""
        # Search in main kanban
        kanban_dirs = [Path("kanban")]
        
        # Search in project kanban directories
        projects_dir = Path("projects")
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if project_dir.is_dir():
                    kanban_dirs.append(project_dir / "kanban")
        
        # Search all kanban directories
        for kanban_dir in kanban_dirs:
            if kanban_dir.exists():
                for subdir in ["stories", "planning", "in-progress", "testing", "complete"]:
                    story_file = kanban_dir / subdir / f"{story_name}.md"
                    if story_file.exists():
                        return story_file
        
        return None
    
    @staticmethod
    def _generate_story_content(args: StoryCreateArgs) -> str:
        """Generate markdown content for a story."""
        content = f"# {args.title or args.name}\n\n"
        
        if args.description:
            content += f"{args.description}\n\n"
        
        content += "## Details\n\n"
        content += f"- **Priority:** {args.priority}\n"
        
        if args.assignee:
            content += f"- **Assignee:** {args.assignee}\n"
        
        if args.effort:
            content += f"- **Effort:** {args.effort}\n"
        
        if args.tags:
            content += f"- **Tags:** {', '.join(args.tags)}\n"
        
        content += f"- **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        content += "## Tasks\n\n- [ ] TODO: Define specific tasks\n\n"
        content += "## Notes\n\n"
        
        return content


# Composable story workflows

def story_full_lifecycle() -> FilterCommand[StoryCreateArgs, CompleteStory]:
    """Complete story lifecycle: create -> planning -> start -> testing -> complete."""
    create_cmd = StoryCommands.create()
    to_planning_cmd = StoryCommands.move_to_planning()
    start_cmd = StoryCommands.start()
    to_testing_cmd = StoryCommands.move_to_testing()
    complete_cmd = StoryCommands.complete()
    
    pipeline = sequence(create_cmd, to_planning_cmd, start_cmd, to_testing_cmd, complete_cmd)
    return pipeline.compose()


def story_development_flow() -> FilterCommand[ReadyStory, TestingStory]:
    """Development flow: start -> testing."""
    start_cmd = StoryCommands.start()
    to_testing_cmd = StoryCommands.move_to_testing()
    
    return start_cmd.compose(to_testing_cmd)


if __name__ == "__main__":
    # Test story commands
    args = StoryCreateArgs(
        name="test-1",
        title="Test Story",
        description="A test story for validation",
        priority="High",
        tags=["test", "validation"]
    )
    
    # Test command composition
    create_cmd = StoryCommands.create()
    story = create_cmd(args)
    
    print(f"Created story: {story.name}")
    print(f"Story file: {story.file_path}")
    print("Story commands module working correctly!")