"""Drive the CLI on a pseudo-terminal, the way an interactive user does.

prompt_toolkit renders only when stdin and stdout are terminals. Behind a
pipe it stops at its "Input is not a terminal" warning, before most of its
startup runs, so a pipe cannot show whether an interactive command reaches
its first prompt. POSIX-only. Windows has no pseudo-terminal, so this
module imports `termios` only when a session starts, which lets the tests
that drive one load on Windows and skip there.

`run_prompted` drives a getpass-style prompt (the MFA code) instead:
stdin and stderr on the terminal, stdout on a pipe, and the line
discipline's local flags sampled at the prompt and after exit so a test
can show that echo was off while typing and restored afterwards.
"""

import errno
import os
import re
import select
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, NamedTuple

from harness_plugin import command_environment

SESSION_TIMEOUT_SECONDS: Final = 30.0
# How long a getpass-style reader may take to turn echo off after its
# prompt appears, and how often the harness looks.
ECHO_OFF_GRACE_SECONDS: Final = 2.0
ECHO_POLL_SECONDS: Final = 0.01
TERMINAL_SIZE: Final = (24, 80)
READ_SIZE: Final = 65536
EXIT_POLL_SECONDS: Final = 0.01
CTRL_C: Final = b"\x03"
# prompt_toolkit asks for the cursor position when it starts and warns when
# no answer arrives. Answering as a terminal would keeps the render
# deterministic.
CURSOR_POSITION_REQUEST: Final = b"\x1b[6n"
CURSOR_POSITION_REPLY: Final = b"\x1b[1;1R"
# CSI and OSC sequences, character-set selection, and keypad and cursor-save
# modes: everything prompt_toolkit writes that is not text.
ESCAPE_SEQUENCE: Final = re.compile(
    rb"\x1b(?:\[[0-?]*[ -/]*[@-~]"
    rb"|\][^\x07\x1b]*(?:\x07|\x1b\\)"
    rb"|[()][0-9A-Za-z]"
    rb"|[=>78])"
)


@dataclass(frozen=True)
class TerminalStep:
    """Text to wait for on the terminal, and keys to press once it shows."""

    expect: str
    keys: bytes


@dataclass(frozen=True)
class TerminalSession:
    """What an interactive command showed and how it exited."""

    transcript: str
    steps_seen: int
    returncode: int


def interrupt_at_prompt(
    command: Sequence[str],
    env: Mapping[str, str],
    prompt: str,
    timeout: float = SESSION_TIMEOUT_SECONDS,
) -> TerminalSession:
    """Run `command` on a pseudo-terminal and press Ctrl-C at `prompt`.

    prompt_toolkit enters raw mode before it draws, so the Ctrl-C reaches it
    as a key press rather than as a signal.
    """
    return run_on_terminal(
        command, env, [TerminalStep(prompt, CTRL_C)], timeout=timeout
    )


def run_on_terminal(
    command: Sequence[str],
    env: Mapping[str, str],
    steps: Sequence[TerminalStep],
    timeout: float = SESSION_TIMEOUT_SECONDS,
) -> TerminalSession:
    """Run `command` on a pseudo-terminal and type each step's keys in turn.

    Each step's text is matched against the output with escape sequences
    removed. A command that never shows a step's text, or keeps running
    after the last step, is killed at the deadline so a hang fails the test
    instead of stalling the suite.
    """
    import termios

    deadline = time.monotonic() + timeout
    parent_fd, child_fd = os.openpty()
    try:
        termios.tcsetwinsize(child_fd, TERMINAL_SIZE)
        # A new session keeps the child off the caller's controlling
        # terminal, so it reads only what this function writes.
        process = subprocess.Popen(
            command,
            stdin=child_fd,
            stdout=child_fd,
            stderr=child_fd,
            env=command_environment(env),
            start_new_session=True,
        )
    except BaseException:
        os.close(parent_fd)
        raise
    finally:
        os.close(child_fd)
    try:
        output, steps_seen = drive_terminal(parent_fd, steps, deadline)
        wait_for_exit(process, deadline)
    finally:
        os.close(parent_fd)
        # Nothing the command started is wanted once the terminal is
        # closed, even if the command itself has exited.
        kill_process_group(process)
    return TerminalSession(
        transcript=visible_text(output),
        steps_seen=steps_seen,
        returncode=process.returncode,
    )


