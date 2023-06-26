#!/usr/bin/python3

import argparse
from email.policy import default
import fcntl
import os
from os import O_RDWR
import time
import subprocess
import datetime

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
    subparser.add_argument("--time", "-t", type=str, default=3600)


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


def get_arg_time():
    if isinstance(args.time, str):
        spl = [float(i) for i in args.time.split(":")]
        if len(spl) < 1 or len(spl) > 4:
            print("Bad time format")
            exit(1)
        unit = [3600 * 24, 3600, 60, 1]
        res = 0
        for idx, i in enumerate(spl):
            res += i * unit[idx + 4 - len(spl)]
        args.time = int(res)
    return args.time


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
    found_name = None
    for name, values in config["workers"].items():
        if args.worker in name:
            if found_name:
                print("Ambiguous worker name, candidates: ", found_name, name)
                exit(1)
            found_name = name
    if not found_name:
        print("Worker name not found:", args.worker)
        exit(1)
    args.worker = found_name
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


def do_kill_init(status_file_path: str, config: dict):
    fd = os.open(status_file_path, O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX)
    user, jobid, start, duration = read_status(status_file_path)
    if user != "init:" + get_user():
        print("do_kill_init: The node is not initializing for this user")
        exit(1)
    updated_status = "{} {} {} {}".format("[idle]", jobid, start, duration)
    with open(status_file_path, "w") as f:
        f.write(updated_status)
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)


def parse_reserve_duration(dur: str, now: datetime.datetime):
    ret = []
    for start_end in dur.split(","):
        spl = start_end.split("-")
        if len(spl) != 2:
            print("Bad duration in config.json")
            exit(1)
        fmt = "%H:%M"
        start = datetime.datetime.strptime(spl[0], fmt)
        end = datetime.datetime.strptime(spl[1], fmt)
        start=start.replace(year=now.year, month=now.month, day = now.day, tzinfo = now.tzinfo)
        end=end.replace(year=now.year, month=now.month, day = now.day, tzinfo = now.tzinfo)
        if start > end:
            ret.append((datetime.datetime(now.year, now.month, now.day, tzinfo = now.tzinfo), end))
            end += datetime.timedelta(days=1)
        ret.append((start, end))
    return ret


def do_alloc(status_file_path: str, config: dict, run: bool):
    if get_arg_time() < 0:
        print("Bad job duration")
        exit(0)
    worker_info = config["workers"][args.worker]
    timezone = config.get("timezone", 8)
    tz = datetime.timezone(datetime.timedelta(hours=timezone))
    now = datetime.datetime.now(tz)
    if len(worker_info) > 2:
        durations = parse_reserve_duration(worker_info[2], now)
        endtime = now + datetime.timedelta(seconds=get_arg_time())
        ok = False
        for st, ed in durations:
            if now >= st and endtime <= ed:
                ok = True
                break
        if not ok:
            print("The worker is not reservable")
            exit(1)
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
        "init:" + get_user(), jobid + 1, time.time(), get_arg_time()
    )
    with open(status_file_path, "w") as f:
        f.write(updated_status)
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
    try:
        if not run:
            subprocess.run(
                'ssh {user}@{host} -p{port} "nohup {install}/housekeeper {user} {time} {shared_path}/{worker}/status.txt 1>/dev/null 2>/dev/null &"'.format(
                    user=get_user(),
                    host=worker_info[0],
                    port=worker_info[1],
                    time=get_arg_time(),
                    shared_path=config["worker_shared_path"],
                    install=config["worker_install_path"],
                    worker=args.worker,
                ),
                shell=True,
                check=True,
            )
        else:
            subprocess.run(
                'ssh -t {user}@{host} -p{port} "nohup {install}/housekeeper {user} {time} {shared_path}/{worker}/status.txt 1>/dev/null 2>/dev/null &\n bash\n {install}/housekeeper --kill {user}"'.format(
                    user=get_user(),
                    host=worker_info[0],
                    port=worker_info[1],
                    time=get_arg_time(),
                    shared_path=config["worker_shared_path"],
                    install=config["worker_install_path"],
                    worker=args.worker,
                ),
                shell=True,
                check=True,
            )
    except:
        print("Failed to alloc. Cleaning up the state")
        do_kill_init(status_file_path, config)


def do_kill(status_file_path: str, config: dict):
    worker_info = config["workers"][args.worker]
    user, jobid, start, duration = read_status(status_file_path)
    if user == "init:" + get_user():
        do_kill_init(status_file_path, config)
        exit(0)
    if user != get_user():
        print("The node is not allocated by target user")
        exit(1)
    subprocess.run(
        'ssh {user}@{host} -p{port} "nohup {install}/housekeeper --kill {user} 1>/dev/null 2>/dev/null &"'.format(
            user=get_user(),
            host=worker_info[0],
            port=worker_info[1],
            install=config["worker_install_path"],
        ),
        shell=True,
    )


def list_info(shared_path: str, config: dict):
    timezone = config.get("timezone", 8)
    tz = datetime.timezone(datetime.timedelta(hours=timezone))
    print(
        "{:25}{:15}{:10}{:25}{:10}".format(
            "Node", "User", "Job ID", "Start", "Duration"
        )
    )
    for filename in os.scandir(shared_path):
        if filename.is_dir():
            path = os.path.join(filename.path, "status.txt")
            if os.path.exists(path):
                user, jobid, start, duration = read_status(path)
                starttime = datetime.datetime.fromtimestamp(start, tz).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                node_name = os.path.basename(filename.path)
                if user != "[idle]":
                    print(
                        "{node:25}{curuser:15}{id:10}{start:25}{duration:10}".format(
                            node=node_name,
                            curuser=user,
                            id=str(jobid),
                            start=starttime,
                            duration=str(datetime.timedelta(seconds=duration)),
                        )
                    )
                else:
                    print("{node:25}{curuser:15}".format(node=node_name, curuser=user))


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
        list_info(path, config)


if __name__ == "__main__":
    main()
