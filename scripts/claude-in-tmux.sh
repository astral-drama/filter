#!/bin/bash

# claude-in-tmux.sh - Start Claude in tmux and send initial command
# Usage: claude-in-tmux.sh "Say hello"

set -e

# Check if argument provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 \"<text to send to Claude>\""
    echo "Example: $0 \"Say hello\""
    exit 1
fi

TEXT_TO_SEND="$1"
SESSION_NAME="claude"

# Kill existing claude session if it exists
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

# Start new tmux session with claude command
tmux new-session -d -s "$SESSION_NAME" -c "$PWD" 'claude --dangerously-skip-permissions'

# Wait a moment for claude to start up
sleep 2

# Send the text to the claude session
tmux send-keys -t "$SESSION_NAME" "$TEXT_TO_SEND"
# Press Enter to execute the command
tmux send-keys -t "$SESSION_NAME" Enter

# Attach to the session
tmux attach-session -t "$SESSION_NAME"