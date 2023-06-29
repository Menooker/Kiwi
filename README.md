# Kiwi: Cluster sharing made simple

Kiwi is a simple cluster booking mangement tool. It can be viewed as an (over) simplified replacement of SLURM cluster manager. The features of Kiwi include:

 * NFS+SSH based cluster info management and viewing
 * Booking a node from the cluster with a duration and preventing others from booking the same node when it is in use
 * Preventing users from logging into unallocated node via SSH.
 * Process cleaning-up by user-id when the booking duration expires or the job is killed

Dependency: python3, psutil, SSH, NFS, gcc

## Why use Kiwi, not SLURM?

SLURM is great in most of aspects, except that it is a bit complex. The user needs to configure munge, NTP and some more configrations to make it work. When we manage a cluster when the nodes of the cluster occationally leave, join and re-image, we find that installing SLURM and re-configuring SLURM takes too much effort. What we want is simply a node booking system for a few users and a process clean-up system. That's why we develop kiwi.

## How it works

Kiwi uses NFS to share the states of the nodes. A NFS mounted path should be configured at the installation of Kiwi. The NFS path should be shared by all nodes in the cluster and each node should have the same path. For each node, Kiwi maintains a status file which stores the current allocated user, current job-id, job allocation timestamp and the job duration on the node.

To allocate a node, Kiwi firstly check the status file for the node to make sure it is idle. It then changes the allocated user in the file to indicate that the node is allocated. A house-keeper process is launched at the background on the allocated node, which will kill all processes on that node of the user.

Kiwi also hooks the SSH login event, which is implemented by SSH's PAM feature. It will check if the login user of SSH is the allocated user in the node's status file.

## Install guide

First, you need to install NFS and make sure all nodes can access a NFS directory at the same path. In the following part of this guide, we assume that the NFS root directory is at `/nfs`. We will put the shared states of Kiwi at path `/nfs/kiwi`. Please change the path in the following command according to the path at your system. Then run the command on each node of the cluster:

```bash
git clone https://github.com/Menooker/Kiwi
cd Kiwi
sudo sh ./install.sh /usr /nfs/kiwi
```

On one of the node in the cluster:

```bash
sudo kiwi-manage init-master
```

This will initialize the shared state directory.

If you would like to change the timezone of the kiwi cluster, please edit `/nfs/kiwi/config.json` and change the `"timezone": 8` line. By default, the timezone is `UTC+8`.

To add a node, run

```bash
sudo kiwi-manage add-node --name {host_name} --host {ip_or_host} --port {port} [--label={lable}]
```

Note that if you log into a node using `ssh user@aaa.company.com`, usually `{host_name}` above should be "aaa" and `{ip_or_host}` above should be `aaa.company.com`.

To add a node and let it only accept reservation during limited time ranges, run

```bash
sudo kiwi-manage add-node --name {host_name} --host {ip_or_host} --port {port} --time hh:mm-hh:mm[,hh:mm-hh:mm,...]
```

Please also edit `/nfs/kiwi/config.json` and change the `worker_shared_path` field. In our example, it should be

```
"worker_shared_path": "/nfs/kiwi/"
```

Please check if the "housekeeper" of Kiwi works. A common issue is that the `psutil` python module is not properly installed. This might be an issue of SELinux. You can check if it is working by running

```
/usr/lib/kiwi/housekeeper
```

It is **OK** to fail like:

```
Traceback (most recent call last):
  File "/usr//lib/kiwi//housekeeper.py", line 18, in <module>
    if sys.argv[1] == "--kill":
IndexError: list index out of range
```

If it outputs `please install psutil...`, please copy the `psutil` files to the Python path specified.

If you want to allow some of the users to login the nodes without Kiwi allocation (e.g. admin users), you can add the user names to "worker_ssh_bypass" list.

To enable SSH login filter, you need to edit `/etc/pam.d/sshd` on each **worker** node. (Warning: After you edit this file, users cannot login to the node until they have an allocation on the node via Kiwi, or the user is in "worker_ssh_bypass" list.) Please keep an SSH session alive after you edit this file, so that if anything goes wrong, you can undo your changes in `/etc/pam.d/sshd`. Also, please add at least one user to the `worker_shared_path` field in the config file, to avoid being blocked by SSH login. Do **NOT** change this file on your master node.

In `/etc/pam.d/sshd`, after the last `account XXX XXX` line, add a new line:

```bash
account required pam_exec.so /usr/lib/kiwi/ssh_checker.py
```

You can check if works properly. On the "master" node, run

```
kiwi alloc -u {username} -w {host} -t 100
ssh {username}@{host}
```

## User guide

The following command are used to book and return nodes in the cluster.

### To list avaliable nodes

```
kiwi info
```

### To allocate a node

```
kiwi alloc -u {username} -w {host} -t {time_in_seconds}
```

The username can be omitted if you would like to allocate in the name of the current user on the node. The "host" parameter should be an idle node listed in `kiwi info`. The `time_in_seconds` parameter should be the duration of the job in seconds. After the time expires, all processes of the user will be killed on the node.

After allocation, users can use ssh to login the node.


### To allocate and run bash on a node

```
kiwi run -u {username} -w {host} -t {time_in_seconds}
```

The meaning of the parameters are the same of `kiwi alloc`

### To kill a job on a node

```
kiwi kill -u {username} -w {host}
```

This will kill the processes of that user on the node and the node will be idle.

## Managing multiple partitions

Kiwi can manage multiple clusters (partitions) on a single master node. A partition is managed by a NFS shared directory. To add a parition in Kiwi, you need to first mount the NFS directory of the partition in local file system. Then you need to add it to Kiwi's local configuration via

```
sudo kiwi-manage partition --path={NFS path} --label={partition name}
```

If the partition has already been initialized by `kiwi-manage init-master`, you can see the partition in

```
kiwi info
```

If the partition NFS directory has not been initialized yet, you can initialize it via

```
sudo kiwi-manage -p {partition_name} init-master
```

or

```
sudo kiwi-manage --shared-path {partition NFS path} init-master
```

Most `kiwi` and `kiwi-manage` commands has an optional `-p` switch to specify which partition to use. If no `-p` option is given, `kiwi-manage` and `kiwi` will use the first partition listed in `local_config.txt` of the installed path.

For example, to list node states of parition "p1":

```
kiwi -p p1 info
```

To allocate node in partition "p1":

```
kiwi -p p1 alloc -w node-name 
```

