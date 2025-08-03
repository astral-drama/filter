"""Workspace generation utilities for Docker compose environments."""

import logging
import shutil
import socket
import subprocess
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import get_workspaces_directory, get_templates_directory, get_kanban_directory

logger = logging.getLogger(__name__)


def render_template(template_path: str, context: dict = None) -> str:
    """Render a Jinja2 template with the given context.

    Args:
        template_path: Path to the template file
        context: Dictionary of variables to use in template rendering

    Returns:
        Rendered template content

    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    template_file = Path(template_path)

    if not template_file.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    # Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(template_file.parent),
        autoescape=select_autoescape(['html', 'xml'])
    )

    # Load and render template
    template = env.get_template(template_file.name)
    return template.render(context or {})


def find_available_port(start_port: int, max_attempts: int = 100) -> int:
    """Find the first available port starting from start_port.

    Args:
        start_port: Port number to start checking from
        max_attempts: Maximum number of ports to check

    Returns:
        First available port number

    Raises:
        RuntimeError: If no available port found within max_attempts
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    
    raise RuntimeError(
        f"No available port found in range "
        f"{start_port}-{start_port + max_attempts}"
    )


def list_templates(template_dir: Optional[Path] = None) -> List[Dict]:
    """List available workspace templates.

    Args:
        template_dir: Directory containing templates (defaults to configured templates directory)

    Returns:
        List of template metadata dictionaries
    """
    if template_dir is None:
        template_dir = get_templates_directory()

    templates = []
    if not template_dir.exists():
        logger.warning(f"Template directory not found: {template_dir}")
        return templates

    for template_path in template_dir.iterdir():
        if template_path.is_dir():
            metadata_file = template_path / "template.yaml"
            if metadata_file.exists():
                try:
                    with open(metadata_file) as f:
                        metadata = yaml.safe_load(f)
                        metadata["path"] = template_path
                        templates.append(metadata)
                except Exception as e:
                    logger.warning(f"Error reading template {template_path}: {e}")
            else:
                # Basic template without metadata
                templates.append({
                    "name": template_path.name,
                    "description": f"Template: {template_path.name}",
                    "path": template_path
                })

    return templates


def create_workspace(
    workspace_name: str,
    base_dir: Optional[Path] = None,
    template_name: str = "default",
    story_context: Optional[Dict[str, Any]] = None
) -> Path:
    """Create a new Docker workspace using specified template.

    Args:
        workspace_name: Name of the workspace (e.g., 'v3', 'dev', 'test')
        base_dir: Base directory for workspaces (defaults to configured workspaces directory)
        template_name: Template to use (defaults to 'default')
        story_context: Optional story context with project_name, story_name, story_path, kanban_directory

    Returns:
        Path to created workspace directory

    Raises:
        FileExistsError: If workspace already exists
        RuntimeError: If unable to find available ports or template not found
    """
    if base_dir is None:
        base_dir = get_workspaces_directory()
    
    workspace_dir = base_dir / workspace_name
    
    if workspace_dir.exists():
        raise FileExistsError(
            f"Workspace {workspace_name} already exists at {workspace_dir}"
        )

    # Find template
    template_dir = get_templates_directory() / template_name
    if not template_dir.exists():
        raise RuntimeError(f"Template '{template_name}' not found at {template_dir}")

    logger.info(f"Creating workspace: {workspace_name} using template: {template_name}")

    # Load template metadata
    template_metadata = {}
    metadata_file = template_dir / "template.yaml"
    if metadata_file.exists():
        with open(metadata_file) as f:
            template_metadata = yaml.safe_load(f)

    # Find available ports based on template requirements
    context = {"workspace_name": workspace_name}
    
    # Default port detection
    postgres_port = find_available_port(5433)
    claude_port = find_available_port(8001)
    
    context.update({
        "postgres_port": postgres_port,
        "claude_port": claude_port
    })
    
    # Add story context if provided
    if story_context:
        context.update(story_context)

    # Additional ports for specific templates
    if template_name == "python":
        jupyter_port = find_available_port(8888)
        context["jupyter_port"] = jupyter_port
        logger.info(
            f"Using ports - Postgres: {postgres_port}, Claude: {claude_port}, Jupyter: {jupyter_port}"
        )
    elif "postgres" in template_metadata.get("features", []):
        logger.info(
            f"Using ports - Postgres: {postgres_port}, Claude: {claude_port}"
        )
    else:
        logger.info(f"Using ports - Claude: {claude_port}")

    # Create directory structure
    workspace_dir.mkdir(parents=True, exist_ok=True)
    workspace_subdir = workspace_dir / "workspace"
    workspace_subdir.mkdir(exist_ok=True)

    # Note: No longer creating shared home directory - using direct mounts from host $HOME
    
    # Render template files
    template_files = ["Dockerfile.j2", "docker-compose.yml.j2", ".env.j2"]
    
    for template_file in template_files:
        template_path = template_dir / template_file
        if template_path.exists():
            try:
                rendered_content = render_template(str(template_path), context)
                
                # Determine output path
                output_name = template_file.replace(".j2", "")
                if output_name == ".env":
                    output_path = workspace_subdir / output_name
                else:
                    output_path = workspace_dir / output_name
                
                output_path.write_text(rendered_content)
                try:
                    relative_path = output_path.relative_to(Path.cwd())
                    logger.info(f"Created {relative_path}")
                except ValueError:
                    logger.info(f"Created {output_path}")
                
            except Exception as e:
                logger.error(f"Error rendering template {template_file}: {e}")
                raise RuntimeError(f"Failed to render template {template_file}: {e}")
        else:
            logger.warning(f"Template file not found: {template_path}")
    
    # Copy kanban directory if it exists
    kanban_src = get_kanban_directory()
    if kanban_src.exists():
        kanban_dest = workspace_subdir / "kanban"
        shutil.copytree(kanban_src, kanban_dest)
        logger.info(f"Copied kanban directory to {kanban_dest}")
    else:
        logger.warning(f"kanban directory not found at {kanban_src}, skipping copy")
    
    # Copy scripts directory and entrypoint script for Docker build context
    scripts_src = Path(__file__).parent.parent.parent / "scripts"
    entrypoint_src = template_dir / "entrypoint.sh"
    
    if scripts_src.exists():
        scripts_dst = workspace_dir / "scripts"
        shutil.copytree(scripts_src, scripts_dst, dirs_exist_ok=True)
        logger.info(f"Copied scripts directory to {scripts_dst}")
    
    if entrypoint_src.exists():
        entrypoint_dst = workspace_dir / "entrypoint.sh"
        shutil.copy2(entrypoint_src, entrypoint_dst)
        logger.info(f"Copied entrypoint script to {entrypoint_dst}")
    
    logger.info(f"Workspace {workspace_name} created successfully at {workspace_dir}")
    logger.info(f"Postgres will be available on port {postgres_port}")
    logger.info(f"Claude will be available on port {claude_port}")
    logger.info(f"To start: cd {workspace_dir} && docker compose up")
    
    return workspace_dir


