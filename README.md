# LLM-Powered Kanban Board

A file-system based Kanban board that uses directories, Markdown files, and symbolic links to track development stories, with integrated LLM automation for task completion in sandboxed Docker containers.

## Overview

This project creates a unique Kanban workflow where:
- Stories are represented as `.md` files that can reference external git repositories
- Board columns are directories (planning, in-progress, testing, pr, complete)
- Stories move between columns using symbolic links
- Each story links to a prompt file that guides LLM task execution
- Stories specify source repositories, branch instructions, and merge targets
- Git repositories are checked out in the `workspaces/` directory
- Each workspace is mounted into a sandboxed Docker container
- LLMs complete development tasks in isolation without permission restrictions

## Project Structure

```
.
├── planning/           # Stories ready for development
├── in-progress/        # Stories currently being worked on
├── testing/           # Stories in testing phase
├── pr/                # Stories ready for pull request
├── complete/          # Completed stories
├── prompts/           # LLM prompt files for each story
├── stories/           # Master directory containing all story files
└── workspaces/        # Git repositories checked out for each story
```

## Workflow

1. **Story Creation**: Create a new story `.md` file in `stories/` with git repository details
2. **Prompt Linking**: Link the story to a corresponding prompt file in `prompts/`
3. **Planning**: Symlink the story to `planning/` directory
4. **Development**: 
   - Move story to `in-progress/`
   - Clone/checkout specified repository and branch in `workspaces/`
   - Mount workspace into Docker container
   - LLM processes the linked prompt and implements the feature in the sandboxed environment
5. **Testing**: Move story to `testing/` after development completion
6. **Pull Request**: Move story to `pr/` when ready for code review
7. **Completion**: Merge to target branch as specified in story and move to `complete/`

## Key Features

- **File-system based**: No database required, uses standard file operations
- **Multi-Repository Support**: Stories can reference any git repository and branch
- **LLM Integration**: Automated task completion using linked prompts
- **Docker Sandboxing**: Each workspace is mounted into an isolated container environment
- **Permission-free Development**: LLMs can work without asking for file system permissions
- **Workspace Management**: Git repositories are checked out in dedicated workspace directories
- **Flexible Branching**: Stories specify source branch, feature branch, and merge target
- **Pull Request Integration**: Dedicated PR column for code review workflow
- **Flexible Movement**: Easy story progression using symbolic links
- **Prompt-Driven Development**: Each story has associated LLM instructions

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd filter
   ```

2. Install the package:
   ```bash
   pip install -e .
   ```

## CLI Usage

The Filter CLI provides commands for template rendering and Docker workspace management.

### Workspace Management

Create isolated Docker environments for development with automatic port detection and multiple template options:

```bash
# List available templates
python -m filter.cli workspace --list-templates

# Create workspace with default template (full-stack)
python -m filter.cli workspace <name>

# Create workspace with specific template
python -m filter.cli workspace <name> --template <template-name>

# Examples
python -m filter.cli workspace dev                    # Default: Postgres + Claude
python -m filter.cli workspace frontend --template minimal  # Claude only
python -m filter.cli workspace ml --template python         # Python + Jupyter + Postgres
```

#### Available Templates

- **default**: Full-stack development environment with PostgreSQL 17 and Claude container
- **minimal**: Lightweight environment with just Claude container (no database)
- **python**: Python-focused environment with PostgreSQL, Claude, and Jupyter notebook server

> 📖 **Detailed template documentation**: See [`docker/README.md`](docker/README.md) for complete template specifications, customization options, and creating custom templates.

Each workspace includes:
- **Auto-detected ports** to avoid conflicts between multiple workspaces
- **Claude container** with development tools (claude-code, Python, Node.js)
- **Shared home directory** (`../../home`) mounted across all workspaces
- **Version-specific workspace** (`./workspace`) for project files
- **Kanban integration** (copies `kanban/` to `workspace/.kanban/`)
- **Environment configuration** (`.env` file with service credentials)

Workspace structure:
```
workspaces/<name>/
├── Dockerfile              # Claude container definition
├── docker-compose.yml      # Service orchestration
└── workspace/
    ├── .env                # Database connection details
    └── .kanban/            # Copy of kanban directory
```

To start a workspace:
```bash
cd workspaces/<name>
docker compose up -d
```

Access the Claude container:
```bash
docker exec -it claude tmux new-session -s claude -c /workspace
```

### Template Rendering

Render Jinja2 templates with variable substitution from multiple sources:

```bash
# Basic template rendering
python -m filter.cli template path/to/template.j2

# With variables
python -m filter.cli template template.j2 --var key1=value1 --var key2=value2

# With config file
python -m filter.cli template template.j2 --config myconfig.yaml

# With environment file
python -m filter.cli template template.j2 --env-file .env.production
```

Variable precedence (highest to lowest):
1. Command line variables (`--var`)
2. Environment file (`.env`)
3. YAML config file (`config.yaml`)

### Options

**Workspace Command:**
- `name`: Workspace name (required)
- `--template, -t`: Template to use (default: `default`)
- `--base-dir`: Base directory for workspaces (default: `workspaces`)
- `--list-templates`: List available templates

**Template Command:**
- `template`: Path to template file (required)
- `--var, -v`: Template variables in `key=value` format (repeatable)
- `--env-file`: Path to `.env` file for variables
- `--config`: Path to YAML config file (default: `config.yaml`)

## Getting Started

1. Create your story directories:
   ```bash
   mkdir -p kanban/{planning,in-progress,testing,pr,complete,prompts,stories}
   ```

2. Create a workspace for development:
   ```bash
   python -m filter.cli workspace dev
   cd workspaces/dev
   docker compose up -d
   ```

3. Create a new story with git repository details:
   ```bash
   cat > kanban/stories/feature-name.md << EOF
   # Story Title
   
   Description of the feature...
   
   ## Git Configuration
   - **Repository**: https://github.com/user/repo.git
   - **Branch From**: main
   - **Merge To**: main
   - **Feature Branch**: feature/story-name
   EOF
   ```

4. Create corresponding prompt:
   ```bash
   echo "Instructions for LLM to complete this task..." > kanban/prompts/feature-name.md
   ```

5. Link story to planning:
   ```bash
   ln -s ../stories/feature-name.md kanban/planning/
   ```

## Benefits

- **Visual Progress Tracking**: Clear view of story status across directories
- **Multi-Project Support**: Work with any git repository from a single Kanban board
- **Automated Development**: LLMs handle implementation details across different codebases
- **Secure Sandbox Environment**: Docker containers prevent system-wide changes
- **Permission-free Workflow**: LLMs can execute tasks without manual approval
- **Workspace Isolation**: Each story works in its own dedicated git workspace
- **Flexible Git Operations**: Define custom branching and merging strategies per story
- **Code Review Integration**: Built-in PR workflow for team collaboration
- **Prompt Reusability**: Standardized prompts for similar story types
- **Simple File Operations**: Move stories with standard file system commands

This approach combines the simplicity of file-based organization with the power of AI-assisted development, multi-repository support, and the security of containerized execution, creating a comprehensive, automated, and safe development workflow that scales across multiple projects.