# Claude Development Guide

This document provides examples and guidance for Claude to effectively work with the Filter workspace system.

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

# Workspace access helpers
filter bash <workspace-name>                              # Interactive bash shell
filter claude <workspace-name>                            # Start Claude session
filter bash <workspace-name> -c "command"                 # Run command and exit

# Template rendering (original functionality)
python -m filter.cli template <template> [--var key=val] [--config file] [--env-file file]

# Help
python -m filter.cli --help
python -m filter.cli workspace --help
python -m filter.cli workspace create --help
python -m filter.cli workspace down --help
python -m filter.cli workspace delete --help
python -m filter.cli bash --help
python -m filter.cli claude --help
python -m filter.cli template --help
```

This workspace system provides isolated, reproducible development environments with automatic port management and full kanban integration.

---

> 📖 **Additional Resources:**
> - [`docker/README.md`](docker/README.md) - Complete template documentation and customization guide
> - [`README.md`](README.md) - Main project documentation and getting started guide