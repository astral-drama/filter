# Project Setup Prompt

You are setting up a new project or initializing development environment for **{{ project_name }}**.

## Project Details

- **Project Name**: {{ project_name }}
- **Project Path**: {{ project_path }}
- **Project Type**: {{ project_type | default("Web Application") }}
- **Technology Stack**: {{ tech_stack | default("To be determined") }}

## Setup Requirements

{{ setup_requirements | default("Standard development environment setup") }}

## Development Environment

- **Language**: {{ language | default("Auto-detect") }}
- **Framework**: {{ framework | default("Auto-detect") }}
- **Database**: {{ database | default("None specified") }}
- **Package Manager**: {{ package_manager | default("Auto-detect") }}

## Setup Tasks

1. **Environment Preparation**:
   - Verify required tools are installed
   - Set up package manager and dependencies
   - Configure development tools
   - Set up linting and formatting

2. **Project Structure**:
   - Create standard directory structure
   - Initialize configuration files
   - Set up build/deployment scripts
   - Create documentation templates

3. **Dependencies**:
   - Install core dependencies
   - Set up development dependencies
   - Configure testing framework
   - Set up CI/CD if required

4. **Configuration**:
   - Environment variables setup
   - Database configuration (if applicable)
   - Logging configuration
   - Security settings

## Quality Assurance

- **Testing**: {{ testing_framework | default("Choose appropriate framework") }}
- **Linting**: {{ linting_tools | default("Standard linting tools") }}
- **Formatting**: {{ formatting_tools | default("Standard formatting tools") }}
- **Documentation**: {{ documentation_format | default("Markdown") }}

## Deliverables

- [ ] Project structure created
- [ ] Dependencies installed
- [ ] Development environment configured
- [ ] Basic tests passing
- [ ] Documentation initialized
- [ ] README.md with setup instructions
- [ ] Development guidelines documented

## Additional Configuration

{{ additional_config | default("No additional configuration specified") }}

---

**Goal**: Create a solid foundation for {{ project_name }} development with all necessary tools and configurations in place.