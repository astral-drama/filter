"""Command line interface for Filter."""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

from .command_utils import (
    check_command_available,
    ensure_command_available,
    run_command,
    run_git_command,
)
from .config import load_config
from .logging_config import audit_log, get_logger, setup_logging
from .projects import (
    create_project,
    delete_project,
    find_story_in_projects,
    list_projects,
)
from .workspace import (
    create_story_workspace,
    create_workspace,
    delete_workspace,
    exec_workspace_command,
    list_templates,
    render_template,
    stop_workspace,
)


def initialize_logging():
    """Initialize logging for Filter commands."""
    try:
        config = load_config()
        setup_logging(config)
        return get_logger(__name__)
    except Exception as e:
        # Fallback to basic logging if configuration fails
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(levelname)s: %(message)s'
        )
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to initialize full logging configuration: {e}")
        return logger


def workspace_create_command(args):
    """Handle workspace create subcommand."""
    logger = initialize_logging()

    # Audit log the command
    audit_log("workspace create command initiated",
             workspace_name=args.name if args.name else "list_templates",
             template=getattr(args, 'template', 'default'))

    if args.list_templates:
        logger.info("Listing available workspace templates")
        templates = list_templates()
        if not templates:
            logger.warning("No templates found in docker/templates/")
            print("No templates found in docker/templates/")
            return

        print("Available workspace templates:")
        for template in templates:
            print(f"  {template['name']}: {template.get('description', 'No description')}")
        logger.info(f"Listed {len(templates)} available templates")
        return

    if not args.name:
        logger.error("Workspace name is required but not provided")
        print("Error: workspace name is required", file=sys.stderr)
        sys.exit(1)

    try:
        base_dir = None
        if hasattr(args, 'base_dir') and args.base_dir:
            base_dir = Path(args.base_dir)
        workspace_path = create_workspace(
            args.name,
            base_dir,
            args.template
        )
        print(f"Workspace '{args.name}' created at: {workspace_path}")
        print(f"To start: cd {workspace_path} && docker compose up")
    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def workspace_down_command(args):
    """Handle workspace down subcommand."""
    logging.basicConfig(level=logging.INFO)

    try:
        base_dir = None
        if hasattr(args, 'base_dir') and args.base_dir:
            base_dir = Path(args.base_dir)
        stop_workspace(args.name, base_dir)
        print(f"Workspace '{args.name}' stopped successfully")
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def workspace_delete_command(args):
    """Handle workspace delete subcommand."""
    logging.basicConfig(level=logging.INFO)

    try:
        base_dir = None
        if hasattr(args, 'base_dir') and args.base_dir:
            base_dir = Path(args.base_dir)
        delete_workspace(args.name, base_dir, args.force)
        print(f"Workspace '{args.name}' deleted successfully")
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def story_create_command(args):
    """Handle story creation using template."""
    import yaml

    from .config import get_projects_directory

    logging.basicConfig(level=logging.INFO)

    try:
        # Find project for this story prefix or ask user to specify
        if hasattr(args, 'project') and args.project:
            project_name = args.project
            projects_dir = get_projects_directory()
            project_dir = projects_dir / project_name
            if not project_dir.exists():
                raise RuntimeError(f"Project '{project_name}' not found")
        else:
            # TODO: Could auto-detect from story_id prefix in the future
            print("Error: --project is required for story creation", file=sys.stderr)
            sys.exit(1)

        # Read project config
        config_file = project_dir / "project.yaml"
        if not config_file.exists():
            raise RuntimeError(f"Project config not found: {config_file}")

        with open(config_file) as f:
            project_config = yaml.safe_load(f)

        # Generate story ID if not provided
        if hasattr(args, 'story_id') and args.story_id:
            story_id = args.story_id
        else:
            # Auto-generate next story ID
            story_id = generate_next_story_id(project_dir, project_config.get('prefix', project_name[:5]))

        # Get required information
        story_description = args.description
        repository = project_config.get('git_url', '')
        branch_from = getattr(args, 'branch_from', 'main')
        merge_to = getattr(args, 'merge_to', 'main')
        feature_branch = f"{story_id}-{args.feature_suffix}" if hasattr(args, 'feature_suffix') and args.feature_suffix else story_id

        # Load and render template
        template_dir = Path(__file__).parent.parent.parent / "story" / "templates"
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("default.md.j2")

        rendered = template.render(
            story_id=story_id,
            story_description=story_description,
            repository=repository,
            branch_from=branch_from,
            merge_to=merge_to,
            feature_branch=feature_branch
        )

        # Write story file
        story_file = project_dir / "kanban" / "stories" / f"{story_id}.md"
        story_file.parent.mkdir(parents=True, exist_ok=True)

        with open(story_file, 'w') as f:
            f.write(rendered)

        print(f"Story '{story_id}' created at: {story_file}")
        print(f"To create workspace: filter story workspace {story_id}")

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def generate_next_story_id(project_dir: Path, prefix: str) -> str:
    """Generate the next story ID by looking at existing stories."""
    import re

    stories_dir = project_dir / "kanban" / "stories"
    if not stories_dir.exists():
        return f"{prefix}-1"

    max_id = 0
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)\.md$")

    for story_file in stories_dir.glob("*.md"):
        match = pattern.match(story_file.name)
        if match:
            story_num = int(match.group(1))
            max_id = max(max_id, story_num)

    return f"{prefix}-{max_id + 1}"


