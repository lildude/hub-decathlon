#!/bin/sh
set -euf

if [ -f /tmp/leader_only ]
    then
        python3 /tapiriik/sync_scheduler.py
    fi
