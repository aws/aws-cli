from awscli.testutils import mock, unittest

from awscli.uriargumenthandler import register_uri_param_handler
from botocore.session import Session


class TestConfigureURIArgumentHandler(unittest.TestCase):

    @mock.patch('awscli.paramfile.URIArgumentHandler')
    def test_default_prefix_maps(self, mock_handler_cls):
        session = mock.Mock(spec=Session)
        session.get_scoped_config.return_value = {}

        register_uri_param_handler(session)
        cases = mock_handler_cls.call_args[0][0]

        self.assertIn('file://', cases)
        self.assertIn('fileb://', cases)