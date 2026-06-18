import json

import pytest

from botocore.config import Config
from botocore.exceptions import InvalidEndpointConfigurationError
from tests import BaseSessionTest, ClientHTTPStubber, requires_crt


class TestClientEvents(BaseSessionTest):
    def setUp(self):
        super().setUp()
        self.region = "us-east-1"

    def create_eventbridge_client(self, region=None, **kwargs):
        if region is None:
            region = self.region
        client = self.session.create_client("events", region, **kwargs)
        return client

    def create_stubbed_eventbridge_client(
        self, with_default_responses=False, **kwargs
    ):
        client = self.create_eventbridge_client(**kwargs)
        http_stubber = ClientHTTPStubber(client)
        http_stubber.start()
        if with_default_responses:
            http_stubber.add_response()
            http_stubber.add_response()
        return client, http_stubber

    def _default_put_events_args(self):
        return {
            "Entries": [
                {
                    "Source": "test",
                    "Resources": [
                        "resource",
                    ],
                    "DetailType": "my-detail",
                    "Detail": "detail",
                    "EventBusName": "my-bus",
                },
            ]
        }

    def _assert_multi_region_endpoint(self, request, endpoint_id, suffix=None):
        if suffix is None:
            suffix = "amazonaws.com"
        assert (
            request.url == f"https://{endpoint_id}.endpoint.events.{suffix}/"
        )

    def _assert_sigv4a_headers(self, request):
        assert request.headers["x-amz-region-set"] == b"*"
        assert request.headers["authorization"].startswith(
            b"AWS4-ECDSA-P256-SHA256 Credential="
        )

    def _assert_params_in_body(self, request, params):
        assert len(params) > 0
        body = json.loads(request.body)
        for key, value in params:
            assert body[key] == value

    def test_put_event_default_endpoint(self):
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True,
        )
        with stubber:
            client.put_events(**self._default_put_events_args())
        assert (
            stubber.requests[0].url
            == "https://events.us-east-1.amazonaws.com/"
        )
        assert b"EndpointId" not in stubber.requests[0].body

    def test_put_event_default_endpoint_explicit_configs(self):
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True,
            config=Config(
                use_dualstack_endpoint=False,
                use_fips_endpoint=False,
            ),
        )
        with stubber:
            client.put_events(**self._default_put_events_args())
        assert (
            stubber.requests[0].url
            == "https://events.us-east-1.amazonaws.com/"
        )
        assert b"EndpointId" not in stubber.requests[0].body

    @requires_crt()
    def test_put_event_endpoint_id(self):
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True,
        )
        default_args = self._default_put_events_args()
        endpoint_id = "abc123.456def"

        with stubber:
            client.put_events(EndpointId=endpoint_id, **default_args)

        self._assert_params_in_body(
            stubber.requests[0],
            [
                ("EndpointId", endpoint_id),
            ],
        )
        self._assert_multi_region_endpoint(stubber.requests[0], endpoint_id)
        self._assert_sigv4a_headers(stubber.requests[0])

    @requires_crt()
    def test_put_event_endpoint_id_explicit_config(self):
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True,
            config=Config(
                use_dualstack_endpoint=False,
                use_fips_endpoint=False,
            ),
        )
        default_args = self._default_put_events_args()
        endpoint_id = "abc123.456def"

        with stubber:
            client.put_events(EndpointId=endpoint_id, **default_args)

        self._assert_params_in_body(
            stubber.requests[0],
            [
                ("EndpointId", endpoint_id),
            ],
        )
        self._assert_multi_region_endpoint(stubber.requests[0], endpoint_id)
        self._assert_sigv4a_headers(stubber.requests[0])

    @requires_crt()
    def test_put_event_bad_endpoint_id(self):
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True,
        )
        default_args = self._default_put_events_args()
        endpoint_id = "badactor.com?foo=bar"

        with pytest.raises(InvalidEndpointConfigurationError):
            client.put_events(EndpointId=endpoint_id, **default_args)

    @requires_crt()
    def test_put_event_bad_endpoint_id_explicit_config(self):
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True,
            config=Config(
                use_dualstack_endpoint=False,
                use_fips_endpoint=False,
            ),
        )
        default_args = self._default_put_events_args()
        endpoint_id = "badactor.com?foo=bar"

        with pytest.raises(InvalidEndpointConfigurationError):
            client.put_events(EndpointId=endpoint_id, **default_args)

    @requires_crt()
    def test_put_event_empty_endpoint_id(self):
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True,
        )
        default_args = self._default_put_events_args()
        endpoint_id = ""

        with pytest.raises(InvalidEndpointConfigurationError):
            client.put_events(EndpointId=endpoint_id, **default_args)

    @requires_crt()
    def test_put_event_empty_endpoint_id_explicit_config(self):
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True,
            config=Config(
                use_dualstack_endpoint=False,
                use_fips_endpoint=False,
            ),
        )
        default_args = self._default_put_events_args()
        endpoint_id = ""

        with pytest.raises(InvalidEndpointConfigurationError):
            client.put_events(EndpointId=endpoint_id, **default_args)

    def test_put_event_default_dualstack_endpoint(self):
        config = Config(use_dualstack_endpoint=True, use_fips_endpoint=False)
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True, config=config
        )
        default_args = self._default_put_events_args()

        with stubber:
            client.put_events(**default_args)
        assert stubber.requests[0].url == "https://events.us-east-1.api.aws/"

    @requires_crt()
    def test_put_events_endpoint_id_dualstack(self):
        config = Config(use_dualstack_endpoint=True, use_fips_endpoint=False)
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True, config=config
        )
        default_args = self._default_put_events_args()
        endpoint_id = "abc123.456def"

        with stubber:
            client.put_events(EndpointId=endpoint_id, **default_args)

        self._assert_params_in_body(
            stubber.requests[0],
            [
                ("EndpointId", endpoint_id),
            ],
        )
        self._assert_multi_region_endpoint(
            stubber.requests[0], endpoint_id, suffix="api.aws"
        )
        self._assert_sigv4a_headers(stubber.requests[0])

    def test_put_events_default_fips_endpoint(self):
        config = Config(use_dualstack_endpoint=False, use_fips_endpoint=True)
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True, config=config
        )
        default_args = self._default_put_events_args()

        with stubber:
            client.put_events(**default_args)
        assert (
            stubber.requests[0].url
            == "https://events-fips.us-east-1.amazonaws.com/"
        )

    @requires_crt()
    def test_put_events_endpoint_id_fips(self):
        config = Config(use_dualstack_endpoint=False, use_fips_endpoint=True)
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True, config=config
        )
        default_args = self._default_put_events_args()
        endpoint_id = "abc123.456def"

        with pytest.raises(InvalidEndpointConfigurationError):
            client.put_events(EndpointId=endpoint_id, **default_args)

    def test_put_events_default_dualstack_fips_endpoint(self):
        config = Config(use_dualstack_endpoint=True, use_fips_endpoint=True)
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True, config=config
        )
        default_args = self._default_put_events_args()

        with stubber:
            client.put_events(**default_args)
        assert (
            stubber.requests[0].url == "https://events-fips.us-east-1.api.aws/"
        )

    @requires_crt()
    def test_put_events_endpoint_id_dualstack_fips(self):
        config = Config(use_dualstack_endpoint=True, use_fips_endpoint=True)
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True, config=config
        )
        default_args = self._default_put_events_args()
        endpoint_id = "abc123.456def"

        with pytest.raises(InvalidEndpointConfigurationError) as e:
            client.put_events(EndpointId=endpoint_id, **default_args)
        assert (
            "FIPS is not supported with EventBridge multi-region endpoints"
            in str(e.value)
        )

    def test_put_events_default_gov_endpoint(self):
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True,
            region="us-iso-east-1",
        )
        default_args = self._default_put_events_args()

        with stubber:
            client.put_events(**default_args)
        assert (
            stubber.requests[0].url
            == "https://events.us-iso-east-1.c2s.ic.gov/"
        )

    @requires_crt()
    def test_put_events_endpoint_id_gov(self):
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True,
            region="us-iso-east-1",
        )
        default_args = self._default_put_events_args()
        endpoint_id = "abc123.456def"

        with stubber:
            client.put_events(EndpointId=endpoint_id, **default_args)

        self._assert_params_in_body(
            stubber.requests[0],
            [
                ("EndpointId", endpoint_id),
            ],
        )
        self._assert_multi_region_endpoint(
            stubber.requests[0], endpoint_id, suffix="c2s.ic.gov"
        )
        self._assert_sigv4a_headers(stubber.requests[0])

    def test_put_events_default_custom_endpoint(self):
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True, endpoint_url="https://example.org"
        )
        default_args = self._default_put_events_args()

        with stubber:
            client.put_events(**default_args)
        assert stubber.requests[0].url == "https://example.org/"

    @requires_crt()
    def test_put_events_endpoint_id_custom(self):
        client, stubber = self.create_stubbed_eventbridge_client(
            with_default_responses=True, endpoint_url="https://example.org"
        )
        default_args = self._default_put_events_args()
        endpoint_id = "abc123.456def"

        with stubber:
            client.put_events(EndpointId=endpoint_id, **default_args)

        self._assert_params_in_body(
            stubber.requests[0],
            [
                ("EndpointId", endpoint_id),
            ],
        )
        assert stubber.requests[0].url == "https://example.org/"
        self._assert_sigv4a_headers(stubber.requests[0])