def story_delete_command(args):
    """Handle story deletion."""
    logging.basicConfig(level=logging.INFO)

    try:
        # Find the story
        story_info = find_story_in_projects(args.story_id)
        if not story_info:
            raise RuntimeError(f"Story '{args.story_id}' not found in any project")

        story_file = story_info['story_file']
        project_name = story_info['project_name']

        # Confirm deletion unless forced
        if not args.force:
            response = input(f"Delete story '{args.story_id}' from project '{project_name}'? (y/N): ")
            if response.lower() != 'y':
                print("Deletion cancelled")
                return

        # Delete the story file
        story_file.unlink()
        print(f"Story '{args.story_id}' deleted from project '{project_name}'")

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def story_workspace_command(args):
    """Handle story workspace creation."""
    logging.basicConfig(level=logging.INFO)

    try:
        base_dir = None
        if hasattr(args, 'base_dir') and args.base_dir:
            base_dir = Path(args.base_dir)

        workspace_path = create_story_workspace(
            args.story_name,
            base_dir,
            args.template,
            custom_name=getattr(args, 'name', None)
        )
        print(f"Story workspace '{args.story_name}' created at: {workspace_path}")
        print(f"To start: cd {workspace_path} && docker compose up")

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def story_command(args):
    """Handle story command routing."""
    # For backwards compatibility - if no subcommand specified, show help
    if not hasattr(args, 'story_func'):
        print("Error: story command requires a subcommand (create, delete, workspace)", file=sys.stderr)
        print("Use 'filter story --help' for more information")
        sys.exit(1)

    args.story_func(args)


def workspace_command(args):
    """Handle workspace command routing."""
    # For backwards compatibility - if no subcommand specified, default to create
    if not hasattr(args, 'workspace_action') or args.workspace_action is None:
        # Check if this looks like old-style usage
        if hasattr(args, 'name') and args.name:
            workspace_create_command(args)
        else:
            print("Error: Please specify a workspace action: create, down, or delete", file=sys.stderr)
            print("Usage: workspace create <name>", file=sys.stderr)
            sys.exit(1)
    else:
        # Subcommand specified, call the appropriate function
        args.func(args)


