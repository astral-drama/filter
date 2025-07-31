"""Command line interface for Filter."""

import argparse
import logging
import os
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dotenv import load_dotenv
import yaml

from .workspace import create_workspace, list_templates, render_template


def workspace_command(args):
    """Handle workspace creation command."""
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
        workspace_path = create_workspace(
            args.name, 
            Path(args.base_dir), 
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

    # Workspace command
    workspace_parser = subparsers.add_parser(
        'workspace', help='Create a new Docker workspace'
    )
    workspace_parser.add_argument(
        'name', nargs='?', help='Workspace name (e.g., v3, dev, test)'
    )
    workspace_parser.add_argument(
        '--template', '-t', default='default',
        help='Template to use (default: default)'
    )
    workspace_parser.add_argument(
        '--base-dir', default='workspaces',
        help='Base directory for workspaces (default: workspaces)'
    )
    workspace_parser.add_argument(
        '--list-templates', action='store_true',
        help='List available templates'
    )
    workspace_parser.set_defaults(func=workspace_command)

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