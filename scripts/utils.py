import sys
import subprocess


class BadRCError(Exception):
    pass


def run(cmd, cwd=None, env=None, echo=True):
    if echo:
        sys.stdout.write("Running cmd: %s\n" % cmd)
    kwargs = {
        'shell': True,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
    }
    if cwd is not None:
        kwargs['cwd'] = cwd
    if env is not None:
        kwargs['env'] = env
    p = subprocess.Popen(cmd, **kwargs)
    stdout, stderr = p.communicate()
    output = stdout.decode('utf-8') + stderr.decode('utf-8')
    if p.returncode != 0:
        raise BadRCError("Bad rc (%s) for cmd '%s': %s" % (
            p.returncode, cmd, output))
    return output
