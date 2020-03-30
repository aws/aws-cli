import contextlib
import os
import platform
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
    if isinstance(cmd, list):
        kwargs['shell'] = False
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


@contextlib.contextmanager
def cd(dirname):
    original = os.getcwd()
    os.chdir(dirname)
    try:
        yield
    finally:
        os.chdir(original)


def bin_path():
    """Get the system's binary path, either `bin` on reasonable systems
    or `Scripts` on Windows.
    """
    path = "bin"

    if platform.system() == "Windows":
        path = "Scripts"

    return path


def virtualenv_enabled():
    # Helper function to see if we need to make
    # our own virtualenv for installs.
    return bool(os.environ.get('VIRTUAL_ENV'))
