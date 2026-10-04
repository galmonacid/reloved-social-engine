#!/bin/zsh

PROJECT_DIR="/Users/guillermo/Documents/ChatGPT/ReLoved Social Engine"
PYTHON_PATH="$PROJECT_DIR/.venv/bin/python"
SCRIPT_PATH="$PROJECT_DIR/scripts/run_daily_reel.py"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/scheduled_reels.log"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR" || exit 1

run_args=()

if [[ "${RELOVED_SCHEDULE_TEST:-0}" == "1" ]]; then
    delay_seconds=0
    run_args=(
        --dry-run
        --force
        --jobs-dir
        "/tmp/reloved-launchd-wrapper-test"
    )
else
    delay_seconds=$(( RANDOM % 1801 ))
fi

{
    echo "[$(date)] Scheduled run started; waiting $delay_seconds seconds."
    sleep "$delay_seconds"

    "$PYTHON_PATH" "$SCRIPT_PATH" "${run_args[@]}"
    exit_status=$?

    echo "[$(date)] Script finished with status $exit_status."
    exit "$exit_status"
} >> "$LOG_FILE" 2>&1
