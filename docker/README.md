# Docker Templates

This directory contains Docker Compose templates for different types of development workspaces.

## Available Templates

### default
**Full-stack development environment with Postgres and Claude**

- **Services**: PostgreSQL 17 + Claude development container
- **Features**: Database, claude-code, Python, Node.js, development tools
- **Ports**: Auto-detected (Postgres 5433+, Claude 8001+)
- **Use case**: General full-stack development with database needs

### minimal
**Lightweight development environment with just Claude container**

- **Services**: Claude development container only
- **Features**: claude-code, Python, Node.js, development tools
- **Ports**: Auto-detected (Claude 8001+)
- **Use case**: Simple development tasks, frontend work, or when database isn't needed

### python
**Python-focused development environment with Postgres and Jupyter**

- **Services**: PostgreSQL 17 + Claude container + Jupyter notebook server
- **Features**: Database, claude-code, Python with enhanced toolchain, Jupyter, testing tools
- **Ports**: Auto-detected (Postgres 5433+, Claude 8001+, Jupyter 8888+)
- **Use case**: Data science, Python development, machine learning projects

## Template Structure

Each template directory contains:

```
template-name/
├── template.yaml          # Template metadata
├── Dockerfile.j2          # Jinja2 template for Docker container
├── docker-compose.yml.j2  # Jinja2 template for services
└── .env.j2                # Jinja2 template for environment variables
```

## Usage

```bash
# List available templates
python -m filter.cli workspace --list-templates

# Create workspace with default template
python -m filter.cli workspace myproject

# Create workspace with specific template
python -m filter.cli workspace myproject --template python

# Create minimal workspace
python -m filter.cli workspace frontend --template minimal
```

## Template Variables

Templates have access to these Jinja2 variables:

- `workspace_name`: Name of the workspace
- `postgres_port`: Auto-detected PostgreSQL port
- `claude_port`: Auto-detected Claude container port
- `jupyter_port`: Auto-detected Jupyter port (python template only)

## Creating Custom Templates

1. Create a new directory in `docker/templates/`
2. Add required template files (`.j2` extensions)
3. Optionally add `template.yaml` for metadata:

```yaml
name: my-template
description: My custom development environment
author: Your Name
version: 1.0.0

services:
  - name: service-name
    description: Service description
    port_range: 8000-8100

features:
  - feature1
  - feature2

files:
  - Dockerfile.j2
  - docker-compose.yml.j2
  - .env.j2
```

4. Test your template:
```bash
python -m filter.cli workspace test --template my-template
```

## Template Features

### Common Container Features
- **Debian bookworm-slim** base image
- **claude user** with sudo access
- **Shared home directory** (`../../home`) mounted across all workspaces
- **Version-specific workspace** (`./workspace`) for project files
- **Kanban integration** (`.kanban/` directory copied automatically)
- **Auto-port detection** to avoid conflicts

### Database Support (default, python templates)
- **PostgreSQL 17** with consistent credentials
- **Environment variables** for easy connection
- **Persistent volumes** for data retention

### Development Tools
- **Claude Code CLI** for AI assistance
- **Python 3.11** with venv support
- **uv** and **ruff** for Python package/linting management
- **Node.js LTS** with npm
- **tmux, nano, emacs** for terminal work
- **Git** and build tools

### Python Template Extras
- **Enhanced Python toolchain** (black, pytest, mypy, ipython)
- **Jupyter notebook server** on dedicated port
- **Testing and development utilities**

## Port Management

Templates automatically detect available ports starting from:
- **PostgreSQL**: 5433
- **Claude**: 8001  
- **Jupyter**: 8888

Each workspace gets unique ports to avoid conflicts when running multiple environments simultaneously.

---

> 📖 **See Also:**
> - [`../README.md`](../README.md) - Main project documentation and getting started guide  
> - [`../CLAUDE.md`](../CLAUDE.md) - Detailed guide for Claude AI sessions with examples and troubleshooting