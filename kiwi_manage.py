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
parser.add_argument("--partition", "-p", default=None)
sub_parsers = parser.add_subparsers(dest="command")
sub_parsers.required = True
init_parser = sub_parsers.add_parser("init-master")
add_parser = sub_parsers.add_parser("add-node")
add_parser.add_argument("--name", type=str, required=True)
add_parser.add_argument("--host", type=str, required=True)
add_parser.add_argument("--port", type=int, required=True)
add_parser.add_argument("--time", type=str, default=None)
add_parser.add_argument("--label", type=str, default="")

add_parser = sub_parsers.add_parser("partition")
add_parser.add_argument("--path", type=str, required=True)
add_parser.add_argument("--label", type=str, required=True)

del_parser = sub_parsers.add_parser("del-node")
args = parser.parse_args()


def get_shared_path():
    if args.shared_path:
        path = args.shared_path
    else:
        with open(os.path.join(install_path, "local_config.txt")) as f:
            paths = f.readlines()
            if not args.partition:
                path = paths[0].strip().split(":")[0]
            else:
                path = None
                for line in paths:
                    p, label = line.strip().split(":")
                    if label == args.partition:
                        path = p
                        break
                if not path:
                    print("Cannot find the partition in ", paths)
                    exit(1)
    return path


def init():
    path = get_shared_path()
    os.makedirs(path)
    os.chmod(path, 0o755)
    config_path = os.path.join(path, "config.json")
    if os.path.exists(config_path):
        print(
            "The file ",
            config_path,
            "exists. Have you initialized before? To reset previous installation, please delete this file.",
        )
        exit(1)
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
    line = [args.host, args.port, "", args.label]
    if args.time:
        line[2] = args.time
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


def partition():
    with open(os.path.join(install_path, "local_config.txt")) as f:
        paths = f.readlines()
        found = False
        for idx, line in enumerate(paths):
            spl = line.strip().split(":")
            if len(spl) != 1 and len(spl) > 2:
                print(
                    "Bad file content",
                    os.path.join(install_path, "local_config.txt"),
                    ": ",
                    line,
                )
            if len(spl) == 1:
                label = ""
                path = spl[0]
            else:
                path, label = spl
            if path == args.path:
                label = args.label
                paths[idx] = "{}:{}\n".format(path, label)
                found = True
                break
        if not found:
            paths.append("{}:{}\n".format(args.path, args.label))

    with open(os.path.join(install_path, "local_config.txt"), "w") as f:
        f.write("".join(paths))


if args.command == "init-master":
    init()
elif args.command == "add-node":
    add()
elif args.command == "partition":
    partition()
