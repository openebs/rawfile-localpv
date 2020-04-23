import functools
import subprocess


def indent(obj, lvl):
    return "\n".join([(lvl * " ") + line for line in str(obj).splitlines()])


def log_grpc_request(func):
    @functools.wraps(func)
    def wrap(self, request, context):
        res = func(self, request, context)
        print(
            f"""{func.__name__}({{
{indent(request, 2)}
}}) = {{
{indent(res, 2)}
}}"""
        )
        return res

    return wrap


def run(cmd):
    return subprocess.run(cmd, shell=True, check=True)
