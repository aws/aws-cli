import contextlib
import os
import shutil
import sys
import subprocess
import tempfile
import zipfile

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


def extract_zip(zipfile_name, target_dir):
    with zipfile.ZipFile(zipfile_name, 'r') as zf:
        for zf_info in zf.infolist():
            # Works around extractall not preserving file permissions:
            # https://bugs.python.org/issue15795
            extracted_path = zf.extract(zf_info, target_dir)
            os.chmod(extracted_path, zf_info.external_attr >> 16)


@contextlib.contextmanager
def tmp_dir():
    dirname = tempfile.mkdtemp()
    try:
        yield dirname
    finally:
        shutil.rmtree(dirname)
