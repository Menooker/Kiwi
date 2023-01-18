#!/usr/bin/python3

try:
    import psutil
except ImportError:
    print("please install psutil.")
    exit(0)

import time
import sys
import os
import fcntl
from os import O_RDWR

import signal
import sys

if sys.argv[1] == "--kill":
    user = sys.argv[2]
    with open("/tmp/kiwi-{}.pid".format(user)) as f:
        pid = int(f.read())
        os.kill(pid, signal.SIGUSR2)
    exit(0)

# parser = argparse.ArgumentParser()
# parser.add_argument("--user", required=True)
# parser.add_argument("--duration", type=int, required=True)
# parser.add_argument("--status-file", type=str, required=True)

user = sys.argv[1]
duration = int(sys.argv[2])
status_file = sys.argv[3]

def update_to_allocated():
    fd = os.open(status_file, O_RDWR)
    print("open done")
    fcntl.flock(fd, fcntl.LOCK_EX)
    with open(status_file) as f:
        old_status = f.read()
    if not old_status.startswith("init:"+user):
        print("Not initializing")
        exit(1)
    old_status = old_status[len("init:"):]
    with open(status_file, 'w') as f:
        f.write(old_status)
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
    return old_status

old_status = update_to_allocated()

with open("/tmp/kiwi-{}.pid".format(user), 'w') as f:
    f.write(str(os.getpid()))

wait_done = False
def kill_process():
    to_kill = []
    for proc in psutil.process_iter():
        if proc.username() == user:
            to_kill.append(proc)

    for p in to_kill:
        try:
            p.terminate()
        except:
            pass

    print("kill done")

    fd = os.open(status_file, O_RDWR)
    print("open done")
    fcntl.flock(fd, fcntl.LOCK_EX)
    with open(status_file) as f:
        new_status = f.read()
    #double check locking
    if new_status != old_status:
        print("file changed")
        exit(0)
    spl = new_status.split(" ")
    spl[0] = "[idle]"
    with open(status_file, 'w') as f:
        f.write(" ".join(spl))
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.unlink("/tmp/kiwi-{}.pid".format(user))

def signal_handler(sig, frame):
    print('Early stop')
    if wait_done:
        return
    kill_process()
    sys.exit(0)

signal.signal(signal.SIGUSR2, signal_handler)

while duration > 0:
    sleep_time = min(duration, 3600)
    duration -= sleep_time
    time.sleep(sleep_time)
    if not os.path.exists(status_file):
        exit(0)
    with open(status_file) as f:
        new_status = f.read()
    if new_status != old_status:
        exit(0)
wait_done=True
kill_process()
