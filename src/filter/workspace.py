"""Workspace generation utilities for Docker compose environments."""

import logging
import shutil
import socket
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


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


def create_workspace(
    workspace_name: str, base_dir: Optional[Path] = None
) -> Path:
    """Create a new Docker workspace with postgres and claude containers.

    Args:
        workspace_name: Name of the workspace (e.g., 'v3', 'dev', 'test')
        base_dir: Base directory for workspaces (defaults to ./workspaces)

    Returns:
        Path to created workspace directory

    Raises:
        FileExistsError: If workspace already exists
        RuntimeError: If unable to find available ports
    """
    if base_dir is None:
        base_dir = Path("workspaces")
    
    workspace_dir = base_dir / workspace_name
    
    if workspace_dir.exists():
        raise FileExistsError(
            f"Workspace {workspace_name} already exists at {workspace_dir}"
        )

    logger.info(f"Creating workspace: {workspace_name}")

    # Find available ports
    postgres_port = find_available_port(5433)
    claude_port = find_available_port(8001)

    logger.info(
        f"Using ports - Postgres: {postgres_port}, Claude: {claude_port}"
    )

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
    
    # Create Dockerfile
    dockerfile_content = """FROM debian:bookworm-slim

# Install basic packages
RUN apt-get update && apt-get install -y \\
    curl \\
    ca-certificates \\
    tmux \\
    nano \\
    emacs \\
    python3 \\
    python3.11-venv \\
    python3-pip \\
    postgresql-client \\
    sudo \\
    gnupg \\
    lsb-release \\
    && rm -rf /var/lib/apt/lists/*

# Install Node.js LTS via NodeSource repository
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \\
    && apt-get install -y nodejs

# Install claude code
RUN npm install -g @anthropic-ai/claude-code

# Install Python tools
RUN pip3 install --break-system-packages uv ruff

# Create claude user with home directory
RUN useradd -m -s /bin/bash claude

# Add claude user to sudo group with NOPASSWD access
RUN echo 'claude ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Create workspace directory owned by claude
RUN mkdir -p /workspace && chown claude:claude /workspace

# Switch to claude user
USER claude

# Set working directory
WORKDIR /workspace

# Keep container running
CMD ["tail", "-f", "/dev/null"]"""
    
    (workspace_dir / "Dockerfile").write_text(dockerfile_content)
    
    # Create docker-compose.yml
    compose_content = f"""services:
  postgres:
    image: postgres:17
    container_name: postgres
    environment:
      POSTGRES_USER: claude
      POSTGRES_PASSWORD: claudepassword321
      POSTGRES_DB: claude
    ports:
      - "{postgres_port}:5432"
    volumes:
      - postgres_{workspace_name}_data:/var/lib/postgresql/data
    restart: unless-stopped

  claude:
    build: .
    container_name: claude
    depends_on:
      - postgres
    ports:
      - "{claude_port}:8000"
    volumes:
      - ../../home:/home/claude
      - ./workspace:/workspace
    environment:
      - DATABASE_URL=postgresql://claude:claudepassword321@postgres:5432/claude
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_USER=claude
      - POSTGRES_PASSWORD=claudepassword321
      - POSTGRES_DB=claude
      - CLAUDE_HOST_PORT={claude_port}
      - CLAUDE_INTERNAL_PORT=8000
      - POSTGRES_HOST_PORT={postgres_port}
    restart: unless-stopped
    tty: true
    stdin_open: true

volumes:
  postgres_{workspace_name}_data:"""
    
    (workspace_dir / "docker-compose.yml").write_text(compose_content)
    
    # Create .env file
    env_content = f"""DATABASE_URL=postgresql://claude:claudepassword321@postgres:5432/claude
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=claude
POSTGRES_PASSWORD=claudepassword321
POSTGRES_DB=claude
CLAUDE_HOST_PORT={claude_port}
CLAUDE_INTERNAL_PORT=8000
POSTGRES_HOST_PORT={postgres_port}"""
    
    (workspace_subdir / ".env").write_text(env_content)
    
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