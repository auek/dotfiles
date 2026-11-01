"""Small process-lifecycle helpers shared by the isolated integration checks."""

import os
import select
import subprocess


def stop_tmux(executable, socket, env):
    """Stop only a private server and wait before its home/socket is removed."""
    command = [executable, "-S", str(socket)]
    panes = subprocess.run([*command, "list-panes", "-a", "-F", "#{pid} #{pane_pid}"],
                           env=env, capture_output=True, text=True, timeout=10)
    descriptors = []
    try:
        for pid in set(panes.stdout.split()):
            try:
                descriptors.append(os.pidfd_open(int(pid)))
            except ProcessLookupError:
                pass
        subprocess.run([*command, "kill-server"], env=env, capture_output=True, timeout=10)
        # kill-server may return before shells save history or the server unlinks
        # its socket. Wait for those exact processes, without sleeps/retries.
        for descriptor in descriptors:
            if not select.select([descriptor], [], [], 10)[0]:
                raise TimeoutError("private tmux process did not exit during cleanup")
    finally:
        for descriptor in descriptors:
            os.close(descriptor)
