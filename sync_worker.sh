#!/bin/sh
set -euf

# The worker shuts down after completing n tasks
# https://github.com/cpfair/tapiriik/issues/191#issuecomment-164065625
while true; do
	# Chokes on non-absolute path!
	python3 /tapiriik/sync_worker.py
	sleep 1
done