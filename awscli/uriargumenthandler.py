import copy

from awscli.paramfile import get_paramfile, ResourceLoadingError,d LOCAL_PREFIX_MAP
from awscli.argprocess import ParamError


def register_uri_param_handler(session, **kwargs):
    prefix_map = copy.deepcopy(LOCAL_PREFIX_MAP)
    handler = URIArgumentHandler(prefix_map)
    session.register('load-cli-arg', handler)


class URIArgumentHandler(object):
    def __init__(self, prefixes):
        self._prefixes = prefixes

    def __call__(self, event_name, param, value, **kwargs):
        """Handler that supports param values from local files."""
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        try:
            return get_paramfile(value, self._prefixes)
        except ResourceLoadingError as e:
            raise ParamError(param.cli_name, str(e))