def init_command(args):
    """Handle filter init command."""
    logging.basicConfig(level=logging.INFO)

    try:
        from .config import create_filter_directory, is_filter_repository

        repo_path = Path.cwd()

        # Check if already initialized
        if is_filter_repository(repo_path) and not args.force:
            print(f"Error: Filter already initialized in {repo_path}")
            print("Use --force to reinitialize")
            sys.exit(1)

        # Check for existing kanban before initialization
        from .config import detect_existing_kanban
        existing_kanban = detect_existing_kanban(repo_path)

        # Create .filter directory structure
        filter_dir = create_filter_directory(
            repo_path,
            project_name=args.project_name,
            prefix=args.prefix,
            migrate_kanban=True
        )

        if existing_kanban:
            print(f"Detected existing kanban directory at: {existing_kanban}")
            print(f"Stories and structure migrated to: {filter_dir / 'kanban'}")
            print(f"You may want to remove the old kanban directory: rm -rf {existing_kanban}")

        print(f"Filter initialized in {repo_path}")
        print(f"Created .filter directory at: {filter_dir}")
        print(f"Kanban board available at: {filter_dir / 'kanban'}")
        print(f"Project metadata: {filter_dir / 'metadata.yaml'}")
        print(f"Repository config: {filter_dir / 'config.yaml'}")

        # Read the generated metadata to show prefix
        metadata_file = filter_dir / "metadata.yaml"
        if metadata_file.exists():
            import yaml
            with open(metadata_file, encoding='utf-8') as f:
                metadata = yaml.safe_load(f)
                prefix = metadata.get('prefix', 'unknown')
                project_name = metadata.get('name', 'unknown')
                print(f"Project: {project_name}")
                print(f"Story prefix: {prefix} (use for stories like {prefix}-1, {prefix}-2-feature)")

        print("\nNext steps:")
        print("1. Add stories to .filter/kanban/stories/")
        print("2. Move stories to appropriate stages (planning, in-progress, etc.)")
        print("3. Create workspaces with: filter story workspace <story-name>")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def check_git_push_access(repo_path: Path, remote: str = "origin") -> bool:
    """Check if we have push access to a git repository.
    
    Args:
        repo_path: Path to the git repository
        remote: Remote name to check (default: origin)
        
    Returns:
        True if push access is available, False otherwise
    """
    try:
        # Use git push --dry-run to test push access without actually pushing
        result = run_git_command([
            "push", "--dry-run", remote, "HEAD"
        ], cwd=repo_path, check=False)

        # If dry-run succeeds, we have push access
        return result.success
    except Exception:
        return False


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse GitHub URL and return (owner, repo) tuple.
    
    Args:
        url: GitHub repository URL
        
    Returns:
        Tuple of (owner, repo_name)
        
    Raises:
        RuntimeError: If URL is not a valid GitHub repository URL
    """
    if not url.startswith("https://github.com/"):
        raise RuntimeError("Not a GitHub repository URL")

    path = url.replace("https://github.com/", "").rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]

    parts = path.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise RuntimeError("Invalid GitHub repository path")

    # Validate owner and repo names for security
    owner, repo = parts[0], parts[1]
    if not validate_github_repo_name(owner) or not validate_github_repo_name(repo):
        raise RuntimeError("Invalid GitHub owner or repository name")

    return owner, repo


def sanitize_directory_name(name: str) -> str:
    """Sanitize directory name to prevent path traversal.
    
    Args:
        name: Directory name to sanitize
        
    Returns:
        Safe directory name
    """
    import re

    # Remove path separators and dangerous characters
    safe_name = re.sub(r'[^\w\-\.]', '_', name)
    # Prevent empty or hidden directories
    if not safe_name or safe_name.startswith('.'):
        safe_name = "repository"
    # Limit length and remove trailing dots
    return safe_name[:50].rstrip('.')


def configure_fork_remotes(fork_url: str, original_url: str, target_dir: Path) -> None:
    """Configure git remotes for fork workflow with validation.
    
    Args:
        fork_url: URL of the forked repository
        original_url: URL of the original repository
        target_dir: Local repository directory
        
    Raises:
        RuntimeError: If URL validation fails
    """
    # Validate URLs before using them in git commands
    if not validate_git_url(fork_url) or not validate_git_url(original_url):
        raise RuntimeError("Invalid git URL provided for remote configuration")

    try:
        # Update remote origin to point to fork
        run_git_command(["remote", "set-url", "origin", fork_url], cwd=target_dir, check=True)

        # Add upstream remote pointing to original repository
        run_git_command(["remote", "add", "upstream", original_url], cwd=target_dir, check=True)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to configure git remotes: {e.stderr}")


def create_github_fork(original_url: str) -> str:
    """Create a fork of a GitHub repository using gh CLI.
    
    Args:
        original_url: Original repository URL
        
    Returns:
        URL of the forked repository
        
    Raises:
        RuntimeError: If gh CLI is not available or fork creation fails
    """
    # Parse and validate GitHub URL
    owner, repo = parse_github_url(original_url)
    repo_path = f"{owner}/{repo}"

    # Check if gh CLI is available
    ensure_command_available('gh', "GitHub CLI (gh) is required for fork creation. Install from https://cli.github.com/")

    try:
        # Create fork using gh CLI
        result = run_command(['gh', 'repo', 'fork', repo_path, '--clone=false'], check=True)

        # Get current GitHub user to construct fork URL
        user_result = run_command(['gh', 'api', 'user'], check=True)
        user_data = json.loads(user_result.stdout)
        github_user = user_data.get('login')

        if not github_user:
            raise RuntimeError("Could not determine GitHub username")

        # Validate the username for security
        if not validate_github_repo_name(github_user):
            raise RuntimeError("Invalid GitHub username returned from API")

        fork_url = f"https://github.com/{github_user}/{repo}.git"
        return fork_url

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to create fork: {e.stderr}")


def clone_command(args):
    """Handle filter clone command."""
    logger = initialize_logging()

    try:
        from .config import create_filter_directory, is_filter_repository

        # Validate conflicting fork options
        if getattr(args, 'no_fork', False) and (getattr(args, 'fork', False) or getattr(args, 'yes', False)):
            print("Error: Cannot use --no-fork with --fork or -y flags", file=sys.stderr)
            sys.exit(1)

        # Audit log the command
        audit_log("clone command initiated",
                 git_url=args.git_url if args.git_url else "missing",
                 directory=args.directory if hasattr(args, 'directory') and args.directory else "auto")

        # Validate git URL
        if not args.git_url:
            logger.error("Git URL is required but not provided")
            print("Error: git URL is required", file=sys.stderr)
            sys.exit(1)

        # Validate git URL format for security
        if not validate_git_url(args.git_url):
            logger.error(f"Invalid git URL format provided: {args.git_url}")
            print("Error: Invalid git URL format", file=sys.stderr)
            sys.exit(1)

        # Ensure git is available
        ensure_command_available('git', "Git is required for cloning repositories")

        # Determine target directory
        if args.directory:
            target_dir = Path(args.directory).resolve()
        else:
            # Extract repository name from URL and sanitize for security
            repo_name = args.git_url.rstrip('/').split('/')[-1]
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
            safe_repo_name = sanitize_directory_name(repo_name)
            target_dir = Path.cwd() / safe_repo_name

        # Check if directory already exists
        if target_dir.exists():
            print(f"Error: Directory {target_dir} already exists", file=sys.stderr)
            sys.exit(1)

        logger.info(f"Cloning repository {args.git_url} to {target_dir}")
        print(f"Cloning repository {args.git_url} to {target_dir}")

        # Clone repository using our command utility
        try:
            result = run_git_command([
                "clone", args.git_url, str(target_dir)
            ], check=True)
            logger.info(f"Repository cloned successfully to {target_dir}")
            print(f"Repository cloned successfully to {target_dir}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone repository: {e.stderr}")
            print(f"Error cloning repository: {e.stderr}", file=sys.stderr)
            sys.exit(1)

        # Change to the cloned directory and initialize Filter
        original_cwd = Path.cwd()
        try:
            os.chdir(target_dir)

            # Check push access to the repository
            has_push_access = check_git_push_access(target_dir)

            if not has_push_access and not getattr(args, 'no_fork', False):
                # Ask user if they want to create a fork
                print("\n⚠️  You don't have push access to this repository.")

                # Check if this is a GitHub repository and gh CLI is available
                if "github.com" in args.git_url and check_command_available('gh'):
                    # Auto-answer yes if --fork or -y flag is provided
                    if getattr(args, 'fork', False) or getattr(args, 'yes', False):
                        print("Auto-creating fork due to --fork or -y flag...")
                        should_fork = True
                    else:
                        response = input("Would you like to create a fork? (y/N): ")
                        should_fork = response.lower() == 'y'
                    
                    if should_fork:
                        try:
                            print("Creating fork...")
                            fork_url = create_github_fork(args.git_url)
                            print(f"Fork created: {fork_url}")

                            # Configure remotes securely
                            print("Updating remote origin to point to your fork...")
                            configure_fork_remotes(fork_url, args.git_url, target_dir)

                            print("✅ Repository configured with fork as origin and original as upstream")

                        except RuntimeError as e:
                            print(f"⚠️  Fork creation failed: {e}")
                            print("You can continue working with read-only access to the original repository.")
                    else:
                        print("Continuing with read-only access to the original repository.")
                        print("You won't be able to push changes directly.")
                else:
                    print("Fork creation requires GitHub CLI (gh) and a GitHub repository.")
                    print("Continuing with read-only access to the original repository.")

            # Check if already initialized
            if is_filter_repository(target_dir) and not args.force:
                print("Repository already has Filter initialized")
                print("Use --force to reinitialize")
            else:
                # Check for existing kanban before initialization
                from .config import detect_existing_kanban
                existing_kanban = detect_existing_kanban(target_dir)

                # Determine project name
                project_name = args.project_name or target_dir.name

                # Create .filter directory structure
                filter_dir = create_filter_directory(
                    target_dir,
                    project_name=project_name,
                    prefix=args.prefix,
                    migrate_kanban=True
                )

                if existing_kanban:
                    print(f"Detected existing kanban directory at: {existing_kanban}")
                    print(f"Stories and structure migrated to: {filter_dir / 'kanban'}")
                    print(f"You may want to remove the old kanban directory: rm -rf {existing_kanban}")

                print(f"Filter initialized in {target_dir}")
                print(f"Created .filter directory at: {filter_dir}")

                # Read the generated metadata to show prefix
                metadata_file = filter_dir / "metadata.yaml"
                if metadata_file.exists():
                    import yaml
                    with open(metadata_file, encoding='utf-8') as f:
                        metadata = yaml.safe_load(f)
                        prefix = metadata.get('prefix', 'unknown')
                        project_name = metadata.get('name', 'unknown')
                        print(f"Project: {project_name}")
                        print(f"Story prefix: {prefix} (use for stories like {prefix}-1, {prefix}-2-feature)")

            print(f"\nRepository ready at: {target_dir}")
            print("\nNext steps:")
            print("1. Add stories to .filter/kanban/stories/")
            print("2. Move stories to appropriate stages (planning, in-progress, etc.)")
            print("3. Create workspaces with: filter story workspace <story-name>")

        finally:
            os.chdir(original_cwd)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def validate_git_url(url: str) -> bool:
    """Validate git URL format for security.
    
    Args:
        url: Git URL to validate
        
    Returns:
        True if URL appears to be a valid git URL
    """
    import re

    # Allow common git URL patterns
    patterns = [
        r'^https://github\.com/[a-zA-Z0-9\-_\.]+/[a-zA-Z0-9\-_\.]+(?:\.git)?/?$',
        r'^git@github\.com:[a-zA-Z0-9\-_\.]+/[a-zA-Z0-9\-_\.]+(?:\.git)?$',
        r'^https://gitlab\.com/[a-zA-Z0-9\-_\.]+/[a-zA-Z0-9\-_\.]+(?:\.git)?/?$',
        r'^git@gitlab\.com:[a-zA-Z0-9\-_\.]+/[a-zA-Z0-9\-_\.]+(?:\.git)?$',
        r'^https://[a-zA-Z0-9\-_\.]+/[a-zA-Z0-9\-_\.]+/[a-zA-Z0-9\-_\.]+(?:\.git)?/?$'
    ]

    return any(re.match(pattern, url) for pattern in patterns)


def safe_getattr(obj, attr: str, default: str = '') -> str:
    """Safely get attribute value with fallback to default.
    
    Args:
        obj: Object to get attribute from
        attr: Attribute name
        default: Default value if attribute is None or empty
        
    Returns:
        Attribute value or default
    """
    return getattr(obj, attr, default) or default


def validate_github_repo_name(name: str) -> bool:
    """Validate GitHub repository name according to GitHub rules.
    
    Args:
        name: Repository name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not name or len(name) > 100:
        return False
    # Allow alphanumeric, hyphens, underscores, and dots
    return re.match(r'^[a-zA-Z0-9\-_.]+$', name) is not None


