# Add New Feature Prompt

You are working on the **{{ project_name }}** project located at `{{ project_path }}`.

## Task Description

Implement a new feature as described in the story requirements. Follow these steps:

1. **Analysis**: Review the existing codebase structure and identify where the new feature should be integrated
2. **Implementation**: Write clean, well-documented code that follows the project's existing patterns
3. **Testing**: Add appropriate tests for the new functionality
4. **Documentation**: Update relevant documentation if needed

## Project Context

- **Project Name**: {{ project_name }}
- **Project Path**: {{ project_path }}
- **Branch**: {{ branch_name | default("main") }}
- **Language/Framework**: {{ tech_stack | default("Unknown") }}

## Requirements

{{ feature_requirements | default("Please refer to the story description for detailed requirements.") }}

## Implementation Guidelines

- Follow the existing code style and conventions
- Add comprehensive logging for debugging
- Include error handling with descriptive messages
- Write unit tests with good coverage
- Update documentation as needed

## Deliverables

- [ ] Feature implementation
- [ ] Unit tests
- [ ] Integration tests (if applicable)
- [ ] Documentation updates
- [ ] Code review ready

---

**Note**: Work in the sandboxed environment. All changes will be contained within the Docker container until ready for review.
