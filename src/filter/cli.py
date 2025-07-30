"""Command line interface for Filter."""

import argparse
import os
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dotenv import load_dotenv


def render_template(template_path: str, context: dict = None) -> str:
    """Render a Jinja2 template with the given context.
    
    Args:
        template_path: Path to the template file
        context: Dictionary of variables to use in template rendering
        
    Returns:
        Rendered template content
        
    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    template_file = Path(template_path)
    
    if not template_file.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    
    # Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(template_file.parent),
        autoescape=select_autoescape(['html', 'xml'])
    )
    
    # Load and render template
    template = env.get_template(template_file.name)
    return template.render(context or {})


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Filter - LLM-Powered Kanban board CLI"
    )
    
    parser.add_argument(
        "template",
        help="Path to the template file to render"
    )
    
    parser.add_argument(
        "--var", "-v",
        action="append",
        default=[],
        help="Template variables in key=value format (can be used multiple times)"
    )
    
    parser.add_argument(
        "--env-file",
        help="Path to .env file for template variables (default: .env in current directory)"
    )
    
    args = parser.parse_args()
    
    # Load environment variables from .env file
    context = {}
    
    # Try to load from .env file
    env_file = args.env_file or ".env"
    if Path(env_file).exists():
        load_dotenv(env_file)
        # Add all environment variables to context
        context.update(os.environ)
    elif args.env_file:
        # If specific .env file was requested but doesn't exist, error
        print(f"Error: .env file not found: {args.env_file}", file=sys.stderr)
        sys.exit(1)
    
    # Parse command line template variables (these override .env variables)
    for var in args.var:
        if "=" not in var:
            print(f"Error: Invalid variable format '{var}'. Use key=value format.", file=sys.stderr)
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


if __name__ == "__main__":
    main()