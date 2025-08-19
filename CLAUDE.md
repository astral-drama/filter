# Claude Development Guide

This document provides examples and guidance for Claude to effectively work with the Filter workspace system.

## Development Standards and Patterns

### Logging and Auditing

The Filter project implements comprehensive logging and auditing for all operations. **Always follow these patterns:**

#### Command Execution

**✅ Use the command utilities:**
```python
from .command_utils import run_command, run_git_command, run_docker_command

# Git operations
result = run_git_command(
    ["worktree", "add", "-b", branch_name, str(path)],
    cwd=project_dir,
    check=False
)

# General commands
result = run_command(
    ["docker", "compose", "up", "-d"],
    cwd=workspace_dir,
    audit=True,
    sensitive=False
)
```

**❌ Never use raw subprocess:**
```python
# DON'T DO THIS
subprocess.run(["git", "status"], cwd=project_dir)  # No logging/auditing
```

#### Logging Patterns

**✅ Use structured logging with context:**
```python
from .logging_config import get_logger

logger = get_logger(__name__)

# Good logging with context
logger.info(f"Creating git worktree for workspace: {workspace_name}",
           extra={'workspace_name': workspace_name, 'worktree_path': str(path)})

# Error logging with structured data
logger.error(f"Failed to create worktree: {error}",
            extra={'workspace_name': workspace_name, 'error': str(error)})
```

**❌ Basic logging without context:**
```python
# DON'T DO THIS
logger.info("Creating worktree")  # No context
```

#### Error Handling

**✅ Use CommandResult pattern:**
```python
result = run_git_command(["status"], cwd=project_dir, check=False)

if result.success:
    logger.info(f"Command succeeded: {result.stdout}")
else:
    logger.warning(f"Command failed: {result.stderr}")
    # Handle error appropriately
```

**❌ Raw exception handling:**
```python
# DON'T DO THIS
try:
    subprocess.run(["git", "status"], check=True)
except subprocess.CalledProcessError as e:
    # No structured logging
```

### Code Organization

#### DRY Principles

**✅ Extract common patterns:**
```python
def _validate_git_repository(project_dir: Path) -> bool:
    """Reusable validation helper."""
    git_dir = project_dir / ".git"
    return git_dir.exists() and project_dir.is_dir()

# Use the helper consistently
if not _validate_git_repository(project_dir):
    raise RuntimeError(f"Invalid git repository: {project_dir}")
```

#### Function Structure

**✅ Follow this pattern:**
```python
def create_git_worktree(project_dir: Path, workspace_dir: Path, workspace_name: str) -> None:
    """Clear docstring with Args, Raises, etc."""
    
    # 1. Input validation
    if not _validate_git_repository(project_dir):
        raise RuntimeError(f"Invalid repository: {project_dir}")
    
    # 2. Log operation start with context
    logger.info(f"Creating git worktree: {workspace_name}",
               extra={'workspace_name': workspace_name, 'project_dir': str(project_dir)})
    
    # 3. Execute operations with proper error handling
    try:
        result = run_git_command(["worktree", "add", "-b", workspace_name, str(path)], 
                               cwd=project_dir, check=False)
        
        if result.success:
            logger.info(f"Successfully created worktree: {workspace_name}")
        else:
            raise RuntimeError(f"Worktree creation failed: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}", extra={'workspace_name': workspace_name})
        raise
```

### Import Patterns

**✅ Standard imports:**
```python
from .command_utils import run_command, run_git_command, CommandResult
from .logging_config import get_logger
from .config import get_workspaces_directory

logger = get_logger(__name__)  # Not logging.getLogger()
```

### Audit Requirements

**All sensitive operations must be audited:**
- File system operations (create, delete, move)
- Git operations (clone, commit, branch, worktree)
- Docker operations (build, run, stop)
- Configuration changes

**Audit logging is automatic** when using command utilities with `audit=True` (default).

### Error Message Standards

**✅ Descriptive error messages with context:**
```python
raise RuntimeError(f"Failed to create worktree '{workspace_name}' at {path}: {result.stderr}")
```

**❌ Generic error messages:**
```python
raise RuntimeError("Git command failed")  # Not helpful
```

### Testing Patterns

**✅ Test with proper cleanup:**
```python
def test_git_worktree_creation():
    # Test implementation
    # Always clean up test artifacts
    cleanup_git_worktree(test_workspace_dir, test_workspace_name)
```

---

## Quick Workspace Creation

To create a new Docker workspace for development, use the CLI command:

```bash
python -m filter.cli workspace create <name> [--template <template-name>]
```

### Template Selection

