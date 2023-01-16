#!/usr/bin/python3

import argparse
from email.policy import default
import fcntl
import os
from os import O_RDWR
import time
import subprocess
from datetime import datetime

install_path = os.path.dirname(os.path.realpath(__file__))

parser = argparse.ArgumentParser()
parser.add_argument("--shared-path", default=None)
sub_parsers = parser.add_subparsers(dest="command")
sub_parsers.required = True
alloc_parser = sub_parsers.add_parser("alloc")
run_parser = sub_parsers.add_parser("run")


def add_run_args(subparser):
    subparser.add_argument("--user", "-u", type=str, default=None)
    subparser.add_argument("--worker", "-w", type=str, required=True)
    subparser.add_argument("--time", "-t", type=int, default=3600)


add_run_args(alloc_parser)
add_run_args(run_parser)

kill_parser = sub_parsers.add_parser("kill")
kill_parser.add_argument("--user", "-u", type=str, required=True)
kill_parser.add_argument("--worker", "-w", type=str, required=True)

info_parser = sub_parsers.add_parser("info")

args = parser.parse_args()


def get_user():
    if not args.user:
        import getpass
        args.user = getpass.getuser()
    return args.user
    

def get_shared_path():
    if args.shared_path:
        path = args.shared_path
    else:
        with open(os.path.join(install_path, "local_config.txt")) as f:
            path = f.read().strip()
    return path

def load_config():
    path = get_shared_path()
    import json
    cfg_path = os.path.join(path, "config.json")
    with open(cfg_path) as f:
        config = json.load(f)
    return path, config


def get_worker_info_and_status_path():
    shared_path, config = load_config()
    status_file_path = os.path.join(shared_path, args.worker, "status.txt")
    return status_file_path, config


def read_status(path):
    with open(path) as f:
        new_status = f.read()
    spl = new_status.split(" ")
    if len(spl) != 4:
        print("Bad status file", path)
        exit(1)
    return (spl[0], int(spl[1]), float(spl[2]), int(spl[3]))


def do_alloc(status_file_path: str, config: dict, run: bool):
    if args.time < 0:
        print("Bad job duration")
        exit(0)
    user, jobid, start, duration = read_status(status_file_path)
    if user != "[idle]":
        print("The node is not idle")
        exit(1)

    fd = os.open(status_file_path, O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX)

    user, jobid, start, duration = read_status(status_file_path)
    if user != "[idle]":
        print("The node is not idle")
        exit(1)
    updated_status = "{} {} {} {}".format(
        get_user(), jobid+1, time.time(), args.time)
    with open(status_file_path, "w") as f:
        f.write(updated_status)
    fcntl.flock(fd, fcntl.LOCK_UN)
    worker_info = config["workers"][args.worker]
    if not run:
        subprocess.run('ssh {user}@{host} -p{port} "nohup {install}/housekeeper {user} {time} {shared_path}/{worker}/status.txt 1>/dev/null 2>/dev/null &"'.format(
            user=get_user(), host=worker_info[0], port=worker_info[1], time=args.time, shared_path=config["worker_shared_path"], install=config["worker_install_path"], worker=args.worker), shell=True)
    else:
        subprocess.run('ssh -t {user}@{host} -p{port} "nohup {install}/housekeeper {user} {time} {shared_path}/{worker}/status.txt 1>/dev/null 2>/dev/null &\n bash\n {install}/housekeeper --kill {user}"'.format(
            user=get_user(), host=worker_info[0], port=worker_info[1], time=args.time, shared_path=config["worker_shared_path"], install=config["worker_install_path"], worker=args.worker), shell=True)


def do_kill(status_file_path: str, config: dict):
    worker_info = config["workers"][args.worker]
    user, jobid, start, duration = read_status(status_file_path)
    if user != get_user():
        print("The node is not allocated by target user")
        exit(1)
    subprocess.run('ssh {user}@{host} -p{port} "nohup {install}/housekeeper --kill {user} 1>/dev/null 2>/dev/null &"'.format(
        user=get_user(), host=worker_info[0], port=worker_info[1], install=config["worker_install_path"]), shell=True)


def list_info(shared_path: str):
    print("Node\tUser\tJob Id\tStart\tDuration")
    for filename in os.scandir(shared_path):
        if filename.is_dir():
            path = os.path.join(filename.path, "status.txt")
            if os.path.exists(path):
                user, jobid, start, duration = read_status(path)
                starttime = datetime.fromtimestamp(
                    start).strftime('%Y-%m-%d %H:%M:%S')
                node_name = os.path.basename(filename.path)
                if user != "[idle]":
                    print("{}\t{}\t{}\t{}\t{}".format(
                        node_name, user, jobid, starttime, duration))
                else:
                    print("{}\t{}".format(node_name, user))


def main():
    if args.command == "alloc":
        path, config = get_worker_info_and_status_path()
        do_alloc(path, config, False)
    elif args.command == "kill":
        path, config = get_worker_info_and_status_path()
        do_kill(path, config)
    elif args.command == "run":
        path, config = get_worker_info_and_status_path()
        do_alloc(path, config, True)
    elif args.command == "info":
        path, config = load_config()
        list_info(path)


if __name__ == "__main__":
    main()
