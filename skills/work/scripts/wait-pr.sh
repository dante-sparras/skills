#!/usr/bin/env bash
# Usage: wait-pr.sh <owner/repo> <number> [minutes]
# Polls a PR until it merges, closes, drops out of auto-merge or the merge queue, or the time runs out.
# Prints one word: MERGED, CLOSED, DROPPED, or TIMEOUT.
set -euo pipefail
repo=$1 number=$2 minutes=${3:-10}
owner=${repo%/*} name=${repo#*/}
query='query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){pullRequest(number:$number){state isInMergeQueue autoMergeRequest{enabledAt}}}}'
armed=false
deadline=$(( $(date +%s) + minutes * 60 ))
while :; do
  read -r state queued automerge < <(gh api graphql -f query="$query" -f owner="$owner" -f name="$name" -F number="$number" \
    --jq '.data.repository.pullRequest | "\(.state) \(.isInMergeQueue) \(.autoMergeRequest != null)"')
  case $state in MERGED | CLOSED) echo "$state"; exit 0 ;; esac
  if [[ $queued == true || $automerge == true ]]; then
    armed=true
  elif $armed; then
    echo DROPPED; exit 0
  fi
  if (( $(date +%s) >= deadline )); then echo TIMEOUT; exit 0; fi
  sleep 30
done