```bash
# List available templates
python -m filter.cli workspace create --list-templates

# Create with default template (full-stack: Postgres + Claude)
python -m filter.cli workspace create myproject

# Create with specific templates
python -m filter.cli workspace create frontend --template minimal  # Claude only
python -m filter.cli workspace create datalab --template python    # Python + Jupyter + Postgres
```

### Examples

```bash
# Full-stack development workspaces
python -m filter.cli workspace create v4                # Default template
python -m filter.cli workspace create api --template default

# Lightweight workspaces (no database)
python -m filter.cli workspace create ui --template minimal
python -m filter.cli workspace create frontend --template minimal

# Python/Data Science workspaces  
python -m filter.cli workspace create ml --template python
python -m filter.cli workspace create analytics --template python
python -m filter.cli workspace create jupyter --template python

# Project-specific workspaces
python -m filter.cli workspace create auth-feature
python -m filter.cli workspace create microservice --template minimal
```

## Workspace Structure

Each created workspace follows this structure:

```
workspaces/<name>/
├── Dockerfile              # Claude container with dev tools
├── docker-compose.yml      # Postgres + Claude services
└── workspace/
    ├── .env                # Database credentials
    └── kanban/             # Full kanban directory copy
        ├── planning/
        ├── in-progress/
        ├── testing/
        ├── pr/
        ├── complete/
        ├── prompts/
        └── stories/
```

## Template Types

### default Template (Full-stack)
- **Services**: PostgreSQL 17 + Claude development container
- **Use case**: General full-stack development with database needs
- **Tools**: Node.js, Python, claude-code, PostgreSQL client, development tools

### minimal Template (Lightweight)
- **Services**: Claude development container only
- **Use case**: Frontend work, simple development tasks, when database isn't needed
- **Tools**: Node.js, Python, claude-code, development tools (no PostgreSQL client)

### python Template (Data Science)
- **Services**: PostgreSQL 17 + Claude container + Jupyter notebook server
- **Use case**: Python development, data science, machine learning projects
- **Tools**: Enhanced Python toolchain, Jupyter, testing tools, database

> 📖 **Complete template specifications**: See [`docker/README.md`](docker/README.md) for detailed template documentation.

## Container Details

### Postgres Container (default, python templates)
- **Image**: postgres:17
- **Container name**: postgres (always the same)
- **Database**: claude / claude / claudepassword321
- **Port**: Auto-detected (starts from 5433)
- **Volume**: `postgres_<workspace>_data`

### Claude Container (all templates)
- **Base**: debian:bookworm-slim
- **Container name**: claude (always the same)
- **Port**: Auto-detected (starts from 8001)
- **Common tools**:
  - Node.js LTS + npm
  - Python 3 + pip + uv + ruff
  - claude-code CLI
  - tmux, nano, emacs
  - sudo (passwordless for claude user)
- **Template-specific tools**:
  - postgresql-client (default, python templates)
  - Enhanced Python tools (python template)

### Jupyter Container (python template only)
- **Port**: Auto-detected (starts from 8888)
- **Access**: Available at `http://localhost:<jupyter_port>`

### Mounts
- `../../home:/home/claude` - Shared home across all workspaces
- `./workspace:/workspace` - Version-specific workspace

## Starting and Using Workspaces

1. **Create workspace**:
   ```bash
   python -m filter.cli workspace create myproject
   ```

2. **Start services**:
   ```bash
   cd workspaces/myproject
   docker compose up -d
   ```

3. **Access container**:
   ```bash
   docker exec -it claude tmux new-session -s claude -c /workspace
   ```

   **Or use the helper commands**:
   ```bash
   filter bash myproject        # Interactive bash shell
   filter claude myproject      # Start Claude session
   ```

4. **Check services**:
   ```bash
   docker compose ps
   ```

## Environment Variables

Environment variables vary by template:

### default Template
```bash
DATABASE_URL=postgresql://claude:claudepassword321@postgres:5432/claude
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=claude
POSTGRES_PASSWORD=claudepassword321
POSTGRES_DB=claude
CLAUDE_HOST_PORT=8001      # Auto-detected
CLAUDE_INTERNAL_PORT=8000
POSTGRES_HOST_PORT=5433    # Auto-detected
```

### minimal Template
```bash
CLAUDE_HOST_PORT=8001      # Auto-detected
CLAUDE_INTERNAL_PORT=8000
```

### python Template
```bash
DATABASE_URL=postgresql://claude:claudepassword321@postgres:5432/claude
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=claude
POSTGRES_PASSWORD=claudepassword321
POSTGRES_DB=claude
CLAUDE_HOST_PORT=8001      # Auto-detected
CLAUDE_INTERNAL_PORT=8000
POSTGRES_HOST_PORT=5433    # Auto-detected
JUPYTER_PORT=8888          # Auto-detected
```

