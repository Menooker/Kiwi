#!/usr/bin/python3

import argparse
import os
import json

if os.geteuid() != 0:
    print("The command must be executed by root")
    exit(1)

install_path = os.path.dirname(os.path.realpath(__file__))

parser = argparse.ArgumentParser()
parser.add_argument("--shared-path", default=None)
sub_parsers = parser.add_subparsers(dest="command")
sub_parsers.required = True
init_parser = sub_parsers.add_parser("init-master")
add_parser = sub_parsers.add_parser("add-node")
add_parser.add_argument("--name", type=str, required=True)
add_parser.add_argument("--host", type=str, required=True)
add_parser.add_argument("--port", type=int, required=True)
add_parser.add_argument("--time", type=str, default=None)

del_parser = sub_parsers.add_parser("del-node")
args = parser.parse_args()


def get_shared_path():
    if args.shared_path:
        path = args.shared_path
    else:
        with open(os.path.join(install_path, "local_config.txt")) as f:
            path = f.read().strip()
    return path


def init():
    path = get_shared_path()
    os.makedirs(path)
    os.chmod(path, 0o755)
    config_path = os.path.join(path, "config.json")
    with open(config_path, "w") as f:
        f.write(
            """{
    "workers":{},
    "worker_install_path" : "/usr/lib/kiwi/",
    "worker_shared_path": "/host/kiwi/shared2/",
    "worker_ssh_bypass" : ["root"],
    "timezone": 8
}"""
        )
    os.chmod(config_path, 0o644)

    with open(os.path.join(path, "fail_safe.txt"), "w") as f:
        pass
    os.chmod(os.path.join(path, "fail_safe.txt"), 0o644)
    print("Config file is created. Please set you own config by editing", config_path)


def add():
    path = get_shared_path()
    config_path = os.path.join(path, "config.json")
    with open(config_path) as f:
        config = json.load(f)
    line = [args.host, args.port]
    if args.time:
        line.append(args.time)
    config["workers"][args.name] = line
    dir_path = os.path.join(path, args.name)
    os.makedirs(dir_path)
    os.chmod(dir_path, 0o755)

    status_path = os.path.join(path, args.name, "status.txt")
    with open(status_path, "w") as f:
        f.write("[idle] 0 0 0")
    os.chmod(status_path, 0o666)

    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)


if args.command == "init-master":
    init()
elif args.command == "add-node":
    add()
