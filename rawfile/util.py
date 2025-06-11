import base64
import functools
import inspect
import pickle
import subprocess
import time


def indent(obj, lvl):
    return "\n".join([(lvl * " ") + line for line in str(obj).splitlines()])


def fmt_timestamp(ts):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def log_grpc_request(func):
    @functools.wraps(func)
    def wrap(self, request, context):
        start = time.time()
        try:
            res = func(self, request, context)
            end = time.time()
            print(
                f"""{fmt_timestamp(end)} => {func.__name__}({{
{indent(request, 2)}
}}) = {{
{indent(res, 2)}
}} <= {fmt_timestamp(end)} // {(end - start) * 1000:.2f}ms"""
            )
            return res
        except Exception as exc:
            ret = (str(context._state.code), context._state.details)
            end = time.time()
            print(
                f"""{fmt_timestamp(end)} => {func.__name__}({{
{indent(request, 2)}
}}) = {ret} <= {fmt_timestamp(end)} // {(end - start) * 1000:.2f}ms
"""
            )
            raise exc

    return wrap


def run(cmd, check=True):
    return subprocess.run(cmd, shell=True, check=check)


def run_out(cmd: str, check=False):
    p = subprocess.run(cmd, shell=True, check=check, capture_output=True)
    return p


class remote_fn(object):
    def __init__(self, fn):
        self.fn = fn

    def as_cmd(self, *args, **kwargs):
        call_data = [inspect.getsource(self.fn).encode(), args, kwargs]
        call_data_serialized = base64.b64encode(pickle.dumps(call_data))

        run_cmd = f"""
python <<EOF
import base64
import pickle

remote_fn = lambda fn: fn # FIXME: dirty hack
call_data = pickle.loads(base64.b64decode({call_data_serialized}))
exec(call_data[0])
{self.fn.__name__}(*call_data[1], **call_data[2])
EOF
        """
        return run_cmd

    def __call__(self, *args, **kwargs):
        raise Exception("Should only be run inside pod")
