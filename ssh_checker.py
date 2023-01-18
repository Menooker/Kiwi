#!/usr/bin/python3

import os
import socket
import pwd
import json

try:
    hostname = socket.gethostname()
except:
    print("Kiwi: Fail safe triggered: gethostname")
    exit(0)


try:
    install_path = os.path.dirname(os.path.realpath(__file__))
    with open(install_path+"/checker_config.txt") as f:
        path = f.read().strip()
    with open(path+"/config.json") as f:
        config = json.load(f)
    bypass_users = set(config["worker_ssh_bypass"])
except:
    print("Kiwi: Fail safe triggered: read config")

status_path = path+"/"+hostname+"/status.txt"
if not os.path.exists(status_path):
    print("Kiwi: Fail safe triggered: status file not found")
    exit(0)

if not os.path.exists(path+"/fail_safe.txt"):
    print("Kiwi: Fail safe triggered")
    exit(0)

try:
    with open(status_path) as f:
        status = f.read()
        spl = status.split(" ")
        if len(spl) != 4:
            print("Kiwi: Fail safe triggered: bad status file")
            exit(0)
except:
    print("Kiwi: Fail safe triggered: cannot open file")
    exit(0)

try:
    user = os.environ["PAM_USER"]
except:
    print("Kiwi: Fail safe triggered: cannot get user")
    exit(0)
if user in bypass_users:
    exit(0)
if user == spl[0] or "init:"+user == spl[0]:
    exit(0)
else:
    print("Kiwi: rejecting ssh login", user,  spl[0])
    exit(1)
