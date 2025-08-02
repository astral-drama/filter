"""Command line interface for Filter."""

import argparse
import logging
import os
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dotenv import load_dotenv
import yaml

from .workspace import (
    create_workspace, 
    list_templates, 
    render_template, 
    exec_workspace_command,
    stop_workspace,
    delete_workspace,
    create_story_workspace
)
from .projects import (
    create_project,
    list_projects,
    delete_project
)
from .config import get_workspaces_directory


def workspace_create_command(args):
    """Handle workspace create subcommand."""
    logging.basicConfig(level=logging.INFO)
    
    if args.list_templates:
        templates = list_templates()
        if not templates:
            print("No templates found in docker/templates/")
            return
            
        print("Available workspace templates:")
        for template in templates:
            print(f"  {template['name']}: {template.get('description', 'No description')}")
        return
    
    if not args.name:
        print("Error: workspace name is required", file=sys.stderr)
        sys.exit(1)
    
    try:
        base_dir = None
        if hasattr(args, 'base_dir') and args.base_dir:
            base_dir = Path(args.base_dir)
        workspace_path = create_workspace(
            args.name, 
            base_dir, 
            args.template
        )
        print(f"Workspace '{args.name}' created at: {workspace_path}")
        print(f"To start: cd {workspace_path} && docker compose up")
    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def workspace_down_command(args):
    """Handle workspace down subcommand."""
    logging.basicConfig(level=logging.INFO)
    
    try:
        base_dir = None
        if hasattr(args, 'base_dir') and args.base_dir:
            base_dir = Path(args.base_dir)
        stop_workspace(args.name, base_dir)
        print(f"Workspace '{args.name}' stopped successfully")
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def workspace_delete_command(args):
    """Handle workspace delete subcommand."""
    logging.basicConfig(level=logging.INFO)
    
    try:
        base_dir = None
        if hasattr(args, 'base_dir') and args.base_dir:
            base_dir = Path(args.base_dir)
        delete_workspace(args.name, base_dir, args.force)
        print(f"Workspace '{args.name}' deleted successfully")
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def story_workspace_command(args):
    """Handle story workspace creation."""
    logging.basicConfig(level=logging.INFO)
    
    try:
        base_dir = None
        if hasattr(args, 'base_dir') and args.base_dir:
            base_dir = Path(args.base_dir)
            
        workspace_path = create_story_workspace(
            args.story_name,
            base_dir,
            args.template
        )
        print(f"Story workspace '{args.story_name}' created at: {workspace_path}")
        print(f"To start: cd {workspace_path} && docker compose up")
        
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def workspace_command(args):
    """Handle workspace command routing."""
    # For backwards compatibility - if no subcommand specified, default to create
    if not hasattr(args, 'workspace_action') or args.workspace_action is None:
        # Check if this looks like old-style usage
        if hasattr(args, 'name') and args.name:
            workspace_create_command(args)
        else:
            print("Error: Please specify a workspace action: create, down, or delete", file=sys.stderr)
            print("Usage: workspace create <name>", file=sys.stderr)
            sys.exit(1)
    else:
        # Subcommand specified, call the appropriate function
        args.func(args)


def project_create_command(args):
    """Handle project create subcommand."""
    logging.basicConfig(level=logging.INFO)
    
    try:
        base_dir = None
        if hasattr(args, 'base_dir') and args.base_dir:
            base_dir = Path(args.base_dir)
        
        project_path = create_project(
            args.name,
            base_dir,
            copy_kanban=not args.no_kanban,
            description=getattr(args, 'description', '') or '',
            git_url=getattr(args, 'git_url', '') or '',
            maintainers=getattr(args, 'maintainers', None) or []
        )
        print(f"Project '{args.name}' created at: {project_path}")
        
        # Load and display the generated config
        from .projects import load_project_config, generate_project_prefix
        config = load_project_config(project_path)
        if config:
            prefix = config.get('prefix', generate_project_prefix(args.name))
            print(f"Story prefix: {prefix} (use for stories like {prefix}-1, {prefix}-2-refactor)")
        
        if not args.no_kanban:
            print(f"Kanban structure available at: {project_path / 'kanban'}")
        
        print(f"Project config: {project_path / 'project.yaml'}")
        
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def project_list_command(args):
    """Handle project list subcommand."""
    try:
        base_dir = None
        if hasattr(args, 'base_dir') and args.base_dir:
            base_dir = Path(args.base_dir)
            
        projects = list_projects(base_dir)
        if projects:
            print("Available projects:")
            for project in projects:
                print(f"  {project}")
        else:
            print("No projects found.")
            
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def project_delete_command(args):
    """Handle project delete subcommand."""
    logging.basicConfig(level=logging.INFO)
    
    try:
        base_dir = None
        if hasattr(args, 'base_dir') and args.base_dir:
            base_dir = Path(args.base_dir)
            
        delete_project(args.name, base_dir, args.force)
        print(f"Project '{args.name}' deleted successfully")
        
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def project_command(args):
    """Handle project command routing."""
    if not hasattr(args, 'project_action') or args.project_action is None:
        print("Error: Please specify a project action: create, list, or delete", file=sys.stderr)
        print("Usage: project create <name>", file=sys.stderr)
        sys.exit(1)
    else:
        # Subcommand specified, call the appropriate function
        args.func(args)


