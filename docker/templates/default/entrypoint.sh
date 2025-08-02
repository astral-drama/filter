#!/bin/bash

# Default entrypoint for Claude container
# Runs claude-in-tmux.sh without arguments for manual Claude session

set -e

echo "=== Entrypoint Debug ==="
echo "STORY_NAME: '$STORY_NAME'"
echo "STORY_PATH: '$STORY_PATH'"
echo "PROJECT_NAME: '$PROJECT_NAME'"
echo "Current directory: $(pwd)"
echo "Environment variables with STORY:"
env | grep STORY || echo "No STORY variables found"
echo "========================"

# Check if this is a story workspace by looking for story environment variables
if [ -n "$STORY_NAME" ] && [ -n "$STORY_PATH" ]; then
    echo "Detected story workspace: $STORY_NAME"
    echo "Running claude-in-tmux.sh with story prompt..."
    # Story workspace - provide context to Claude
    claude-in-tmux.sh "Read the .env file, read the story at $STORY_PATH and start working on the story"
else
    echo "Regular workspace detected - starting Claude without prompt"
    # Regular workspace - just start Claude
    claude-in-tmux.sh
fi