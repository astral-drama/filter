"""Categorical repository commands extracted from CLI.

This module provides composable repository commands that follow
categorical composition laws and type safety.
"""

import json
import os
import subprocess
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ..command_algebra import FilterCommand, Effect, EffectType, sequence
from ..command_utils import run_git_command, run_command
from ..types import (
    Repository, Uninitialised, Initialised, Cloned, Configured,
    UninitRepo, InitRepo, ClonedRepo, ConfiguredRepo
)
from ..functors.repository import repository_functor
from ..logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class CloneArgs:
    """Arguments for repository cloning."""
    url: str
    target_dir: Optional[Path] = None
    branch: str = "main"
    fork: bool = False


@dataclass
class InitArgs:
    """Arguments for repository initialization."""
    path: Path
    create_github_repo: bool = False
    repo_name: Optional[str] = None
    description: Optional[str] = None
    private: bool = False


class RepositoryCommands:
    """Categorical repository commands extracted from CLI."""
    
    @staticmethod
    def clone() -> FilterCommand[CloneArgs, ClonedRepo]:
        """Clone a repository from remote (None -> Cloned)."""
        def clone_action(args: CloneArgs) -> ClonedRepo:
            logger.info(f"Cloning repository from {args.url}")
            
            # Determine target directory
            if args.target_dir:
                target_dir = args.target_dir
            else:
                repo_name = RepositoryCommands._extract_repo_name(args.url)
                target_dir = Path.cwd() / repo_name
            
            # Handle fork creation if requested
            clone_url = args.url
            if args.fork:
                logger.info("Creating fork before cloning")
                clone_url = RepositoryCommands._create_github_fork(args.url)
            
            # Clone the repository
            clone_cmd = ["clone", clone_url, str(target_dir)]
            if args.branch != "main":
                clone_cmd.extend(["-b", args.branch])
            
            result = run_git_command(clone_cmd)
            if not result.success:
                raise RuntimeError(f"Failed to clone repository: {result.stderr}")
            
            # Configure fork remotes if this was a fork
            if args.fork:
                RepositoryCommands._configure_fork_remotes(clone_url, args.url, target_dir)
            
            logger.info(f"Repository cloned to {target_dir}")
            
            return Repository[Cloned](
                path=target_dir,
                url=clone_url,
                branch=args.branch,
                metadata={"cloned_from": args.url, "is_fork": args.fork}
            )
        
        return FilterCommand(
            name="repository_clone",
            action=clone_action,
            effects=[
                Effect(EffectType.GIT, "Clone repository from remote"),
                Effect(EffectType.FILESYSTEM, "Create local repository"),
                Effect(EffectType.NETWORK, "Download repository data"),
                Effect(EffectType.AUDIT, "Repository cloned")
            ],
            description="Clone repository from remote URL"
        )
    
    @staticmethod
    def init() -> FilterCommand[InitArgs, InitRepo]:
        """Initialize repository with Filter (Uninitialised -> Initialised)."""
        def init_action(args: InitArgs) -> InitRepo:
            logger.info(f"Initializing Filter in repository at {args.path}")
            
            # Ensure directory exists
            args.path.mkdir(parents=True, exist_ok=True)
            
            # Initialize git repository if needed
            if not (args.path / ".git").exists():
                result = run_git_command(["init"], cwd=args.path)
                if not result.success:
                    raise RuntimeError(f"Failed to initialize git repository: {result.stderr}")
            
            # Create .filter directory structure
            filter_dir = args.path / ".filter"
            filter_dir.mkdir(exist_ok=True)
            
            # Create kanban structure
            RepositoryCommands._create_kanban_structure(filter_dir)
            
            # Create configuration
            RepositoryCommands._create_filter_config(filter_dir, args)
            
            # Create GitHub repository if requested
            if args.create_github_repo:
                RepositoryCommands._create_github_repository(args)
            
            logger.info(f"Filter initialized in {args.path}")
            
            return Repository[Initialised](
                path=args.path,
                metadata={"filter_initialized": True, "github_repo": args.create_github_repo}
            )
        
        return FilterCommand(
            name="repository_init",
            action=init_action,
            effects=[
                Effect(EffectType.GIT, "Initialize git repository"),
                Effect(EffectType.FILESYSTEM, "Create .filter directory structure"),
                Effect(EffectType.CONFIG, "Create Filter configuration"),
                Effect(EffectType.AUDIT, "Repository initialized")
            ],
            description="Initialize repository with Filter metadata and structure"
        )
    
    @staticmethod
    def configure() -> FilterCommand[InitRepo, ConfiguredRepo]:
        """Complete repository configuration (Initialised -> Configured)."""
        def configure_action(repo: InitRepo) -> ConfiguredRepo:
            logger.info(f"Configuring repository at {repo.path}")
            
            # Update configuration with advanced settings
            config_file = repo.filter_dir / "config.yaml"
            
            config = {
                "version": "1.0",
                "filter": {
                    "enabled": True,
                    "kanban": True,
                    "workspace": True,
                    "git_integration": True
                },
                "workspace": {
                    "default_template": "default",
                    "auto_cleanup": True
                },
                "git": {
                    "auto_commit": False,
                    "branch_protection": True
                }
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            # Create git hooks
            RepositoryCommands._setup_git_hooks(repo.path)
            
            # Create initial .gitignore
            RepositoryCommands._create_gitignore(repo.path)
            
            logger.info(f"Repository {repo.path} fully configured")
            
            return Repository[Configured](
                path=repo.path,
                url=repo.url,
                branch=repo.branch,
                metadata=repo.with_metadata(configured=True, git_hooks=True).metadata
            )
        
        return FilterCommand(
            name="repository_configure",
            action=configure_action,
            effects=[
                Effect(EffectType.CONFIG, "Update Filter configuration"),
                Effect(EffectType.GIT, "Setup git hooks"),
                Effect(EffectType.FILESYSTEM, "Create .gitignore"),
                Effect(EffectType.AUDIT, "Repository configured")
            ],
            description="Complete repository configuration with advanced settings"
        )
    
    @staticmethod
    def validate() -> FilterCommand[Repository, Repository]:
        """Validate repository structure and configuration."""
        def validate_action(repo: Repository) -> Repository:
            logger.info(f"Validating repository at {repo.path}")
            
            # Check git repository
            if not repo.is_git_repo():
                raise ValueError(f"Not a valid git repository: {repo.path}")
            
            # Check Filter structure if initialized
            if repo.has_filter():
                filter_dir = repo.filter_dir
                required_dirs = ["kanban", "kanban/stories", "kanban/planning", 
                               "kanban/in-progress", "kanban/testing", "kanban/complete"]
                
                for req_dir in required_dirs:
                    if not (filter_dir / req_dir).exists():
                        raise ValueError(f"Missing required directory: {req_dir}")
                
                # Check configuration
                config_file = filter_dir / "config.yaml"
                if not config_file.exists():
                    raise ValueError("Missing Filter configuration file")
            
            logger.info(f"Repository validation passed: {repo.path}")
            return repo
        
        return FilterCommand(
            name="repository_validate",
            action=validate_action,
            effects=[
                Effect(EffectType.AUDIT, "Repository validation")
            ],
            description="Validate repository structure and configuration"
        )
    
    # Helper methods
    
    @staticmethod
    def _extract_repo_name(url: str) -> str:
        """Extract repository name from URL."""
        # Handle various URL formats
        if url.endswith('.git'):
            url = url[:-4]
        
        return Path(url).name
    
    @staticmethod
    def _create_github_fork(original_url: str) -> str:
        """Create a GitHub fork and return the fork URL."""
        # Parse GitHub URL
        if "github.com" not in original_url:
            raise ValueError("Fork creation only supported for GitHub repositories")
        
        # Extract owner and repo
        parts = original_url.replace("https://github.com/", "").replace(".git", "").split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid GitHub URL format: {original_url}")
        
        owner, repo = parts
        
        # Use GitHub CLI to create fork
        result = run_command(["gh", "repo", "fork", f"{owner}/{repo}", "--clone=false"])
        if not result.success:
            raise RuntimeError(f"Failed to create fork: {result.stderr}")
        
        # Get current user
        user_result = run_command(["gh", "api", "user"])
        if not user_result.success:
            raise RuntimeError("Failed to get GitHub user information")
        
        user_data = json.loads(user_result.stdout)
        username = user_data["login"]
        
        return f"https://github.com/{username}/{repo}.git"
    
    @staticmethod
    def _configure_fork_remotes(fork_url: str, original_url: str, repo_path: Path):
        """Configure git remotes for a forked repository."""
        # Add upstream remote
        result = run_git_command(["remote", "add", "upstream", original_url], cwd=repo_path)
        if not result.success:
            logger.warning(f"Failed to add upstream remote: {result.stderr}")
        
        # Fetch upstream
        result = run_git_command(["fetch", "upstream"], cwd=repo_path)
        if not result.success:
            logger.warning(f"Failed to fetch upstream: {result.stderr}")
    
    @staticmethod
    def _create_kanban_structure(filter_dir: Path):
        """Create kanban directory structure."""
        kanban_dir = filter_dir / "kanban"
        kanban_dir.mkdir(exist_ok=True)
        
        # Create kanban subdirectories
        subdirs = ["stories", "planning", "in-progress", "testing", "pr", "complete", "prompts"]
        for subdir in subdirs:
            (kanban_dir / subdir).mkdir(exist_ok=True)
        
        # Create README files
        for subdir in subdirs:
            readme_file = kanban_dir / subdir / "README.md"
            if not readme_file.exists():
                readme_content = f"# {subdir.title()}\n\nStories in the {subdir} phase.\n"
                readme_file.write_text(readme_content)
    
    @staticmethod
    def _create_filter_config(filter_dir: Path, args: InitArgs):
        """Create initial Filter configuration."""
        config = {
            "version": "1.0",
            "filter": {
                "enabled": True,
                "kanban": True
            }
        }
        
        if args.repo_name:
            config["repository"] = {
                "name": args.repo_name,
                "description": args.description or ""
            }
        
        config_file = filter_dir / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    
    @staticmethod
    def _create_github_repository(args: InitArgs):
        """Create GitHub repository."""
        if not args.repo_name:
            args.repo_name = args.path.name
        
        gh_args = ["repo", "create", args.repo_name]
        
        if args.description:
            gh_args.extend(["--description", args.description])
        
        if args.private:
            gh_args.append("--private")
        else:
            gh_args.append("--public")
        
        result = run_command(["gh"] + gh_args, cwd=args.path)
        if not result.success:
            raise RuntimeError(f"Failed to create GitHub repository: {result.stderr}")
    
    @staticmethod
    def _setup_git_hooks(repo_path: Path):
        """Setup git hooks for Filter integration."""
        hooks_dir = repo_path / ".git" / "hooks"
        
        # Pre-commit hook
        pre_commit_hook = hooks_dir / "pre-commit"
        pre_commit_content = """#!/bin/bash
# Filter pre-commit hook
echo "Filter: Running pre-commit checks..."

# Add any Filter-specific pre-commit logic here
# For example: validate story references, check kanban consistency

exit 0
"""
        pre_commit_hook.write_text(pre_commit_content)
        pre_commit_hook.chmod(0o755)
    
    @staticmethod
    def _create_gitignore(repo_path: Path):
        """Create .gitignore file with Filter-specific patterns."""
        gitignore_file = repo_path / ".gitignore"
        
        if gitignore_file.exists():
            content = gitignore_file.read_text()
        else:
            content = ""
        
        filter_patterns = """
# Filter workspace directories
workspaces/
.filter/logs/
.filter/tmp/

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db
"""
        
        if "# Filter workspace directories" not in content:
            content += filter_patterns
            gitignore_file.write_text(content)


# Composable repository workflows

def clone_and_init() -> FilterCommand[CloneArgs, InitRepo]:
    """Clone repository and initialize Filter."""
    clone_cmd = RepositoryCommands.clone()
    
    # Transform cloned repo to init args
    def cloned_to_init_args(cloned_repo: ClonedRepo) -> InitArgs:
        return InitArgs(path=cloned_repo.path)
    
    init_cmd = RepositoryCommands.init().map_input(cloned_to_init_args)
    
    return clone_cmd.compose(init_cmd)


def full_repository_setup() -> FilterCommand[CloneArgs, ConfiguredRepo]:
    """Complete repository setup: clone -> init -> configure."""
    clone_cmd = RepositoryCommands.clone()
    
    def cloned_to_init_args(cloned_repo: ClonedRepo) -> InitArgs:
        return InitArgs(path=cloned_repo.path)
    
    init_cmd = RepositoryCommands.init().map_input(cloned_to_init_args)
    configure_cmd = RepositoryCommands.configure()
    
    pipeline = sequence(clone_cmd, init_cmd, configure_cmd)
    return pipeline.compose()


if __name__ == "__main__":
    # Test repository commands
    init_args = InitArgs(
        path=Path("/tmp/test-repo"),
        repo_name="test-repo",
        description="Test repository for validation"
    )
    
    # Test command composition
    init_cmd = RepositoryCommands.init()
    repo = init_cmd(init_args)
    
    print(f"Initialized repository: {repo.name}")
    print(f"Repository path: {repo.path}")
    print("Repository commands module working correctly!")