## Common Development Patterns

### Database Connection
```bash
# From within Claude container
psql $DATABASE_URL

# Or using individual vars
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB
```

### Port Information
The CLI automatically finds available ports and reports them:
```
INFO:filter.workspace:Using ports - Postgres: 5433, Claude: 8001
```

### Kanban Access
All kanban files are available in the container at `/workspace/kanban/`:
- `/workspace/kanban/prompts/` - LLM prompts
- `/workspace/kanban/stories/` - Story definitions
- `/workspace/kanban/planning/` - Planned work
- etc.

## Workspace Management

### List Running Services
```bash
docker compose ps
```

### Stop Workspace
```bash
python -m filter.cli workspace down <name>
# OR manually:
docker compose down
```

### Remove Workspace (keeps data)
```bash
python -m filter.cli workspace delete <name>
# OR manually:
docker compose down
rm -rf workspaces/<name>
```

### Remove Workspace + Data (force delete running workspace)
```bash
python -m filter.cli workspace delete <name> --force
# OR manually:
docker compose down -v  # Removes volumes too
rm -rf workspaces/<name>
```

### Multiple Workspaces
You can run multiple workspaces simultaneously since ports are auto-detected:
```bash
python -m filter.cli workspace create api --template default   # Gets ports 5433, 8001
python -m filter.cli workspace create ui --template minimal    # Gets port 8002  
python -m filter.cli workspace create ml --template python     # Gets ports 5434, 8003, 8888
```

## Troubleshooting

### Container Won't Start
- Check if ports are available: `netstat -tuln | grep <port>`
- Check Docker logs: `docker compose logs`
- Rebuild container: `docker compose build --no-cache`

### Port Conflicts
The CLI automatically finds available ports, but if you need specific ports, you can manually edit `docker-compose.yml`.

### Database Issues
- Check Postgres logs: `docker compose logs postgres`
- Reset database: `docker compose down -v && docker compose up -d postgres`

### Shared Home Directory
The `../../home` directory is shared across ALL workspaces. Use it for:
- SSH keys
- Git configuration
- Shared tools/scripts
- Claude Code settings

## Best Practices

1. **Use descriptive workspace names**: `auth-service`, `frontend-v2`, `migration-testing`
2. **One workspace per feature/project** for isolation
3. **Keep shared tools in `home/`** directory
4. **Use the kanban structure** in `/workspace/kanban/` for organization
5. **Clean up unused workspaces** to save disk space
6. **Check ports** with `docker compose ps` before creating new workspaces

## CLI Command Reference

```bash
# Workspace creation
python -m filter.cli workspace create --list-templates           # List available templates
python -m filter.cli workspace create <name>                     # Create with default template
python -m filter.cli workspace create <name> --template <type>   # Create with specific template
python -m filter.cli workspace create <name> --base-dir <dir>    # Custom base directory

# Workspace management
python -m filter.cli workspace down <name>                       # Stop workspace containers
python -m filter.cli workspace delete <name>                     # Delete stopped workspace
python -m filter.cli workspace delete <name> --force             # Force delete running workspace

# Project management
python -m filter.cli project create <name>                       # Create new project with kanban
python -m filter.cli project create <name> --description "desc"  # Create with description
python -m filter.cli project create <name> --git-url <url>       # Create with git URL
python -m filter.cli project create <name> --maintainer <email>  # Create with maintainer
python -m filter.cli project create <name> --no-kanban           # Create project without kanban
python -m filter.cli project list                                # List all projects
python -m filter.cli project delete <name>                       # Delete project
python -m filter.cli project delete <name> --force               # Force delete project

# Story workspaces
python -m filter.cli story <story-name>                          # Create workspace for story
python -m filter.cli story <story-name> --template <template>    # Create with specific template

# Workspace access helpers
filter bash <workspace-name>                              # Interactive bash shell
filter claude <workspace-name>                            # Start Claude session
filter claude <workspace-name> -r                         # Start Claude session with resume
filter bash <workspace-name> -c "command"                 # Run command and exit

# Template rendering (original functionality)
python -m filter.cli template <template> [--var key=val] [--config file] [--env-file file]

# Help
python -m filter.cli --help
python -m filter.cli workspace --help
python -m filter.cli workspace create --help
python -m filter.cli workspace down --help
python -m filter.cli workspace delete --help
python -m filter.cli project --help
python -m filter.cli project create --help
python -m filter.cli project list --help
python -m filter.cli project delete --help
python -m filter.cli bash --help
python -m filter.cli claude --help
python -m filter.cli template --help
```

