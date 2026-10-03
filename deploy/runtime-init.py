"""Serialize the shared Docker volume's first-boot initialization."""
import fcntl
import subprocess

with open("/app/data/.runtime-init.lock", "a+b") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    subprocess.run(["/bin/sh", "/app/runtime-init.sh"], check=True)