def drive_terminal(
    parent_fd: int, steps: Sequence[TerminalStep], deadline: float
) -> tuple[bytes, int]:
    """Read until the child closes the terminal or the deadline passes.

    Answers every cursor position request and types each step's keys once,
    the first time its text is visible. A step's text is looked for only in
    output that arrived after the previous step's keys, so what the
    terminal showed earlier, such as the echo of typed keys, cannot satisfy
    it. Returns the raw output and how many steps' text was seen.
    """
    output = bytearray()
    replies_sent = 0
    steps_seen = 0
    search_start = 0
    while (remaining := deadline - time.monotonic()) > 0:
        readable, _, _ = select.select([parent_fd], [], [], remaining)
        if not readable:
            break
        chunk = read_terminal(parent_fd)
        if not chunk:
            break
        output += chunk
        # Counting over the whole output catches a request split across
        # reads.
        requests = output.count(CURSOR_POSITION_REQUEST)
        if requests > replies_sent:
            os.write(
                parent_fd, CURSOR_POSITION_REPLY * (requests - replies_sent)
            )
            replies_sent = requests
        if steps_seen < len(steps):
            step = steps[steps_seen]
            if step.expect in visible_text(output[search_start:]):
                os.write(parent_fd, step.keys)
                steps_seen += 1
                search_start = len(output)
    return bytes(output), steps_seen


def read_terminal(parent_fd: int) -> bytes:
    """The child's next output, or b"" once it has closed the terminal."""
    try:
        return os.read(parent_fd, READ_SIZE)
    except OSError as error:
        # Linux reports a terminal whose child side is closed with EIO
        # rather than end of file.
        if error.errno == errno.EIO:
            return b""
        raise


def wait_for_exit(process: subprocess.Popen[bytes], deadline: float) -> None:
    """Wait for the command to exit or the deadline to pass.

    An exited command is left unreaped for `kill_process_group`.
    """
    options = os.WEXITED | os.WNOHANG | os.WNOWAIT
    while os.waitid(os.P_PID, process.pid, options) is None:
        if time.monotonic() >= deadline:
            return
        time.sleep(EXIT_POLL_SECONDS)


def kill_process_group(process: subprocess.Popen[bytes]) -> None:
    """Kill the command and whatever it started, then reap the command.

    The command leads a session of its own, so anything it started that may
    still hold the terminal shares its process group, which lasts until its
    last member exits even if the command already has. Reaping only after
    the signal keeps the command's process ID, which names the group, from
    being reused in between.
    """
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        # Nothing in the group is left to kill. macOS reports EPERM rather
        # than ESRCH when every process left in the group has exited and
        # awaits reaping, as the command does after `wait_for_exit`.
        pass
    process.wait()


def visible_text(output: bytes | bytearray) -> str:
    """Output with escape sequences removed, decoded for matching."""
    return ESCAPE_SEQUENCE.sub(b"", output).decode("utf-8", errors="replace")


# Makes the terminal on fd 0 the controlling terminal of the new session,
# then execs the command in place (argv[1] must be a path). An exec
# launcher rather than preexec_fn, which is unsafe in a threaded parent
# (these helpers run under asyncio.to_thread). With a controlling terminal
# getpass opens /dev/tty, and Ctrl-C typed on the terminal raises SIGINT.
CONTROLLING_TERMINAL_LAUNCHER: Final = (
    sys.executable,
    "-c",
    "import fcntl, os, sys, termios; "
    "fcntl.ioctl(0, termios.TIOCSCTTY, 0); "
    "os.execv(sys.argv[1], sys.argv[1:])",
)

# What to do when the prompt has appeared once more: called with the
# terminal's controller fd and the child's pid.
PromptAction = Callable[[int, int], None]


class PromptOutcome(NamedTuple):
    """What a prompted command showed and how it exited.

    `transcript` is every byte read from the terminal (the child's stderr,
    or /dev/tty, plus the line discipline's echo). The local-flag samples
    are None if the prompt never appeared or the terminal could not be
    queried.
    """

    transcript: bytes
    stdout: bytes
    returncode: int
    lflag_at_prompt: int | None
    lflag_after_exit: int | None


