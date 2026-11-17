"""Minimal fallback entry point for a distro-provided AWS CLI package."""

import sys

from awscli import clidriver
from awscli.utils import add_metadata_component_to_user_agent_extra

# The version the host names itself by and the md/ components it adds to
# every request's User-Agent, which the runner publishes and runtime.py sets
# as this does.
_user_agent_version = sys._zippy_user_agent_version
del sys._zippy_user_agent_version
_user_agent_metadata = sys._zippy_user_agent_metadata
del sys._zippy_user_agent_metadata
_set_user_agent_for_session = clidriver._set_user_agent_for_session


def _set_host_user_agent(session):
    _set_user_agent_for_session(session)
    if _user_agent_version is not None:
        session.user_agent_version = _user_agent_version
    for name, value in _user_agent_metadata:
        add_metadata_component_to_user_agent_extra(session, name, value)


clidriver._set_user_agent_for_session = _set_host_user_agent

sys.exit(clidriver.main())
