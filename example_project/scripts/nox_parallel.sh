#!/usr/bin/env bash
# Run every nox session concurrently and show a live status table.
#
# Usage: nox_parallel.sh [jobs]
#
#   jobs  How many sessions to run at once, as a number or as a percentage of
#         the CPU cores. Defaults to "100%".
#
# Each session writes its output to ".nox/logs/<session>.log", which stays in place
# after the run so that a failing session can be read.
set -uo pipefail

jobs="${1:-100%}"
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1

# Poetry asks the system keyring for credentials on every install. With this many
# installs at once a SecretService lookup can fail, and Poetry reports that as
# "Cannot install <package>" instead of moving on. The project has no private
# package source, so there is nothing for the keyring to answer.
export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring

logs=".nox/logs"
joblog="$logs/joblog.tsv"
sessions="$logs/sessions.txt"
rm -rf "$logs" && mkdir -p "$logs"
# An aborted run leaves per-session coverage data behind, which the combine at the
# end would otherwise fold into this run.
rm -f .coverage.*

poetry run nox --list --json 2>/dev/null | jq -r '.[].session' > "$sessions"
mapfile -t names < "$sessions"
total=${#names[@]}

slugs=() width=0
for name in "${names[@]}"; do
  slugs+=("$(printf %s "$name" | tr -c '[:alnum:]' '-')")
  [ ${#name} -gt $width ] && width=${#name}
done

tty=0
if [ -t 1 ]; then tty=1; fi
rows=$(tput lines 2>/dev/null || echo 24)
live_max=$((rows - 4))
if [ "$live_max" -lt 1 ]; then live_max=1; fi

# Each session gets its own coverage data file. Sessions run "coverage combine",
# which consumes every parallel data file next to the data file it writes to.
# Without a per-session data file, the first session to combine takes the data
# of the sessions still running, and those sessions then fail with "No data to combine".
# Each session also gets its own log file, so that session output does not
# interleave on the terminal. The table below reports progress instead. Each log
# ends with the lines that session left uncovered, which is the part worth reading
# when the combined coverage at the end is short of 100%.
(
  parallel -j"$jobs" --joblog "$joblog" \
    'slug="$(printf %s {} | tr -c "[:alnum:]" "-")"
     dir="'"$logs"'"
     export COVERAGE_FILE=".coverage.$slug"
     poetry run nox -s {} > "$dir/$slug.log" 2>&1
     rc=$?
     if report="$(poetry run coverage report --skip-covered --show-missing 2>/dev/null)"; then
       printf "\n--- coverage: lines this session did not cover ---\n%s\n" "$report" >> "$dir/$slug.log"
       printf %s "$report" | grep "^TOTAL" | grep -oE "[0-9]+%" | tail -1 | tr -d "%" > "$dir/$slug.pct"
     fi
     exit $rc' \
    < "$sessions" 2> "$logs/parallel.log"
  printf %s "$?" > "$logs/status"
) &
runner=$!

declare -A code secs reported
finished=0
live=0
drawn=""

# Column 1 of the job log is the line the session was read from, column 4 its
# runtime and column 7 its exit code.
read_joblog() {
  if [ ! -s "$joblog" ]; then return 0; fi
  local seq host start runtime send recv exitval rest
  while IFS=$'\t' read -r seq host start runtime send recv exitval rest; do
    if [ "$seq" = "Seq" ]; then continue; fi
    if [ -z "${code[$seq]:-}" ]; then finished=$((finished + 1)); fi
    code[$seq]=$exitval
    secs[$seq]=${runtime%%.*}
  done < "$joblog"
}

# Percentage pytest last printed, or the phase the session is still in.
progress() {
  local log="$logs/${slugs[$1 - 1]}.log" pct
  if [ ! -f "$log" ]; then printf 'queued'; return; fi
  pct="$(grep -oE '\[ *[0-9]+%\]' "$log" | tail -1 | tr -dc '0-9')"
  if [ -n "$pct" ]; then printf '%3s%%' "$pct"; else printf 'starting'; fi
}

# Percentage the session covered on its own. A skipped session reports nothing.
session_coverage() {
  local file="$logs/${slugs[$1 - 1]}.pct"
  if [ ! -s "$file" ]; then return 0; fi
  printf '%s%%' "$(cat "$file")"
}

# Test counts pytest printed in its summary banner, without the timing and warnings.
outcome() {
  local log="$logs/${slugs[$1 - 1]}.log" banner
  banner="$(grep -E '^=+ .*(passed|failed|error|no tests ran).* =+$' "$log" | tail -1)"
  if [ -n "$banner" ]; then
    printf '%s' "$banner" | sed -E 's/^=+ +//; s/ +=+$//; s/,? *[0-9]+ warnings?//; s/ in [0-9.]+s.*$//'
  elif grep -q 'skipped\.$' "$log"; then
    printf 'skipped'
  else
    printf 'no tests ran'
  fi
}

# Build a whole frame and write it in one call. Erasing the old frame first would
# leave the screen blank while the next one is built, which reads as flashing.
render() {
  local mode="$1" i mark state name pad shown=0 hidden=0 line frame=""
  local lines=()

  # Sessions that finished since the last frame. These scroll out of the live
  # block and stay on screen.
  for ((i = 1; i <= total; i++)); do
    if [ -z "${code[$i]:-}" ] || [ -n "${reported[$i]:-}" ]; then continue; fi
    reported[$i]=1
    mark=' ok '
    if [ "${code[$i]}" != 0 ]; then mark='FAIL'; fi
    if [ "$tty" = 1 ] && [ "${code[$i]}" != 0 ]; then mark=$'\033[31mFAIL\033[0m'; fi
    # Name the log file behind the session name, so that ctrl-clicking it opens the
    # log. The URI names no host, because PyCharm resolves it through java.nio, which
    # rejects a file URI that carries an authority. The escapes take no columns, so pad
    # the name before wrapping it.
    name="${names[$i - 1]}"
    pad="$(printf '%*s' "$((width - ${#name}))" '')"
    if [ "$tty" = 1 ]; then
      name=$'\033]8;;file://'"$PWD/$logs/${slugs[$i - 1]}.log"$'\033\\'"$name"$'\033]8;;\033\\'
    fi
    lines+=("$(printf '%s  %s%s  %-24s %5s  %4ss' \
      "$mark" "$name" "$pad" "$(outcome "$i")" \
      "$(session_coverage "$i")" "${secs[$i]}")")
  done
  local scrolled=${#lines[@]}

  if [ "$mode" = live ]; then
    lines+=("$(printf '\033[2m--- %d/%d sessions done ---\033[0m' "$finished" "$total")")
    for ((i = 1; i <= total; i++)); do
      if [ -n "${code[$i]:-}" ]; then continue; fi
      state="$(progress "$i")"
      if [ "$state" = queued ]; then continue; fi
      if [ "$shown" -lt "$live_max" ]; then
        lines+=("$(printf '      %-*s  %s' "$width" "${names[$i - 1]}" "$state")")
        shown=$((shown + 1))
      else
        hidden=$((hidden + 1))
      fi
    done
    if [ "$hidden" -gt 0 ]; then lines+=("$(printf '      ... and %d more' "$hidden")"); fi
  fi

  if [ "$tty" != 1 ]; then
    for line in "${lines[@]}"; do printf '%s\n' "$line"; done
    return
  fi

  # A frame that repeats the last one has nothing to redraw.
  local body; body="$(printf '%s\n' "${lines[@]}")"
  if [ "$scrolled" = 0 ] && [ "$body" = "$drawn" ]; then return; fi
  drawn="$body"

  # Start at the top of the previous live block and overwrite it line by line.
  if [ "$live" -gt 0 ]; then frame+=$'\033'"[${live}A"; fi
  for line in "${lines[@]}"; do frame+=$'\033[2K'"$line"$'\n'; done
  # A shorter frame leaves rows of the previous one below the cursor.
  if [ "${#lines[@]}" -lt "$live" ]; then frame+=$'\033[J'; fi
  live=$((${#lines[@]} - scrolled))

  printf '%s' "$frame"
}

# GNU parallel runs each session in its own process group, so a SIGHUP from a
# closing terminal never reaches them. Walk the process tree to find them.
descendants() {
  local pid=$1 child
  for child in $(pgrep -P "$pid" 2>/dev/null); do
    printf '%s\n' "$child"
    descendants "$child"
  done
}

# Stop every session this run started. Otherwise closing the terminal, or pressing
# ctrl-c, leaves nox and pytest running and writing coverage data.
cleanup() {
  local status=$? pids
  trap - EXIT HUP INT TERM
  if [ "$tty" = 1 ]; then printf '\033[?25h'; fi
  if [ ! -f "$logs/status" ]; then
    echo "Stopping sessions..."
    pids="$(descendants "$runner")"
    kill -TERM "$runner" $pids 2>/dev/null
    sleep 2
    kill -KILL "$runner" $pids 2>/dev/null
  fi
  exit "$status"
}

if [ "$tty" = 1 ]; then printf '\033[?25l'; fi
trap cleanup EXIT HUP INT TERM

while :; do
  running=1
  if [ -f "$logs/status" ]; then running=0; fi
  read_joblog
  mode=done
  if [ "$running" = 1 ] && [ "$tty" = 1 ]; then mode=live; fi
  render "$mode"
  if [ "$running" = 0 ]; then break; fi
  sleep 0.5
done
wait
if [ "$tty" = 1 ]; then printf '\033[?25h'; fi

# Merge the per-session data files into the ".coverage" file.
poetry run coverage combine

summary="$(printf 'Ran %d sessions in %dm %02ds.' "$total" "$((SECONDS / 60))" "$((SECONDS % 60))")"
if combined="$(poetry run coverage report --format=total 2>/dev/null)"; then
  summary="$summary Combined coverage $combined%."
fi
echo "$summary"

# GNU parallel exits with the number of sessions that failed. An empty job log means
# it never started one, and the reason is in its own log.
status="$(cat "$logs/status")"
if [ ! -s "$joblog" ]; then echo "No sessions ran. See $logs/parallel.log"; fi
exit "$status"