def find_workspace_container(workspace_name: str, service: str = "claude") -> str:
    """Find the container name for a workspace service.
    
    Args:
        workspace_name: Name of the workspace
        service: Service name (claude, postgres)
        
    Returns:
        Container name
        
    Raises:
        RuntimeError: If container not found or not running
    """
    container_name = f"{service}_{workspace_name}"
    
    try:
        # Check if container exists and is running
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        if container_name in result.stdout:
            return container_name
        else:
            raise RuntimeError(f"Container '{container_name}' not found or not running")
            
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to check container status: {e}")


def exec_workspace_command(workspace_name: str, command: List[str], interactive: bool = None) -> int:
    """Execute a command in the workspace claude container.
    
    Args:
        workspace_name: Name of the workspace
        command: Command to execute as list of strings
        interactive: Whether to run in interactive mode (auto-detected if None)
        
    Returns:
        Exit code from the command
        
    Raises:
        RuntimeError: If workspace/container not found
    """
    container_name = find_workspace_container(workspace_name, "claude")

    docker_cmd = ["docker", "exec"]

    # Auto-detect interactive mode if not specified
    if interactive is None:
        import sys
        interactive = sys.stdin.isatty() and sys.stdout.isatty()

    if interactive:
        docker_cmd.extend(["-it"])

    # Set working directory to match Dockerfile WORKDIR
    docker_cmd.extend(["--workdir", "/workspace"])

    docker_cmd.extend([container_name] + command)

    try:
        # Replace current process with docker exec
        return subprocess.run(docker_cmd).returncode
    except KeyboardInterrupt:
        return 130  # Standard exit code for Ctrl+C
    except Exception as e:
        raise RuntimeError(f"Failed to execute command: {e}") from e


