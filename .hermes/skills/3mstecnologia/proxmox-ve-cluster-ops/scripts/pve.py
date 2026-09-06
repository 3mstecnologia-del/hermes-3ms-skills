#!/usr/bin/env python3
"""Read-only Proxmox VE access helper (Madalena Labs, skill proxmox-ve-cluster-ops).

Dependencies: Python 3.9+ stdlib (urllib); for SSH verbs it shells out to
`sshpass` + `ssh`.

Credentials come ONLY from the environment at runtime (never args, never logs):
  Direct:
    PVE_HOST   (e.g. 192.0.2.10)
    PVE_PW     (password)
    PVE_USER   (default root@pam)
    PVE_API_PORT (default 8006)
    PVE_SSH_PORT (default 22)
  Or node prefix (matches Cofre layout, e.g. Cofre UNIPLAC //legacy):
    PVE_UNIPLAC_01_HOST / _USERNAME / _PASSWORD / _SSH_PORT / _API_PORT
    ... then run with --node 01

Usage:
  pve.py --node 01 api-status
  pve.py --host 192.0.2.10 --user root@pam version
  pve.py --node 01 nodes
  pve.py --node 01 guests [node]
  pve.py --node 01 vms [node] | cts [node]
  pve.py --node 01 vm-config <node> <vmid> [--keys cores,memory,sockets,scsi0]
  pve.py --node 01 lxc-config <node> <vmid>
  pve.py --node 01 storage | tasks <node> [--limit 20] | node-status <node>
  pve.py --node 01 cluster-health      # quorum via SSH `pvecm status`
  pve.py --node 01 ssh '<cmd>'         # run a privileged command via sshpass/ssh

Exit code 0 on success; non-zero with a short message on failure.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
import ssl
import http.cookiejar


def _norm_user(u):
    """Ensure the API user has a realm (PVE API rejects a bare username)."""
    u = u or "root@pam"
    return u if "@" in u else f"{u}@pam"


def env_for_node(node):
    """Build a dict of credential fields from the environment (runtime only)."""
    if not node:
        return None
    p = f"PVE_UNIPLAC_{node}"
    host = os.environ.get(f"{p}_HOST")
    if not host:
        return None
    return {
        "host": host,
        "port": int(os.environ.get(f"{p}_API_PORT", "8006")),
        "user": _norm_user(os.environ.get(f"{p}_USERNAME")),
        "password": os.environ.get(f"{p}_PASSWORD", ""),
        "ssh_port": int(os.environ.get(f"{p}_SSH_PORT", "22")),
        "ssh_user": os.environ.get(f"{p}_SSH_USER", "root"),
        "ssh_password": os.environ.get(f"{p}_SSH_PASSWORD", os.environ.get(f"{p}_PASSWORD", "")),
    }


def creds(args):
    if args.node:
        c = env_for_node(args.node)
        if not c:
            sys.exit(f"credenciales no encontradas para PVE_UNIPLAC_{args.node}_* en el entorno")
        return c
    return {
        "host": args.host, "port": args.port, "user": args.user,
        "password": os.environ.get("PVE_PW", ""),
        "ssh_port": args.ssh_port, "ssh_user": args.ssh_user,
        "ssh_password": os.environ.get("PVE_PW", ""),
    }


class PveApi:
    def __init__(self, c):
        self.base = f"https://{c['host']}:{c['port']}/api2/json"
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE
        self._jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=self._ctx),
            urllib.request.HTTPCookieProcessor(self._jar),
        )
        self._csrf = self._login(c["user"], c["password"])

    def _login(self, user, password):
        data = urllib.parse.urlencode(
            {"username": user, "password": password}
        ).encode()
        req = urllib.request.Request(self.base + "/access/ticket", data=data)
        with self._opener.open(req, timeout=25) as resp:
            body = json.loads(resp.read().decode())
        # PVE 8.x devuelve el ticket solo en el JSON; el valor ES el PVEAuthCookie.
        ticket = body["data"].get("ticket", "")
        self._cookie = f"PVEAuthCookie={ticket}" if ticket else ""
        return body["data"].get("CSRFPreventionToken", "")

    def get(self, path):
        headers = {}
        if self._csrf:
            headers["CSRFPreventionToken"] = self._csrf
        if self._cookie:
            headers["Cookie"] = self._cookie
        req = urllib.request.Request(self.base + path, headers=headers)
        with self._opener.open(req, timeout=25) as resp:
            return json.loads(resp.read().decode()).get("data")


def ssh(c, cmd):
    if not c["ssh_password"]:
        sys.exit("PVE password (SSH) no configurada en el entorno")
    argv = ["sshpass", "-p", c["ssh_password"], "ssh",
            "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=8", "-o", "LogLevel=ERROR",
            "-p", str(c["ssh_port"]),
            f"{c['ssh_user']}@{c['host']}", cmd]
    return subprocess.run(argv, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser(description="Proxmox VE read-only access")
    ap.add_argument("--node", help="prefijo de nodo, p.ej. 01 -> PVE_UNIPLAC_01_*")
    ap.add_argument("--host", help="host directo")
    ap.add_argument("--port", type=int, default=8006)
    ap.add_argument("--user", default="root@pam")
    ap.add_argument("--ssh-port", type=int, default=22)
    ap.add_argument("--ssh-user", default="root")
    ap.add_argument("--keys", help="lista de claves separadas por coma (set_projected)")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("command", nargs="+")
    args = ap.parse_args()
    c = creds(args)
    cmd = args.command[0]

    def proj(obj, keys):
        if not args.keys:
            return obj
        ks = set(args.keys.split(","))
        if isinstance(obj, list):
            return [{k: it.get(k) for k in ks} for it in obj]
        return {k: obj.get(k) for k in ks}

    if cmd == "ssh":
        r = ssh(c, " ".join(args.command[1:]))
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        sys.exit(r.returncode)

    if cmd in ("api-status", "cluster-health"):
        # cluster-health runs pvecm status over SSH for quorum
        if cmd == "cluster-health":
            r = ssh(c, "pvecm status")
            print(r.stdout)
            sys.exit(r.returncode)
        # api-status: prove auth + version
        api = PveApi(c)
        ver = api.get("/version")
        print(json.dumps(ver, indent=2, default=str))
        sys.exit(0)

    api = PveApi(c)
    if cmd == "version":
        print(json.dumps(api.get("/version"), indent=2, default=str))
    elif cmd == "nodes":
        print(json.dumps(proj(api.get("/nodes"), ["node","status","uptime"]), indent=2, default=str))
    elif cmd == "resources":
        print(json.dumps(api.get("/cluster/resources"), indent=2, default=str))
    elif cmd in ("vms", "cts", "guests"):
        node = args.command[1] if len(args.command) > 1 else None
        if cmd == "guests":
            out = {}
            for t in ("qemu", "lxc"):
                rec = api.get(f"/nodes/{node}/{( 'qemu' if t=='qemu' else 'lxc')}")
                out[t] = proj(rec, ["vmid","name","status","type"])
            print(json.dumps(out, indent=2, default=str))
        else:
            kind = "qemu" if cmd == "vms" else "lxc"
            rec = api.get(f"/nodes/{node}/{kind}")
            print(json.dumps(proj(rec, ["vmid","name","status","type"]), indent=2, default=str))
    elif cmd in ("vm-config", "lxc-config"):
        node, vmid = args.command[1], int(args.command[2])
        kind = "qemu" if cmd == "vm-config" else "lxc"
        cfg = api.get(f"/nodes/{node}/{kind}/{vmid}/config")
        print(json.dumps(proj(cfg, None), indent=2, default=str))
    elif cmd == "storage":
        print(json.dumps(proj(api.get("/storage"), ["storage","type","content","shared","active"]), indent=2, default=str))
    elif cmd == "tasks":
        node = args.command[1]
        rec = api.get(f"/nodes/{node}/tasks")
        rr = rec[: args.limit]
        print(json.dumps(proj(rr, ["upid","type","status"]), indent=2, default=str))
    elif cmd == "node-status":
        node = args.command[1]
        s = api.get(f"/nodes/{node}/status")
        slim = {
            "node": node, "uptime": s.get("uptime"), "cpu": s.get("cpu"),
            "maxcpu": s.get("maxcpu"),
            "mem": s.get("mem"), "maxmem": s.get("maxmem"),
            "disk": s.get("disk"), "maxdisk": s.get("maxdisk"),
        }
        print(json.dumps(slim, indent=2, default=str))
    else:
        sys.exit(f"comando desconocido: {cmd}")


if __name__ == "__main__":
    main()