def create_github_repository(project_name: str, github_user: str = None, description: str = "", is_private: bool = False) -> str:
    """Create a GitHub repository using gh CLI.
    
    Args:
        project_name: Name of the project/repository
        github_user: GitHub username (if None, uses current gh user)
        description: Repository description
        is_private: Whether to create a private repository
        
    Returns:
        URL of the created repository
        
    Raises:
        RuntimeError: If gh CLI is not available or repository creation fails
    """
    # Validate repository name for security
    if not validate_github_repo_name(project_name):
        raise RuntimeError(f"Invalid repository name: '{project_name}'. Must contain only alphanumeric characters, hyphens, underscores, and dots, and be 100 characters or less.")

    # Check if gh CLI is available
    try:
        subprocess.run(['gh', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("GitHub CLI (gh) is not installed or not in PATH. Install it from https://cli.github.com/")

    # Get current GitHub user if not specified
    if not github_user:
        try:
            result = subprocess.run(['gh', 'api', 'user'], capture_output=True, text=True, check=True)
            user_data = json.loads(result.stdout)
            github_user = user_data.get('login')
            if not github_user:
                raise RuntimeError("Could not determine GitHub username")
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            raise RuntimeError("Failed to get GitHub user information. Make sure you're authenticated with 'gh auth login'")

    # Construct repository name
    repo_name = f"{github_user}/{project_name}"

    # Build gh repo create command
    cmd = ['gh', 'repo', 'create', repo_name]

    if is_private:
        cmd.append('--private')
    else:
        cmd.append('--public')

    if description:
        cmd.extend(['--description', description])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        repo_url = f"https://github.com/{repo_name}.git"
        logging.info(f"Created GitHub repository: {repo_url}")
        return repo_url
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to create GitHub repository: {e.stderr.strip()}")


def project_create_command(args):
    """Handle project create subcommand."""
    logging.basicConfig(level=logging.INFO)

    try:
        base_dir = None
        if hasattr(args, 'base_dir') and args.base_dir:
            base_dir = Path(args.base_dir)

        # Handle GitHub repository creation if requested
        git_url = safe_getattr(args, 'git_url')

        if getattr(args, 'create_repo', False):
            if git_url:
                print("Warning: --create-repo specified but --git-url already provided. Using existing git-url.")
            else:
                description = safe_getattr(args, 'description')
                github_user = getattr(args, 'github_user', None)
                is_private = getattr(args, 'private', False)

                print(f"Creating GitHub repository for project '{args.name}'...")
                git_url = create_github_repository(
                    args.name,
                    github_user=github_user,
                    description=description,
                    is_private=is_private
                )
                print(f"GitHub repository created: {git_url}")

        project_path = create_project(
            args.name,
            base_dir,
            copy_kanban=not args.no_kanban,
            description=safe_getattr(args, 'description'),
            git_url=git_url,
            maintainers=getattr(args, 'maintainers', None) or []
        )

        print(f"Project '{args.name}' created at: {project_path}")

        # Load and display the generated config
        from .projects import generate_project_prefix, load_project_config
        config = load_project_config(project_path)
        if config:
            prefix = config.get('prefix', generate_project_prefix(args.name))
            print(f"Story prefix: {prefix} (use for stories like {prefix}-1, {prefix}-2-refactor)")

        if not args.no_kanban:
            print(f"Kanban structure available at: {project_path / 'kanban'}")

        print(f"Project config: {project_path / 'project.yaml'}")

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def project_list_command(args):
    """Handle project list subcommand."""
    try:
        base_dir = None
        if hasattr(args, 'base_dir') and args.base_dir:
            base_dir = Path(args.base_dir)

        projects = list_projects(base_dir)
        if projects:
            print("Available projects:")
            for project in projects:
                print(f"  {project}")
        else:
            print("No projects found.")

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def project_delete_command(args):
    """Handle project delete subcommand."""
    logging.basicConfig(level=logging.INFO)

    try:
        base_dir = None
        if hasattr(args, 'base_dir') and args.base_dir:
            base_dir = Path(args.base_dir)

        delete_project(args.name, base_dir, args.force)
        print(f"Project '{args.name}' deleted successfully")

    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def project_command(args):
    """Handle project command routing."""
    if not hasattr(args, 'project_action') or args.project_action is None:
        print("Error: Please specify a project action: create, list, or delete", file=sys.stderr)
        print("Usage: project create <name>", file=sys.stderr)
        sys.exit(1)
    else:
        # Subcommand specified, call the appropriate function
        args.func(args)


def claude_command(args):
    """Handle claude session command."""
    try:
        command = ["claude"]
        if hasattr(args, 'resume') and args.resume:
            command.append("-r")
        command.append("--dangerously-skip-permissions")

        exit_code = exec_workspace_command(args.workspace, command)
        sys.exit(exit_code)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def bash_command(args):
    """Handle bash shell command."""
    try:
        command = ["bash"]
        if hasattr(args, 'command_args') and args.command_args:
            command.extend(args.command_args)
        exit_code = exec_workspace_command(args.workspace, command)
        sys.exit(exit_code)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def template_command(args):
    """Handle template rendering command."""
    # Load template variables from multiple sources
    context = {}

    # 1. Load from YAML config file (lowest priority)
    if Path(args.config).exists():
        try:
            with open(args.config) as f:
                config_data = yaml.safe_load(f)
                if config_data:
                    context.update(config_data)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML config file {args.config}: {e}",
                  file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading config file {args.config}: {e}",
                  file=sys.stderr)
            sys.exit(1)

    # 2. Load from .env file (medium priority - overrides config)
    env_file = args.env_file or ".env"
    if Path(env_file).exists():
        load_dotenv(env_file)
        # Add all environment variables to context
        context.update(os.environ)
    elif args.env_file:
        # If specific .env file was requested but doesn't exist, error
        print(f"Error: .env file not found: {args.env_file}",
              file=sys.stderr)
        sys.exit(1)

    # 3. Parse command line template variables (highest priority)
    for var in args.var:
        if "=" not in var:
            print(f"Error: Invalid variable format '{var}'. "
                  "Use key=value format.", file=sys.stderr)
            sys.exit(1)
        key, value = var.split("=", 1)
        context[key] = value

    try:
        # Render template and output to stdout
        result = render_template(args.template, context)
        print(result, end="")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error rendering template: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Filter - LLM-Powered Kanban board CLI"
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Workspace command with subcommands
    workspace_parser = subparsers.add_parser(
        'workspace', help='Manage Docker workspaces'
    )
    workspace_subparsers = workspace_parser.add_subparsers(
        dest='workspace_action', help='Workspace actions'
    )

    # Create subcommand (default action)
    create_parser = workspace_subparsers.add_parser(
        'create', help='Create a new Docker workspace'
    )
    create_parser.add_argument(
        'name', help='Workspace name (e.g., v3, dev, test)'
    )
    create_parser.add_argument(
        '--template', '-t', default='default',
        help='Template to use (default: default)'
    )
    create_parser.add_argument(
        '--base-dir',
        help='Base directory for workspaces (default: from config)'
    )
    create_parser.add_argument(
        '--list-templates', action='store_true',
        help='List available templates'
    )
    create_parser.set_defaults(func=workspace_create_command)

    # Down subcommand
    down_parser = workspace_subparsers.add_parser(
        'down', help='Stop a running workspace'
    )
    down_parser.add_argument(
        'name', help='Workspace name to stop'
    )
    down_parser.add_argument(
        '--base-dir',
        help='Base directory for workspaces (default: from config)'
    )
    down_parser.set_defaults(func=workspace_down_command)

    # Delete subcommand
    delete_parser = workspace_subparsers.add_parser(
        'delete', help='Delete a workspace'
    )
    delete_parser.add_argument(
        'name', help='Workspace name to delete'
    )
    delete_parser.add_argument(
        '--base-dir',
        help='Base directory for workspaces (default: from config)'
    )
    delete_parser.add_argument(
        '--force', '-f', action='store_true',
        help='Force delete running workspace (stops it first)'
    )
    delete_parser.set_defaults(func=workspace_delete_command)

    # Set default routing function for workspace command
    workspace_parser.set_defaults(func=workspace_command)

    # Init command
    init_parser = subparsers.add_parser(
        'init', help='Initialize Filter in a repository'
    )
    init_parser.add_argument(
        '--project-name',
        help='Project name (defaults to repository directory name)'
    )
    init_parser.add_argument(
        '--prefix',
        help='Story prefix (auto-generated if not provided)'
    )
    init_parser.add_argument(
        '--force', '-f', action='store_true',
        help='Force initialization even if .filter directory exists'
    )
    init_parser.set_defaults(func=init_command)

    # Clone command
    clone_parser = subparsers.add_parser(
        'clone', help='Clone a repository and initialize Filter'
    )
    clone_parser.add_argument(
        'git_url',
        help='Git repository URL to clone'
    )
    clone_parser.add_argument(
        'directory', nargs='?',
        help='Target directory (defaults to repository name)'
    )
    clone_parser.add_argument(
        '--project-name',
        help='Project name (defaults to repository directory name)'
    )
    clone_parser.add_argument(
        '--prefix',
        help='Story prefix (auto-generated if not provided)'
    )
    clone_parser.add_argument(
        '--force', '-f', action='store_true',
        help='Force initialization even if .filter directory exists'
    )
    clone_parser.add_argument(
        '--no-fork', action='store_true',
        help='Skip fork creation even if push access is denied'
    )
    clone_parser.add_argument(
        '--fork', action='store_true',
        help='Automatically create fork if push access is denied (non-interactive)'
    )
    clone_parser.add_argument(
        '-y', '--yes', action='store_true',
        help='Answer yes to all questions (equivalent to --fork for clone)'
    )
    clone_parser.set_defaults(func=clone_command)

    # Project command with subcommands
    project_parser = subparsers.add_parser('project', help='Manage projects')
    project_subparsers = project_parser.add_subparsers(dest='project_action', help='Project actions')

    # Create subcommand
    project_create_parser = project_subparsers.add_parser(
        'create', help='Create a new project'
    )
    project_create_parser.add_argument(
        'name', help='Project name (e.g., ib-stream, marketbridge)'
    )
    project_create_parser.add_argument(
        '--base-dir',
        help='Base directory for projects (default: from config)'
    )
    project_create_parser.add_argument(
        '--no-kanban', action='store_true',
        help='Do not copy kanban structure to project'
    )
    project_create_parser.add_argument(
        '--description',
        help='Project description'
    )
    project_create_parser.add_argument(
        '--git-url',
        help='Git repository URL'
    )
    project_create_parser.add_argument(
        '--maintainer', action='append', dest='maintainers',
        help='Project maintainer (can be used multiple times)'
    )
    project_create_parser.add_argument(
        '--create-repo', action='store_true',
        help='Create GitHub repository using gh CLI (requires --git-url or GitHub username)'
    )
    project_create_parser.add_argument(
        '--github-user',
        help='GitHub username for repository creation (defaults to current gh user)'
    )
    project_create_parser.add_argument(
        '--public', action='store_true',
        help='Create public repository (default unless --private specified)'
    )
    project_create_parser.add_argument(
        '--private', action='store_true',
        help='Create private repository'
    )
    project_create_parser.set_defaults(func=project_create_command)

    # List subcommand
    project_list_parser = project_subparsers.add_parser(
        'list', help='List existing projects'
    )
    project_list_parser.add_argument(
        '--base-dir',
        help='Base directory for projects (default: from config)'
    )
    project_list_parser.set_defaults(func=project_list_command)

    # Delete subcommand
    project_delete_parser = project_subparsers.add_parser(
        'delete', help='Delete a project'
    )
    project_delete_parser.add_argument(
        'name', help='Project name to delete'
    )
    project_delete_parser.add_argument(
        '--base-dir',
        help='Base directory for projects (default: from config)'
    )
    project_delete_parser.add_argument(
        '--force', '-f', action='store_true',
        help='Force delete without confirmation'
    )
    project_delete_parser.set_defaults(func=project_delete_command)

    # Set default routing function for project command
    project_parser.set_defaults(func=project_command)

    # Story management command
    story_parser = subparsers.add_parser(
        'story', help='Manage stories (create, delete, workspace)'
    )
    story_subparsers = story_parser.add_subparsers(
        dest='story_command', help='Story management commands'
    )

    # Story create subcommand
    story_create_parser = story_subparsers.add_parser(
        'create', help='Create a new story from template'
    )
    story_create_parser.add_argument(
        'description', help='Brief description of the story'
    )
    story_create_parser.add_argument(
        '--project', required=True,
        help='Project name to create story in'
    )
    story_create_parser.add_argument(
        '--story-id',
        help='Story ID (auto-generated if not provided)'
    )
    story_create_parser.add_argument(
        '--branch-from', default='main',
        help='Branch to branch from (default: main)'
    )
    story_create_parser.add_argument(
        '--merge-to', default='main',
        help='Branch to merge to (default: main)'
    )
    story_create_parser.add_argument(
        '--feature-suffix',
        help='Feature branch suffix (default: story-id only)'
    )
    story_create_parser.set_defaults(story_func=story_create_command)

    # Story delete subcommand
    story_delete_parser = story_subparsers.add_parser(
        'delete', help='Delete an existing story'
    )
    story_delete_parser.add_argument(
        'story_id', help='Story ID to delete (e.g., ibstr-1)'
    )
    story_delete_parser.add_argument(
        '--force', '-f', action='store_true',
        help='Force delete without confirmation'
    )
    story_delete_parser.set_defaults(story_func=story_delete_command)

    # Story workspace subcommand
    story_workspace_parser = story_subparsers.add_parser(
        'workspace', help='Create workspace for an existing story'
    )
    story_workspace_parser.add_argument(
        'story_name', help='Story name (e.g., ibstr-1, marke-2-refactor)'
    )
    story_workspace_parser.add_argument(
        '--template', default='default',
        help='Template to use (default: default)'
    )
    story_workspace_parser.add_argument(
        '--base-dir',
        help='Base directory for workspaces (default: from config)'
    )
    story_workspace_parser.add_argument(
        '--name',
        help='Custom suffix for workspace name (e.g., experiment, refactor, performance)'
    )
    story_workspace_parser.set_defaults(story_func=story_workspace_command)

    # Set default routing function for story command
    story_parser.set_defaults(func=story_command)

    # Claude command
    claude_parser = subparsers.add_parser(
        'claude', help='Start Claude session in workspace'
    )
    claude_parser.add_argument(
        'workspace', help='Workspace name (e.g., v3, dev, test)'
    )
    claude_parser.add_argument(
        '-r', '--resume', action='store_true',
        help='Resume previous Claude session'
    )
    claude_parser.set_defaults(func=claude_command)

    # Bash command
    bash_parser = subparsers.add_parser(
        'bash', help='Start bash shell in workspace'
    )
    bash_parser.add_argument(
        'workspace', help='Workspace name (e.g., v3, dev, test)'
    )
    bash_parser.add_argument(
        'command_args', nargs=argparse.REMAINDER, help='Additional arguments for bash'
    )
    bash_parser.set_defaults(func=bash_command)

    # Template command (original functionality)
    template_parser = subparsers.add_parser(
        'template', help='Render a Jinja2 template'
    )
    template_parser.add_argument(
        "template",
        help="Path to the template file to render"
    )
    template_parser.add_argument(
        "--var", "-v",
        action="append",
        default=[],
        help="Template variables in key=value format (can be used multiple times)"
    )
    template_parser.add_argument(
        "--env-file",
        help="Path to .env file for template variables (default: .env in current directory)"
    )
    template_parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to YAML config file for template variables (default: config.yaml)"
    )
    template_parser.set_defaults(func=template_command)

    args = parser.parse_args()

    # Handle case where no command is specified (backwards compatibility)
    if not hasattr(args, 'func'):
        if hasattr(args, 'template'):
            # Old-style direct template call
            template_command(args)
        else:
            parser.print_help()
            sys.exit(1)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