## Project Management

The Filter system includes project management capabilities for organizing stories and kanban boards by project. This helps keep stories from different projects separate and organized.

### Project Structure

Each project follows this structure:

```
projects/<project-name>/
├── project.yaml           # Project configuration with prefix and metadata
└── kanban/
    ├── planning/
    ├── in-progress/
    ├── testing/
    ├── pr/
    ├── complete/
    ├── prompts/
    └── stories/
```

### Creating Projects

```bash
# Create a new project with kanban structure
python -m filter.cli project create ib-stream

# Create a project with metadata
python -m filter.cli project create marketbridge \
  --description "Multi-market trading bridge system" \
  --git-url "https://github.com/user/marketbridge.git" \
  --maintainer "developer@example.com" \
  --maintainer "lead@example.com"

# Create a project without kanban structure
python -m filter.cli project create simple-tool --no-kanban

# Create project in custom directory
python -m filter.cli project create analytics --base-dir /custom/projects
```

### Managing Projects

```bash
# List all projects
python -m filter.cli project list

# Delete a project
python -m filter.cli project delete old-project

# Force delete without confirmation
python -m filter.cli project delete old-project --force
```

### Project Configuration

Each project includes a `project.yaml` configuration file with:

```yaml
name: marketbridge
prefix: marke                                    # Auto-generated 5-char prefix
description: Multi-market trading bridge system
git_url: https://github.com/user/marketbridge.git
maintainers:
- developer@example.com
- lead@example.com
created_at: null
version: '1.0'
```

### Story Naming with Prefixes

The auto-generated prefix helps create consistent story and branch names:

- **Story examples**: `marke-1`, `marke-2-refactor`, `marke-15-auth-fix`  
- **Branch examples**: `marke-1`, `marke-2-refactor`, `marke-15-auth-fix`
- **Prefix generation**: `ib-stream` → `ibstr`, `marketbridge` → `marke`

### Example Workflow

1. **Create project**: `python -m filter.cli project create ib-stream`
2. **Note the prefix**: Project creates with prefix `ibstr` for story naming
3. **Organize stories**: Create stories like `ibstr-1.md`, `ibstr-2-optimization.md`
4. **Plan work**: Move stories from `stories/` to `planning/` 
5. **Track progress**: Move through `in-progress/` → `testing/` → `pr/` → `complete/`
6. **Branch naming**: Use same prefix for git branches: `ibstr-1`, `ibstr-2-optimization`

### Benefits

- **Story Organization**: Keep stories separated by project
- **Consistent Naming**: Auto-generated prefixes for stories and branches
- **Project Metadata**: Track descriptions, git URLs, and maintainers
- **Kanban Isolation**: Each project has its own kanban board
- **Flexible Structure**: Projects can exist with or without kanban
- **Easy Management**: Simple CLI commands for project lifecycle

## Story Workspaces

The Filter system can create dedicated workspaces for individual stories, providing an isolated development environment with project context.

### Creating Story Workspaces

```bash
# Create workspace for a story (searches all projects)
python -m filter.cli story ibstr-1

# Create with specific template
python -m filter.cli story marke-2-refactor --template python
```

### Story Workspace Features

When you create a story workspace:

1. **Automatic Discovery**: Finds the story across all projects
2. **Project Context**: Workspace is named after the story (e.g., `ibstr-1`)
3. **Kanban Mounting**: Project's kanban directory is mounted at `/workspace/kanban`
4. **Environment Variables**: Story context available in `.env`:
   ```bash
   PROJECT_NAME=ib-stream
   STORY_NAME=ibstr-1
   STORY_PATH=kanban/stories/ibstr-1.md
   ```

### Example Story Workspace

```bash
# Create story workspace
filter story ibstr-1

# Output shows project context
# Story workspace 'ibstr-1' created at: /path/to/workspaces/ibstr-1
# Project: ib-stream
# Story file: stories/ibstr-1.md

# Start the workspace
cd /path/to/workspaces/ibstr-1
docker compose up -d

# Access your story file
filter claude ibstr-1
# Story file available at: /workspace/kanban/stories/ibstr-1.md
```

### Benefits

- **Story-Focused Development**: Workspace named and configured for specific story
- **Project Context**: Full access to project's kanban structure
- **Environment Integration**: Story details available as environment variables
- **Consistent Naming**: Workspace name matches story name and git branch conventions

This workspace system provides isolated, reproducible development environments with automatic port management and full kanban integration.

---

> 📖 **Additional Resources:**
> - [`docker/README.md`](docker/README.md) - Complete template documentation and customization guide
> - [`README.md`](README.md) - Main project documentation and getting started guide