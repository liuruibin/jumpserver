#!/usr/bin/env python
#
import os
import sys
import signal
import subprocess

import redis_lock
from redis import Redis

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS_DIR = os.path.join(BASE_DIR, 'apps')

sys.path.insert(0, BASE_DIR)
sys.path.insert(0, APPS_DIR)
from apps.jumpserver.const import CONFIG
from apps.jumpserver.settings import base as jms_settings

os.environ.setdefault('PYTHONOPTIMIZE', '1')
if os.getuid() == 0:
    os.environ.setdefault('C_FORCE_ROOT', '1')

params = {
    'host': CONFIG.REDIS_HOST,
    'port': CONFIG.REDIS_PORT,
    'password': CONFIG.REDIS_PASSWORD,
    "ssl": CONFIG.REDIS_USE_SSL,
    'ssl_cert_reqs': CONFIG.REDIS_SSL_REQUIRED,
    "ssl_keyfile": jms_settings.REDIS_SSL_KEYFILE,
    "ssl_certfile": jms_settings.REDIS_SSL_CERTFILE,
    "ssl_ca_certs": jms_settings.REDIS_SSL_CA_CERTS
}
redis = Redis(**params)
scheduler = "django_celery_beat.schedulers:DatabaseScheduler"

cmd = [
    'celery',
    '-A', 'ops',
    'beat',
    '-l', 'INFO',
    '--scheduler', scheduler,
    '--max-interval', '60'
]

processes = []


def stop_beat_process(sig, frame):
    for p in processes:
        os.kill(p.pid, 15)


def main():
    # 父进程结束通知子进程结束
    signal.signal(signal.SIGTERM, stop_beat_process)

    with redis_lock.Lock(redis, name="beat-distribute-start-lock", expire=60, auto_renewal=True):
        print("Get beat lock start to run it")
        process = subprocess.Popen(cmd, cwd=APPS_DIR)
        processes.append(process)
        process.wait()


if __name__ == '__main__':
    main()
