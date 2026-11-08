#!/usr/bin/env bash
# Replace the placeholders with your GitHub username (and your name for the license).
# Usage: ./scripts/set_github_user.sh your-username "Your Name"
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <github-username> [\"Your Name\"]" >&2
  exit 1
fi

USER_NAME="$1"
FULL_NAME="${2:-$1}"
cd "$(dirname "$0")/.."

FILES=$(grep -rIl --exclude-dir=.git -e "YOUR_GITHUB_USERNAME" -e "YOUR NAME" . || true)
for f in $FILES; do
  sed -i.bak -e "s/YOUR_GITHUB_USERNAME/${USER_NAME}/g" -e "s/YOUR NAME/${FULL_NAME}/g" "$f"
  rm -f "$f.bak"
done
echo "Updated: ${FILES:-nothing to change}"
