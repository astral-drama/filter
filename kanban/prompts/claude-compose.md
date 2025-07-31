Create a docker compose file that includes:

**Postgres Setup:**

- Postgres container named "postgres" (always use this exact name)
- Username: claude, Password: claudepassword321, Database: claude
- Check for available host port above 5432 and bind postgres to it

**Claude Container Setup:**

- Container named "claude" (always use this exact name) built from debian:bookworm-slim
- Install: curl, ca-certificates, tmux, nano, emacs, python3, python3.11-venv, python3-pip, postgresql-client, sudo
- Install Node.js LTS and npm via NodeSource repository
- Install claude code: `npm install -g @anthropic-ai/claude-code`
- Install Python tools: `pip3 install --break-system-packages uv ruff`
- Create user "claude" with home directory
- Add claude user to sudo group with NOPASSWD access: `echo 'claude ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers`
- Create directory /workspace owned by claude:claude

**Directory Structure:**

- Create directories: workspace/
- Check if ../../home exists, if not create it (shared across all versions)
- Mount ../../home to /home/claude (shared home directory)
- Mount ./workspace to /workspace (version-specific workspace)
- Set working directory to /workspace
- Copy kanban/ directory to ./workspace/.kanban (making prompts and stories available in container)
- Create .env file in ./workspace with postgres connection URL and port information

**Docker Configuration:**

- Remove version field from docker-compose.yml
- Use CMD (not ENTRYPOINT) to keep container running: `CMD ["tail", "-f", "/dev/null"]`
- Add restart: unless-stopped, tty: true, stdin_open: true

**Networking:**

- Check for available host port above 8000 and bind claude container to it
- Add environment variables for postgres connection

**Environment File:**

- Create .env file in ./workspace directory containing:
  - DATABASE_URL=postgresql://claude:claudepassword321@postgres:5432/claude
  - POSTGRES_HOST=postgres
  - POSTGRES_PORT=5432
  - POSTGRES_USER=claude
  - POSTGRES_PASSWORD=claudepassword321
  - POSTGRES_DB=claude
  - CLAUDE_HOST_PORT=[selected host port for claude container]
  - CLAUDE_INTERNAL_PORT=8000
  - POSTGRES_HOST_PORT=[selected host port for postgres]
