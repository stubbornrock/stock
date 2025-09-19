#!/bin/bash

SESSION_BACKEND="backend"
SESSION_BACKEND_COMMAND="cd /root/apps/; python ebm.py"

#
rm -rf *.log
# 检查 tmux session 是否存在
tmux has-session -t "$SESSION_BACKEND" 2>/dev/null

if [ $? != 0 ]; then
  echo "Creating new tmux session: $SESSION_BACKEND"
  tmux new-session -d -s "$SESSION_BACKEND" "$SESSION_BACKEND_COMMAND"
else
  echo "tmux session $SESSION_BACKEND already exists. Restarting..."
  # 先杀掉已有 session
  tmux kill-session -t "$SESSION_BACKEND"
  # 再创建新的 session
  tmux new-session -d -s "$SESSION_BACKEND" "$SESSION_BACKEND_COMMAND"
fi

echo "Done."