def claude_command(args):
    """Handle claude session command."""
    try:
        command = ["claude"]
        if hasattr(args, 'resume') and args.resume:
            command.append("-r")
        command.append("--dangerously-skip-permissions")
        
        exit_code = exec_workspace_command(args.workspace, command)
        sys.exit(exit_code)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def bash_command(args):
    """Handle bash shell command."""
    try:
        command = ["bash"]
        if hasattr(args, 'command_args') and args.command_args:
            command.extend(args.command_args)
        exit_code = exec_workspace_command(args.workspace, command)
        sys.exit(exit_code)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def template_command(args):
    """Handle template rendering command."""
    # Load template variables from multiple sources
    context = {}

    # 1. Load from YAML config file (lowest priority)
    if Path(args.config).exists():
        try:
            with open(args.config, 'r') as f:
                config_data = yaml.safe_load(f)
                if config_data:
                    context.update(config_data)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML config file {args.config}: {e}",
                  file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading config file {args.config}: {e}",
                  file=sys.stderr)
            sys.exit(1)

    # 2. Load from .env file (medium priority - overrides config)
    env_file = args.env_file or ".env"
    if Path(env_file).exists():
        load_dotenv(env_file)
        # Add all environment variables to context
        context.update(os.environ)
    elif args.env_file:
        # If specific .env file was requested but doesn't exist, error
        print(f"Error: .env file not found: {args.env_file}",
              file=sys.stderr)
        sys.exit(1)

    # 3. Parse command line template variables (highest priority)
    for var in args.var:
        if "=" not in var:
            print(f"Error: Invalid variable format '{var}'. "
                  "Use key=value format.", file=sys.stderr)
            sys.exit(1)
        key, value = var.split("=", 1)
        context[key] = value

    try:
        # Render template and output to stdout
        result = render_template(args.template, context)
        print(result, end="")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error rendering template: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Filter - LLM-Powered Kanban board CLI"
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Workspace command with subcommands
    workspace_parser = subparsers.add_parser(
        'workspace', help='Manage Docker workspaces'
    )
    workspace_subparsers = workspace_parser.add_subparsers(
        dest='workspace_action', help='Workspace actions'
    )
    
    # Create subcommand (default action)
    create_parser = workspace_subparsers.add_parser(
        'create', help='Create a new Docker workspace'
    )
    create_parser.add_argument(
        'name', help='Workspace name (e.g., v3, dev, test)'
    )
    create_parser.add_argument(
        '--template', '-t', default='default',
        help='Template to use (default: default)'
    )
    create_parser.add_argument(
        '--base-dir',
        help='Base directory for workspaces (default: from config)'
    )
    create_parser.add_argument(
        '--list-templates', action='store_true',
        help='List available templates'
    )
    create_parser.set_defaults(func=workspace_create_command)
    
    # Down subcommand
    down_parser = workspace_subparsers.add_parser(
        'down', help='Stop a running workspace'
    )
    down_parser.add_argument(
        'name', help='Workspace name to stop'
    )
    down_parser.add_argument(
        '--base-dir',
        help='Base directory for workspaces (default: from config)'
    )
    down_parser.set_defaults(func=workspace_down_command)
    
    # Delete subcommand
    delete_parser = workspace_subparsers.add_parser(
        'delete', help='Delete a workspace'
    )
    delete_parser.add_argument(
        'name', help='Workspace name to delete'
    )
    delete_parser.add_argument(
        '--base-dir',
        help='Base directory for workspaces (default: from config)'
    )
    delete_parser.add_argument(
        '--force', '-f', action='store_true',
        help='Force delete running workspace (stops it first)'
    )
    delete_parser.set_defaults(func=workspace_delete_command)
    
    # Set default routing function for workspace command
    workspace_parser.set_defaults(func=workspace_command)

    # Project command with subcommands
    project_parser = subparsers.add_parser('project', help='Manage projects')
    project_subparsers = project_parser.add_subparsers(dest='project_action', help='Project actions')
    
    # Create subcommand
    project_create_parser = project_subparsers.add_parser(
        'create', help='Create a new project'
    )
    project_create_parser.add_argument(
        'name', help='Project name (e.g., ib-stream, marketbridge)'
    )
    project_create_parser.add_argument(
        '--base-dir',
        help='Base directory for projects (default: from config)'
    )
    project_create_parser.add_argument(
        '--no-kanban', action='store_true',
        help='Do not copy kanban structure to project'
    )
    project_create_parser.add_argument(
        '--description', 
        help='Project description'
    )
    project_create_parser.add_argument(
        '--git-url',
        help='Git repository URL'
    )
    project_create_parser.add_argument(
        '--maintainer', action='append', dest='maintainers',
        help='Project maintainer (can be used multiple times)'
    )
    project_create_parser.set_defaults(func=project_create_command)
    
    # List subcommand
    project_list_parser = project_subparsers.add_parser(
        'list', help='List existing projects'
    )
    project_list_parser.add_argument(
        '--base-dir',
        help='Base directory for projects (default: from config)'
    )
    project_list_parser.set_defaults(func=project_list_command)
    
    # Delete subcommand
    project_delete_parser = project_subparsers.add_parser(
        'delete', help='Delete a project'
    )
    project_delete_parser.add_argument(
        'name', help='Project name to delete'
    )
    project_delete_parser.add_argument(
        '--base-dir',
        help='Base directory for projects (default: from config)'
    )
    project_delete_parser.add_argument(
        '--force', '-f', action='store_true',
        help='Force delete without confirmation'
    )
    project_delete_parser.set_defaults(func=project_delete_command)
    
    # Set default routing function for project command
    project_parser.set_defaults(func=project_command)

    # Story workspace command
    story_parser = subparsers.add_parser(
        'story', help='Create workspace for a story'
    )
    story_parser.add_argument(
        'story_name', help='Story name (e.g., ibstr-1, marke-2-refactor)'
    )
    story_parser.add_argument(
        '--template', default='default',
        help='Template to use (default: default)'
    )
    story_parser.add_argument(
        '--base-dir',
        help='Base directory for workspaces (default: from config)'
    )
    story_parser.set_defaults(func=story_workspace_command)

    # Claude command
    claude_parser = subparsers.add_parser(
        'claude', help='Start Claude session in workspace'
    )
    claude_parser.add_argument(
        'workspace', help='Workspace name (e.g., v3, dev, test)'
    )
    claude_parser.add_argument(
        '-r', '--resume', action='store_true',
        help='Resume previous Claude session'
    )
    claude_parser.set_defaults(func=claude_command)

    # Bash command
    bash_parser = subparsers.add_parser(
        'bash', help='Start bash shell in workspace'
    )
    bash_parser.add_argument(
        'workspace', help='Workspace name (e.g., v3, dev, test)'
    )
    bash_parser.add_argument(
        'command_args', nargs=argparse.REMAINDER, help='Additional arguments for bash'
    )
    bash_parser.set_defaults(func=bash_command)

    # Template command (original functionality)
    template_parser = subparsers.add_parser(
        'template', help='Render a Jinja2 template'
    )
    template_parser.add_argument(
        "template",
        help="Path to the template file to render"
    )
    template_parser.add_argument(
        "--var", "-v",
        action="append",
        default=[],
        help="Template variables in key=value format (can be used multiple times)"
    )
    template_parser.add_argument(
        "--env-file",
        help="Path to .env file for template variables (default: .env in current directory)"
    )
    template_parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to YAML config file for template variables (default: config.yaml)"
    )
    template_parser.set_defaults(func=template_command)

    args = parser.parse_args()

    # Handle case where no command is specified (backwards compatibility)
    if not hasattr(args, 'func'):
        if hasattr(args, 'template'):
            # Old-style direct template call
            template_command(args)
        else:
            parser.print_help()
            sys.exit(1)
    else:
        args.func(args)


if __name__ == "__main__":
    main()