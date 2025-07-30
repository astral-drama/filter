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

## Getting Started

1. Create your story directories:
   ```bash
   mkdir -p planning in-progress testing pr complete prompts stories workspaces
   ```

2. Create a new story with git repository details:
   ```bash
   cat > stories/feature-name.md << EOF
   # Story Title
   
   Description of the feature...
   
   ## Git Configuration
   - **Repository**: https://github.com/user/repo.git
   - **Branch From**: main
   - **Merge To**: main
   - **Feature Branch**: feature/story-name
   EOF
   ```

3. Create corresponding prompt:
   ```bash
   echo "Instructions for LLM to complete this task..." > prompts/feature-name.md
   ```

4. Link story to planning:
   ```bash
   ln -s ../stories/feature-name.md planning/
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