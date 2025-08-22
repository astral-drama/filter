"""Categorical project commands extracted from CLI.

This module provides composable project commands that follow
categorical composition laws and type safety.
"""

import re
import yaml
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from ..command_algebra import FilterCommand, Effect, EffectType, sequence
from ..types import (
    Project, Empty, Populated, Active,
    EmptyProject, PopulatedProject, ActiveProject
)
from ..functors.project import project_functor
from ..logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ProjectCreateArgs:
    """Arguments for project creation."""
    name: str
    description: str = ""
    git_url: Optional[str] = None
    maintainers: Optional[List[str]] = None
    base_dir: Optional[Path] = None
    no_kanban: bool = False


class ProjectCommands:
    """Categorical project commands extracted from CLI."""
    
    @staticmethod
    def create() -> FilterCommand[ProjectCreateArgs, EmptyProject]:
        """Create a new project in Empty state."""
        def create_action(args: ProjectCreateArgs) -> EmptyProject:
            logger.info(f"Creating project: {args.name}")
            
            # Determine base directory
            base_dir = args.base_dir or Path.cwd() / "projects"
            project_path = base_dir / args.name
            
            # Generate project prefix
            prefix = ProjectCommands._generate_prefix(args.name)
            
            # Create project directory
            project_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Project {args.name} created at {project_path}")
            
            return Project[Empty](
                name=args.name,
                path=project_path,
                prefix=prefix,
                description=args.description,
                git_url=args.git_url,
                maintainers=args.maintainers or []
            )
        
        return FilterCommand(
            name="project_create",
            action=create_action,
            effects=[
                Effect(EffectType.FILESYSTEM, "Create project directory"),
                Effect(EffectType.AUDIT, "Project created")
            ],
            description="Create a new project with generated prefix"
        )
    
    @staticmethod
    def populate() -> FilterCommand[EmptyProject, PopulatedProject]:
        """Populate project with kanban structure (Empty -> Populated)."""
        def populate_action(project: EmptyProject) -> PopulatedProject:
            logger.info(f"Populating project {project.name} with kanban structure")
            
            # Create kanban directory structure
            kanban_dir = project.kanban_dir
            kanban_dir.mkdir(exist_ok=True)
            
            # Create kanban subdirectories
            subdirs = ["stories", "planning", "in-progress", "testing", "pr", "complete", "prompts"]
            for subdir in subdirs:
                subdir_path = kanban_dir / subdir
                subdir_path.mkdir(exist_ok=True)
                
                # Create README for each directory
                readme_file = subdir_path / "README.md"
                if not readme_file.exists():
                    readme_content = f"# {subdir.title()}\n\nStories in the {subdir} phase.\n"
                    readme_file.write_text(readme_content)
            
            # Create project configuration
            ProjectCommands._create_project_config(project)
            
            logger.info(f"Project {project.name} populated with kanban structure")
            
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
            name="project_populate",
            action=populate_action,
            effects=[
                Effect(EffectType.FILESYSTEM, "Create kanban directory structure"),
                Effect(EffectType.CONFIG, "Create project configuration"),
                Effect(EffectType.AUDIT, "Project populated")
            ],
            description="Populate project with kanban structure and configuration"
        )
    
    @staticmethod
    def activate() -> FilterCommand[PopulatedProject, ActiveProject]:
        """Activate project for development (Populated -> Active)."""
        def activate_action(project: PopulatedProject) -> ActiveProject:
            logger.info(f"Activating project {project.name}")
            
            # Update project configuration to mark as active
            config_file = project.config_file
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f) or {}
                
                config['status'] = 'active'
                config['activated_at'] = datetime.now().isoformat()
                
                with open(config_file, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
            
            logger.info(f"Project {project.name} activated")
            
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
            name="project_activate",
            action=activate_action,
            effects=[
                Effect(EffectType.CONFIG, "Update project status to active"),
                Effect(EffectType.AUDIT, "Project activated")
            ],
            description="Activate project for development"
        )
    
    @staticmethod
    def deactivate() -> FilterCommand[ActiveProject, PopulatedProject]:
        """Deactivate project (Active -> Populated)."""
        def deactivate_action(project: ActiveProject) -> PopulatedProject:
            logger.info(f"Deactivating project {project.name}")
            
            # Update project configuration to mark as inactive
            config_file = project.config_file
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f) or {}
                
                config['status'] = 'inactive'
                config['deactivated_at'] = datetime.now().isoformat()
                
                with open(config_file, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
            
            logger.info(f"Project {project.name} deactivated")
            
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
            name="project_deactivate",
            action=deactivate_action,
            effects=[
                Effect(EffectType.CONFIG, "Update project status to inactive"),
                Effect(EffectType.AUDIT, "Project deactivated")
            ],
            description="Deactivate project"
        )
    
    @staticmethod
    def delete() -> FilterCommand[Project, None]:
        """Delete a project and all its contents."""
        def delete_action(project: Project) -> None:
            logger.info(f"Deleting project {project.name}")
            
            # Remove project directory
            if project.path.exists():
                import shutil
                shutil.rmtree(project.path)
            
            logger.info(f"Project {project.name} deleted")
            return None
        
        return FilterCommand(
            name="project_delete",
            action=delete_action,
            effects=[
                Effect(EffectType.FILESYSTEM, "Remove project directory"),
                Effect(EffectType.AUDIT, "Project deleted")
            ],
            description="Delete project and all contents"
        )
    
    @staticmethod
    def list_projects() -> FilterCommand[Optional[Path], List[Project]]:
        """List all projects in the projects directory."""
        def list_action(base_dir: Optional[Path]) -> List[Project]:
            projects_dir = base_dir or Path.cwd() / "projects"
            projects = []
            
            if not projects_dir.exists():
                return projects
            
            for project_dir in projects_dir.iterdir():
                if project_dir.is_dir():
                    config_file = project_dir / "project.yaml"
                    if config_file.exists():
                        try:
                            with open(config_file, 'r') as f:
                                config = yaml.safe_load(f) or {}
                            
                            # Determine project state based on structure and config
                            if (project_dir / "kanban").exists():
                                if config.get('status') == 'active':
                                    state = Active
                                else:
                                    state = Populated
                            else:
                                state = Empty
                            
                            project = Project(
                                name=config.get('name', project_dir.name),
                                path=project_dir,
                                prefix=config.get('prefix', ''),
                                description=config.get('description', ''),
                                git_url=config.get('git_url'),
                                maintainers=config.get('maintainers', [])
                            )
                            projects.append(project)
                            
                        except Exception as e:
                            logger.warning(f"Error reading project config {config_file}: {e}")
            
            return projects
        
        return FilterCommand(
            name="project_list",
            action=list_action,
            effects=[
                Effect(EffectType.FILESYSTEM, "Scan projects directory"),
                Effect(EffectType.AUDIT, "Projects listed")
            ],
            description="List all projects in projects directory"
        )
    
    # Helper methods
    
    @staticmethod
    def _generate_prefix(name: str) -> str:
        """Generate a 5-character prefix from project name."""
        # Remove non-alphanumeric characters and convert to lowercase
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
        
        if len(clean_name) <= 5:
            return clean_name
        
        # For longer names, use first 5 characters or intelligent abbreviation
        if '-' in name or '_' in name:
            # If hyphenated, take first letters of each word
            words = re.split(r'[-_]', name.lower())
            prefix = ''.join(word[0] for word in words if word)[:5]
            if len(prefix) >= 3:
                return prefix
        
        # Fall back to first 5 characters
        return clean_name[:5]
    
    @staticmethod
    def _create_project_config(project: EmptyProject):
        """Create project configuration file."""
        config = {
            'name': project.name,
            'prefix': project.prefix,
            'description': project.description,
            'git_url': project.git_url,
            'maintainers': project.maintainers,
            'created_at': project.created_at.isoformat() if project.created_at else None,
            'version': '1.0'
        }
        
        config_file = project.config_file
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)


