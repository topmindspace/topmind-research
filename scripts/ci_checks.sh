#!/usr/bin/env bash
# 本地与 CI 共用的检查入口。只用 Python 标准库；装了 skills-ref（命令 agentskills）时额外跑官方校验器。
# 用法：bash scripts/ci_checks.sh        （仓库根目录执行）
#       AGENTSKILLS=/path/to/agentskills bash scripts/ci_checks.sh
set -u
cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"
fail=0
run() {
  echo "==> $*"
  if "$@"; then echo; else echo "!! 失败：$*"; echo; fail=1; fi
}

run "$PY" scripts/check_versions.py
run "$PY" scripts/check_skill_refs.py
run "$PY" scripts/check_sources.py --offline
run "$PY" scripts/ci_privacy_scan.py
run "$PY" topmind-research/scripts/check_citations.py --allow-placeholders \
  topmind-research/assets/templates/analyze-report.md \
  topmind-research/assets/templates/collect-weekly.md \
  topmind-research/assets/templates/fact-sheet.md
run "$PY" -m unittest discover -s tests

AS="${AGENTSKILLS:-$(command -v agentskills || true)}"
if [ -n "$AS" ]; then
  run "$AS" validate topmind-research
else
  echo "==> 跳过 agentskills validate：未安装 skills-ref（pip install skills-ref）"
  echo
fi

if [ "$fail" -ne 0 ]; then
  echo "结果：有检查未通过"
  exit 1
fi
echo "结果：全部通过"