def run_prompted(
    command: Sequence[str],
    env: Mapping[str, str],
    prompt: str,
    actions: Sequence[PromptAction],
    *,
    cwd: Path,
    ctty: bool = False,
    launcher: Sequence[str] = (),
    timeout: float = SESSION_TIMEOUT_SECONDS,
) -> PromptOutcome:
    """Run `command` with stdin and stderr on a terminal, stdout piped.

    Runs `actions[i]` when `prompt` has appeared `i + 1` times, and keeps
    draining the terminal and the pipe until both close: an exiting
    session leader on macOS waits until its queued terminal output is
    read. The child gets a new session, so it never touches the caller's
    terminal, and is killed with its process group at the deadline.
    """
    import termios

    deadline = time.monotonic() + timeout
    argv = [
        *(CONTROLLING_TERMINAL_LAUNCHER if ctty else ()),
        *launcher,
        *command,
    ]
    controller_fd, terminal_fd = os.openpty()
    try:
        termios.tcsetwinsize(terminal_fd, TERMINAL_SIZE)
        process = subprocess.Popen(
            argv,
            stdin=terminal_fd,
            stdout=subprocess.PIPE,
            stderr=terminal_fd,
            env=command_environment(env),
            cwd=cwd,
            start_new_session=True,
        )
    except BaseException:
        os.close(controller_fd)
        raise
    finally:
        os.close(terminal_fd)
    try:
        transcript, stdout, lflag_at_prompt = drive_prompts(
            process, controller_fd, prompt.encode("utf-8"), actions, deadline
        )
        returncode = wait_for_session_exit(process, deadline)
        lflag_after_exit = local_flags(controller_fd)
    finally:
        # If driving the session raised, the child may still run: kill and
        # reap it, as interrupt_at_prompt does, so no zombie is left.
        os.close(controller_fd)
        if process.poll() is None:
            kill_session(process)
            process.wait()
        if process.stdout is not None:
            process.stdout.close()
    return PromptOutcome(
        transcript=transcript,
        stdout=stdout,
        returncode=returncode,
        lflag_at_prompt=lflag_at_prompt,
        lflag_after_exit=lflag_after_exit,
    )


def drive_prompts(
    process: subprocess.Popen[bytes],
    controller_fd: int,
    prompt: bytes,
    actions: Sequence[PromptAction],
    deadline: float,
) -> tuple[bytes, bytes, int | None]:
    """Read the terminal and stdout until both close or the deadline.

    Returns (terminal bytes, stdout bytes, local flags when the prompt
    first appeared). The flags are sampled before the first action, so
    they show the state the prompt set, not the restored one; a reader
    may print its prompt before it turns echo off, so the sample and the
    first action wait up to ECHO_OFF_GRACE_SECONDS for ECHO to clear.
    """
    assert process.stdout is not None
    stdout_fd = process.stdout.fileno()
    transcript = bytearray()
    stdout = bytearray()
    open_fds = [controller_fd, stdout_fd]
    performed = 0
    lflag_at_prompt: int | None = None
    while open_fds and (remaining := deadline - time.monotonic()) > 0:
        readable, _, _ = select.select(open_fds, [], [], remaining)
        if not readable:
            break
        for fd in readable:
            chunk = read_terminal(fd)
            if not chunk:
                open_fds.remove(fd)
            elif fd == controller_fd:
                transcript += chunk
            else:
                stdout += chunk
        # Counting over the whole transcript catches a prompt split
        # across reads.
        seen = transcript.count(prompt)
        if seen and lflag_at_prompt is None:
            lflag_at_prompt = flags_once_echo_off(controller_fd, deadline)
        while performed < min(seen, len(actions)):
            actions[performed](controller_fd, process.pid)
            performed += 1
    return bytes(transcript), bytes(stdout), lflag_at_prompt


def flags_once_echo_off(controller_fd: int, deadline: float) -> int | None:
    """The local flags once ECHO is clear, or after the grace period."""
    import termios

    limit = min(deadline, time.monotonic() + ECHO_OFF_GRACE_SECONDS)
    while True:
        flags = local_flags(controller_fd)
        if flags is None or not flags & termios.ECHO:
            return flags
        if time.monotonic() >= limit:
            return flags
        time.sleep(ECHO_POLL_SECONDS)


def local_flags(controller_fd: int) -> int | None:
    """The terminal's c_lflag, read through the controller side.

    The controller still answers after the child has exited (and after a
    session leader's exit revoked the terminal side), so it reports what
    the child left behind.
    """
    import termios

    try:
        return termios.tcgetattr(controller_fd)[3]
    except termios.error:
        return None


def wait_for_session_exit(
    process: subprocess.Popen[bytes], deadline: float
) -> int:
    """The exit status, killing the process group past the deadline."""
    try:
        return process.wait(timeout=max(deadline - time.monotonic(), 0))
    except subprocess.TimeoutExpired:
        kill_session(process)
        return process.wait()


def kill_session(process: subprocess.Popen[bytes]) -> None:
    """SIGKILL the process group the child leads (start_new_session)."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        process.kill()