# Composable project workflows

def create_and_populate_project() -> FilterCommand[ProjectCreateArgs, PopulatedProject]:
    """Create and populate a project in one step."""
    create_cmd = ProjectCommands.create()
    populate_cmd = ProjectCommands.populate()
    
    return create_cmd.compose(populate_cmd)


def full_project_setup() -> FilterCommand[ProjectCreateArgs, ActiveProject]:
    """Complete project setup: create -> populate -> activate."""
    create_cmd = ProjectCommands.create()
    populate_cmd = ProjectCommands.populate()
    activate_cmd = ProjectCommands.activate()
    
    pipeline = sequence(create_cmd, populate_cmd, activate_cmd)
    return pipeline.compose()


def project_lifecycle_with_kanban(args: ProjectCreateArgs) -> FilterCommand[None, ActiveProject]:
    """Full project lifecycle starting from args."""
    if args.no_kanban:
        # Just create without kanban
        create_cmd = ProjectCommands.create().map_input(lambda _: args)
        return create_cmd
    else:
        # Full setup with kanban
        setup_cmd = full_project_setup().map_input(lambda _: args)
        return setup_cmd


if __name__ == "__main__":
    # Test project commands
    args = ProjectCreateArgs(
        name="test-project",
        description="A test project for validation",
        maintainers=["developer@example.com"]
    )
    
    # Test command composition
    create_cmd = ProjectCommands.create()
    project = create_cmd(args)
    
    print(f"Created project: {project.name}")
    print(f"Project prefix: {project.prefix}")
    print(f"Project path: {project.path}")
    print("Project commands module working correctly!")