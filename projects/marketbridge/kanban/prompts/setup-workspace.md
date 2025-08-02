# Setup Workspace Prompt

You are setting up a development workspace for the **{{ story_name }}** story.

## Workspace Configuration

- **Story**: {{ story_name }}
- **Repository**: {{ repository_url }}
- **Base Branch**: {{ base_branch | default("main") }}
- **Feature Branch**: {{ feature_branch }}
- **Workspace Directory**: {{ workspaces_directory }}/{{ workspace_name }}

## Task Description

Clone the specified repository and create a new feature branch for development work. This workspace will be mounted into a Docker container for isolated development.

## Setup Steps

1. **Clone Repository**:

   ```bash
   cd {{ workspaces_directory }}
   git clone {{ repository_url }} {{ workspace_name }}
   cd {{ workspace_name }}
   ```

2. **Verify Repository State**:

   ```bash
   git status
   git log --oneline -5
   git branch -a
   ```

3. **Create Feature Branch**:

   ```bash
   git checkout {{ base_branch }}
   git pull origin {{ base_branch }}
   git checkout -b {{ feature_branch }}
   git push -u origin {{ feature_branch }}
   ```

4. **Workspace Validation**:
   - Verify the feature branch was created successfully
   - Confirm workspace is ready for development
   - Check that all necessary files are present

## Environment Details

- **Workspaces Root**: {{ workspaces_directory }}
- **Workspace Name**: {{ workspace_name }}
- **Git Repository**: <{{ repository_url }}>
- **Author**: {{ git_author_name | default("LLM Developer") }} <{{ git_author_email | default("llm@example.com") }}>

## Git Configuration

Set up git configuration for this workspace:

```bash
git config user.name "{{ git_author_name | default("LLM Developer") }}"
git config user.email "{{ git_author_email | default("llm@example.com") }}"
```

## Verification Checklist

- [ ] Repository cloned successfully
- [ ] Base branch is up to date
- [ ] Feature branch created and pushed
- [ ] Git configuration set
- [ ] Workspace ready for development
- [ ] All project dependencies identified

## Next Steps

After workspace setup is complete:

1. Review project structure and dependencies
2. Run any necessary setup scripts (npm install, pip install, etc.)
3. Verify the development environment works
4. Begin implementing the story requirements

## Error Handling

If any step fails:

- Document the error and attempted solution
- Check network connectivity and repository permissions
- Verify the base branch exists
- Ensure the feature branch name doesn't already exist

---

**Note**: This workspace will be mounted into a Docker container for safe, isolated development work.