import time
from datetime import datetime, timedelta, timezone

import humanize
from orchestrator.k8s import read_config_map, write_config_map
from utils.logs import fmt_exception, logger

from .usage import Usage

time_fmt = "%Y-%m-%dT%H:%M:%S.%fZ"


class Ping:
    def __init__(self, usage: Usage, ping_delta: timedelta):
        self.configmap = "rawfile-config"
        self.install_ts_key = "install-ts"
        self.ping_ts_key = "last-ping-ts"
        self.installed = False
        self.install_ts = None
        self.ping_ts = None
        self.ping_delta = ping_delta
        self.usage = usage

    def refresh(self):
        self.usage.refresh()

    def run(self):
        record_ping = False

        while True:
            try:
                # becomes a no-op after the install
                self.ping_ts = self.send_install_once()

                if record_ping:
                    # write last ping ts to configmap, allowing us to stay accurate even across restarts
                    write_config_map(
                        self.configmap, self.ping_ts_key, self.ping_ts, overwrite=True
                    )
                    record_ping = False

                self.usage.refresh()
                self.ping_ts = wait_ping(self.ping_ts, self.ping_delta)
                self.usage.send_ping()
                record_ping = True
            except Exception as e:
                logger.error("Analytics Error", exception=fmt_exception(e))
                # todo: add backoff ramp up
                time.sleep(60 * 60)

    def send_install_once(self):
        if self.ping_ts:
            return self.ping_ts

        # todo: install another config_map via helm which is cleaned up on uninstall
        # this would allow us to track reinstalls which was a metrics which had been previously
        # questioned by the CNCF in another engine
        data = read_config_map(self.configmap)

        if self.install_ts_key in data:
            self.install_ts = data[self.install_ts_key]
            self.installed = True

            # Ping starts 24h post install
            if self.ping_ts_key in data:
                self.ping_ts = data[self.ping_ts_key]
            else:
                self.ping_ts = self.install_ts

            return self.ping_ts

        if self.install_ts is None:
            # this is the first time running after install, set ts and record it in the cm
            self.install_ts = now_to_str()

        if not self.installed:
            self.usage.send_install()
            self.installed = True

        write_config_map(self.configmap, self.install_ts_key, self.install_ts)
        # After we've sent the install event, and written it to the cm, we can now start the ping
        return self.install_ts


def time_to_str(tm) -> str:
    return tm.strftime(time_fmt)


def now_to_str() -> str:
    return datetime.now(timezone.utc).strftime(time_fmt)


# start_ts_utc is a timestamp in the format returned by time_utc
def wait_ping(last_ts: str, interval: timedelta):
    # parse the formatted ts string into a datetime
    install_time = datetime.strptime(last_ts, time_fmt).replace(tzinfo=timezone.utc)

    # Next ping is added on top of the last one
    target_time = install_time + interval

    now = datetime.now(timezone.utc)
    wait = target_time - now
    wait_seconds = wait.total_seconds()
    if wait_seconds > 0:
        logger.trace(
            f"Waiting {humanize.precisedelta(wait)} till the next ping",
            install_time=install_time,
            target_time=target_time,
        )
        time.sleep(wait_seconds)
        return time_to_str(target_time)
    else:
        return time_to_str(now)