def stop_workspace(workspace_name: str, base_dir: Optional[Path] = None) -> None:
    """Stop a running workspace by bringing down its containers.
    
    Args:
        workspace_name: Name of the workspace to stop
        base_dir: Base directory for workspaces (defaults to configured workspaces directory)
        
    Raises:
        RuntimeError: If workspace doesn't exist or docker compose fails
    """
    if base_dir is None:
        base_dir = get_workspaces_directory()
    
    workspace_dir = base_dir / workspace_name
    
    if not workspace_dir.exists():
        raise RuntimeError(f"Workspace '{workspace_name}' not found at {workspace_dir}")
    
    compose_file = workspace_dir / "docker-compose.yml"
    if not compose_file.exists():
        raise RuntimeError(f"No docker-compose.yml found in {workspace_dir}")
    
    logger.info(f"Stopping workspace: {workspace_name}")
    
    try:
        result = subprocess.run(
            ["docker", "compose", "down"],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Workspace {workspace_name} stopped successfully")
        if result.stdout:
            logger.info(result.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to stop workspace {workspace_name}: {e.stderr}")


def delete_workspace(workspace_name: str, base_dir: Optional[Path] = None, force: bool = False) -> None:
    """Delete a workspace directory and optionally stop it first.
    
    Args:
        workspace_name: Name of the workspace to delete
        base_dir: Base directory for workspaces (defaults to configured workspaces directory)
        force: If True, stop the workspace first if it's running
        
    Raises:
        RuntimeError: If workspace doesn't exist or operations fail
    """
    if base_dir is None:
        base_dir = get_workspaces_directory()
    
    workspace_dir = base_dir / workspace_name
    
    if not workspace_dir.exists():
        raise RuntimeError(f"Workspace '{workspace_name}' not found at {workspace_dir}")
    
    # Check if workspace is running
    is_running = False
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "-q"],
            cwd=workspace_dir,
            capture_output=True,
            text=True
        )
        is_running = bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        # Ignore errors checking if running
        pass
    
    if is_running and not force:
        raise RuntimeError(
            f"Workspace '{workspace_name}' is currently running. "
            "Stop it first with 'workspace down' or use --force to stop and delete."
        )
    
    if is_running and force:
        logger.info(f"Force stopping workspace: {workspace_name}")
        try:
            stop_workspace(workspace_name, base_dir)
        except RuntimeError as e:
            logger.warning(f"Warning: Could not stop workspace cleanly: {e}")
    
    logger.info(f"Deleting workspace: {workspace_name}")
    
    try:
        shutil.rmtree(workspace_dir)
        logger.info(f"Workspace {workspace_name} deleted successfully from {workspace_dir}")
    except Exception as e:
        raise RuntimeError(f"Failed to delete workspace directory {workspace_dir}: {e}")


def clone_git_repository(workspace_dir: Path, git_url: str, branch_name: str) -> None:
    """Clone a git repository into the workspace directory.
    
    Args:
        workspace_dir: Path to the workspace directory
        git_url: Git repository URL to clone
        branch_name: Branch name to create and checkout (typically the story name)
        
    Raises:
        RuntimeError: If git operations fail
    """
    repo_dir = workspace_dir / "workspace" / "repo"
    
    try:
        # Clone the repository
        logger.info(f"Cloning repository {git_url} to {repo_dir}")
        subprocess.run(
            ["git", "clone", git_url, str(repo_dir)],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Create and checkout feature branch
        logger.info(f"Creating and checking out branch {branch_name}")
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True
        )
        
        logger.info(f"Repository cloned successfully to {repo_dir}")
        logger.info(f"Checked out feature branch: {branch_name}")
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Git operation failed: {e.stderr if e.stderr else str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Failed to clone repository: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def create_story_workspace(
    story_name: str,
    base_dir: Optional[Path] = None,
    template_name: str = "default"
) -> Path:
    """Create a workspace for a specific story.
    
    Args:
        story_name: Story name (e.g., 'ibstr-1', 'marke-2-refactor')
        base_dir: Base directory for workspaces (defaults to configured workspaces directory)
        template_name: Template to use (defaults to 'default')
        
    Returns:
        Path to the created workspace directory
        
    Raises:
        RuntimeError: If story not found or workspace creation fails
    """
    from .projects import find_story_in_projects, load_project_config
    
    # Find the story across all projects
    story_info = find_story_in_projects(story_name)
    if not story_info:
        raise RuntimeError(f"Story '{story_name}' not found in any project")
    
    project_name = story_info['project_name']
    project_dir = story_info['project_dir']
    kanban_dir = story_info['kanban_dir']
    story_path = story_info['story_path']
    
    logger.info(f"Found story '{story_name}' in project '{project_name}'")
    logger.info(f"Story file: {story_path}")
    
    # Load project configuration to get git URL
    project_config = load_project_config(project_dir)
    git_url = project_config.get('git_url', '') if project_config else ''
    
    # Create story context for the workspace
    story_context = {
        'project_name': project_name,
        'story_name': story_name,
        'story_path': story_path,
        'kanban_directory': str(kanban_dir)
    }
    
    # Use the existing create_workspace function with story context
    workspace_dir = create_workspace(
        workspace_name=story_name,
        base_dir=base_dir,
        template_name=template_name,
        story_context=story_context
    )
    
    # Clone git repository if URL is available
    if git_url:
        clone_git_repository(workspace_dir, git_url, story_name)
    else:
        logger.warning(f"No git URL found in project config for {project_name}")
    
    logger.info(f"Project: {project_name}")
    logger.info(f"Story file: {story_path}")
    logger.info(f"Kanban directory will be mounted from: {kanban_dir}")
    
    return workspace_dir
