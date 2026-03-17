#!/bin/bash

SESSION_NAME="dev"

if [ -z "$TMUX" ]; then
  tmux new-session -s "$SESSION_NAME" \; \
    split-window -v -p 30 \; \
    split-window -h -p 50 \; \
    select-pane -t 0
    else
      tmux split-window -v -p 30 \; \
        split-window -h -p 50 \; \
        select-pane -t 0
fi
