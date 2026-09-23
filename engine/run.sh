#!/usr/bin/env bash
# 引擎统一执行入口。
# 为什么不用裸 pytest：本机装了 ROS，其 launch_testing 插件会被 pytest
# 自动加载并因缺依赖报错——这里固定禁用插件自动加载，保证在任何机器上行为一致。
# 平台后端(runner.py)和 CI 都通过本脚本执行测试。
set -e
cd "$(dirname "$0")"

export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export SUT_BASE_URL="${SUT_BASE_URL:-http://localhost:8000}"

# 本机开发优先用项目 venv；容器/CI 镜像里没有 venv，用系统 python
if [ -x ".venv/bin/python" ]; then
  PY=.venv/bin/python
else
  PY=python3
fi

# $@ 可选：传给 pytest 的额外参数（如 -m smoke / --junitxml=...）
exec "$PY" -m pytest "$@"
