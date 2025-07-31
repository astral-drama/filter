"""Workspace generation utilities for Docker compose environments."""

import logging
import shutil
import socket
import subprocess
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

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
        template_dir: Directory containing templates (defaults to docker/templates)

    Returns:
        List of template metadata dictionaries
    """
    if template_dir is None:
        template_dir = Path("docker/templates")

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
    template_name: str = "default"
) -> Path:
    """Create a new Docker workspace using specified template.

    Args:
        workspace_name: Name of the workspace (e.g., 'v3', 'dev', 'test')
        base_dir: Base directory for workspaces (defaults to ./workspaces)
        template_name: Template to use (defaults to 'default')

    Returns:
        Path to created workspace directory

    Raises:
        FileExistsError: If workspace already exists
        RuntimeError: If unable to find available ports or template not found
    """
    if base_dir is None:
        base_dir = Path("workspaces")
    
    workspace_dir = base_dir / workspace_name
    
    if workspace_dir.exists():
        raise FileExistsError(
            f"Workspace {workspace_name} already exists at {workspace_dir}"
        )

    # Find template
    template_dir = Path("docker/templates") / template_name
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

    # Ensure shared home directory exists
    home_dir = base_dir.parent / "home"
    if not home_dir.exists():
        home_dir.mkdir(exist_ok=True)
        (home_dir / ".gitkeep").touch()
        logger.info(f"Created shared home directory: {home_dir}")
    
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
    kanban_src = Path("kanban")
    if kanban_src.exists():
        kanban_dest = workspace_subdir / ".kanban"
        shutil.copytree(kanban_src, kanban_dest)
        logger.info(f"Copied kanban directory to {kanban_dest}")
    else:
        logger.warning("kanban directory not found, skipping copy")
    
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

    docker_cmd.extend([container_name] + command)

    try:
        # Replace current process with docker exec
        return subprocess.run(docker_cmd).returncode
    except KeyboardInterrupt:
        return 130  # Standard exit code for Ctrl+C
    except Exception as e:
        raise RuntimeError(f"Failed to execute command: {e}") from e
