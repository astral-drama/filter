# LLM-Powered Kanban Board

A file-system based Kanban board that uses directories, Markdown files, and symbolic links to track development stories, with integrated LLM automation for task completion in sandboxed Docker containers.

## Overview

This project creates a unique Kanban workflow where:
- Stories are represented as `.md` files
- Board columns are directories (planning, in-progress, testing, complete)
- Stories move between columns using symbolic links
- Each story links to a prompt file that guides LLM task execution
- Feature branches are automatically created for each story
- Each branch is checked out in a sandboxed Docker container
- LLMs complete development tasks in isolation without permission restrictions

## Project Structure

```
.
├── planning/           # Stories ready for development
├── in-progress/        # Stories currently being worked on
├── testing/           # Stories in testing phase
├── complete/          # Completed stories
├── prompts/           # LLM prompt files for each story
└── stories/           # Master directory containing all story files
```

## Workflow

1. **Story Creation**: Create a new story `.md` file in `stories/`
2. **Prompt Linking**: Link the story to a corresponding prompt file in `prompts/`
3. **Planning**: Symlink the story to `planning/` directory
4. **Development**: 
   - Move story to `in-progress/`
   - Create feature branch for the story
   - Spin up Docker container with the feature branch checked out
   - LLM processes the linked prompt and implements the feature in the sandboxed environment
5. **Testing**: Move story to `testing/` after development completion
6. **Completion**: Merge feature branch and move story to `complete/`

## Key Features

- **File-system based**: No database required, uses standard file operations
- **LLM Integration**: Automated task completion using linked prompts
- **Docker Sandboxing**: Each feature branch runs in an isolated container environment
- **Permission-free Development**: LLMs can work without asking for file system permissions
- **Git Integration**: Automatic feature branch creation and management
- **Flexible Movement**: Easy story progression using symbolic links
- **Prompt-Driven Development**: Each story has associated LLM instructions

## Getting Started

1. Create your story directories:
   ```bash
   mkdir -p planning in-progress testing complete prompts stories
   ```

2. Create a new story:
   ```bash
   echo "# Story Title\n\nDescription of the feature..." > stories/feature-name.md
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
- **Automated Development**: LLMs handle implementation details
- **Secure Sandbox Environment**: Docker containers prevent system-wide changes
- **Permission-free Workflow**: LLMs can execute tasks without manual approval
- **Branch Management**: Automatic feature branch creation and cleanup
- **Prompt Reusability**: Standardized prompts for similar story types
- **Simple File Operations**: Move stories with standard file system commands

This approach combines the simplicity of file-based organization with the power of AI-assisted development and the security of containerized execution, creating an efficient, automated, and safe development workflow.