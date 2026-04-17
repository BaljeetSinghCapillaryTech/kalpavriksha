#!/bin/bash
# schedule_with_note.sh — Self-scheduling mechanism for Claude orchestrator
# Usage: ./schedule_with_note.sh <minutes> <note> [target_window]
#
# Writes a note file and schedules a delayed tmux send-keys to trigger
# a check-in in the target window after the specified delay.

MINUTES="${1:?Usage: $0 <minutes> <note> [target_window]}"
NOTE="${2:?Usage: $0 <minutes> <note> [target_window]}"
TARGET_WINDOW="${3:-$(tmux display-message -p '#{session_name}:#{window_index}' 2>/dev/null || echo '0:0')}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NOTE_FILE="$SCRIPT_DIR/next_check_note.txt"

# Write the note file
cat > "$NOTE_FILE" <<EOF
Scheduled at: $(date '+%Y-%m-%d %H:%M:%S')
Check-in after: ${MINUTES} minutes
Note: ${NOTE}
EOF

# Convert minutes to seconds
SECONDS_DELAY=$(echo "$MINUTES * 60" | bc)

# Launch detached background process
nohup bash -c "sleep $SECONDS_DELAY && tmux send-keys -t '$TARGET_WINDOW' 'echo \"--- Scheduled check-in ---\" && cat $NOTE_FILE' Enter" > /dev/null 2>&1 &

BG_PID=$!
echo "Scheduled check-in in ${MINUTES} minutes (PID: ${BG_PID}, target: ${TARGET_WINDOW})"
echo "Note: ${NOTE}"
