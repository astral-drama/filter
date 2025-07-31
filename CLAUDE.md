# Claude Development Guide

This document provides examples and guidance for Claude to effectively work with the Filter workspace system.

## Quick Workspace Creation

To create a new Docker workspace for development, use the CLI command:

```bash
python -m filter.cli workspace <name>
```

### Examples

```bash
# Create workspace for version 4
python -m filter.cli workspace v4

# Create development workspace
python -m filter.cli workspace dev

# Create testing workspace  
python -m filter.cli workspace test

# Create workspace for specific feature
python -m filter.cli workspace auth-feature
```

## Workspace Structure

Each created workspace follows this structure:

```
workspaces/<name>/
├── Dockerfile              # Claude container with dev tools
├── docker-compose.yml      # Postgres + Claude services
└── workspace/
    ├── .env                # Database credentials
    └── .kanban/            # Full kanban directory copy
        ├── planning/
        ├── in-progress/
        ├── testing/
        ├── pr/
        ├── complete/
        ├── prompts/
        └── stories/
```

## Container Details

### Postgres Container
- **Image**: postgres:17
- **Container name**: postgres (always the same)
- **Database**: claude / claude / claudepassword321
- **Port**: Auto-detected (starts from 5433)
- **Volume**: `postgres_<workspace>_data`

### Claude Container  
- **Base**: debian:bookworm-slim
- **Container name**: claude (always the same)
- **Port**: Auto-detected (starts from 8001)
- **Tools included**:
  - Node.js LTS + npm
  - Python 3 + pip + uv + ruff
  - claude-code CLI
  - tmux, nano, emacs
  - postgresql-client
  - sudo (passwordless for claude user)

### Mounts
- `../../home:/home/claude` - Shared home across all workspaces
- `./workspace:/workspace` - Version-specific workspace

## Starting and Using Workspaces

1. **Create workspace**:
   ```bash
   python -m filter.cli workspace myproject
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

4. **Check services**:
   ```bash
   docker compose ps
   ```

## Environment Variables

Each workspace includes these environment variables in `.env`:

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
All kanban files are available in the container at `/workspace/.kanban/`:
- `/workspace/.kanban/prompts/` - LLM prompts
- `/workspace/.kanban/stories/` - Story definitions
- `/workspace/.kanban/planning/` - Planned work
- etc.

## Workspace Management

### List Running Services
```bash
docker compose ps
```

### Stop Workspace
```bash
docker compose down
```

### Remove Workspace (keeps data)
```bash
docker compose down
rm -rf workspaces/<name>
```

### Remove Workspace + Data
```bash
docker compose down -v  # Removes volumes too
rm -rf workspaces/<name>
```

### Multiple Workspaces
You can run multiple workspaces simultaneously since ports are auto-detected:
```bash
python -m filter.cli workspace v1    # Gets ports 5433, 8001
python -m filter.cli workspace v2    # Gets ports 5434, 8002  
python -m filter.cli workspace v3    # Gets ports 5435, 8003
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
4. **Use the kanban structure** in `/workspace/.kanban/` for organization
5. **Clean up unused workspaces** to save disk space
6. **Check ports** with `docker compose ps` before creating new workspaces

## CLI Command Reference

```bash
# Create workspace
python -m filter.cli workspace <name> [--base-dir workspaces]

# Template rendering (original functionality)
python -m filter.cli template <template> [--var key=val] [--config file] [--env-file file]

# Help
python -m filter.cli --help
python -m filter.cli workspace --help
python -m filter.cli template --help
```

This workspace system provides isolated, reproducible development environments with automatic port management and full kanban integration.