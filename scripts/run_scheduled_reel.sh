#!/bin/zsh

PROJECT_DIR="/Users/guillermo/Developer/ReLoved Social Engine"
PYTHON_PATH="$PROJECT_DIR/.venv/bin/python"
SCRIPT_PATH="$PROJECT_DIR/scripts/run_daily_reel.py"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/scheduled_reels.log"

# launchd does not inherit the interactive shell's environment.
export PATH="/Users/guillermo/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

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
    run_args=(--force)
fi

{
    echo "[$(date)] Scheduled run started; waiting $delay_seconds seconds."
    if [[ "${RELOVED_SCHEDULE_TEST:-0}" != "1" ]]; then
        "$PYTHON_PATH" "$SCRIPT_PATH" --check-auth
        auth_status=$?
        if (( auth_status != 0 )); then
            echo "[$(date)] Authentication preflight failed with status $auth_status; renew the Meta credentials in .env."
            /usr/bin/osascript -e 'display notification "Publishing is blocked. Check scheduled_reels.log and renew the Meta credentials in .env." with title "ReLoved publishing failed"' || true
            exit "$auth_status"
        fi
    fi
    sleep "$delay_seconds"

    "$PYTHON_PATH" "$SCRIPT_PATH" "${run_args[@]}"
    exit_status=$?

    echo "[$(date)] Script finished with status $exit_status."
    exit "$exit_status"
} >> "$LOG_FILE" 2>&1
