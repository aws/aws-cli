# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""Unit tests for the shared read-only call bridge / emitter (helpers)."""

import io
from types import SimpleNamespace

import pytest
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
)
from botocore.exceptions import (
    ConnectionError as BotoConnectionError,
)

from awscli.customizations.exceptions import ParamValidationError
from awscli.customizations.compositereadonly import helpers


class FakeClient:
    """A botocore-shaped client whose methods return or raise on demand."""

    def __init__(self):
        self._returns = {}
        self._raises = {}
        self.calls = []

    def set_return(self, method, value):
        self._returns[method] = value

    def set_raise(self, method, exc):
        self._raises[method] = exc

    def __getattr__(self, method):
        # __getattr__ only fires for names not found normally, so the private
        # attributes above are untouched.
        def _call(**params):
            self.calls.append((method, params))
            if method in self._raises:
                raise self._raises[method]
            return self._returns.get(method, {"ok_marker": method})

        return _call


def _client_error(code, status=400, message="boom"):
    return ClientError(
        {
            "Error": {"Code": code, "Message": message},
            "ResponseMetadata": {"HTTPStatusCode": status},
        },
        "GetThing",
    )


def _parsed_globals(output="json", query=None):
    return SimpleNamespace(output=output, query=query)


# ------------------------------------------------------------- assert_read_only


def test_assert_read_only_allows_read_verbs():
    # None of these should raise; read/lifecycle verbs are permitted.
    for op in (
        "GetThing",
        "DescribeThing",
        "ListThings",
        "StartQuery",
        "StopQuery",
        "GetQueryResults",
    ):
        helpers.assert_read_only(op)


def test_assert_read_only_refuses_mutations():
    for op in (
        "CreateThing",
        "DeleteThing",
        "PutObject",
        "UpdateStack",
        "TerminateInstances",
        "RunInstances",
    ):
        with pytest.raises(helpers.ReadOnlyViolation):
            helpers.assert_read_only(op)


def test_assert_read_only_exact_verb_name_is_refused():
    # The verb alone (no suffix) is still a mutation.
    with pytest.raises(helpers.ReadOnlyViolation):
        helpers.assert_read_only("Create")


def test_assert_read_only_respects_word_boundary():
    # "Created"/"Setting" start with a mutating prefix but the next char is
    # lower-case, so they are NOT mistaken for Create/Set mutations.
    helpers.assert_read_only("Createcountry")
    helpers.assert_read_only("Setting")
    helpers.assert_read_only("Removalist")


# ------------------------------------------------------------- result factories


def test_ok_result_shape():
    r = helpers.ok_result(
        {"a": 1}, is_exhaustive=True, guidance=["g"], key="k"
    )
    assert r["ok"] is True
    assert r["value"] == {"a": 1}
    assert r["is_exhaustive"] is True
    assert r["guidance"] == ["g"]
    assert r["key"] == "k"


def test_err_result_marks_retriable_codes():
    # THROTTLED is in the retriable set, so retriable is True even unset.
    r = helpers.err_result(helpers.THROTTLED, "slow down")
    assert r["ok"] is False
    assert r["retriable"] is True
    # A non-retriable code stays non-retriable unless forced.
    r2 = helpers.err_result(helpers.NOT_FOUND, "missing")
    assert r2["retriable"] is False
    r3 = helpers.err_result(helpers.NOT_FOUND, "missing", retriable=True)
    assert r3["retriable"] is True


def test_invalid_input_flags_param_error():
    r = helpers.invalid_input("bad", ["fix it"], value={"x": 1})
    assert r["code"] == helpers.INVALID_INPUT
    assert r["param_error"] is True
    assert r["value"] == {"x": 1}


# --------------------------------------------------------------- _map_client_error


def test_map_client_error_known_code():
    code, aws_code = helpers._map_client_error(
        _client_error("AccessDenied", status=403)
    )
    assert code == helpers.PERMISSION_DENIED
    assert aws_code == "AccessDenied"


def test_map_client_error_status_fallbacks():
    cases = {
        404: helpers.NOT_FOUND,
        401: helpers.PERMISSION_DENIED,
        403: helpers.PERMISSION_DENIED,
        429: helpers.THROTTLED,
        500: helpers.SERVICE_ERROR,
        503: helpers.SERVICE_ERROR,
    }
    for status, expected in cases.items():
        code, aws_code = helpers._map_client_error(
            _client_error("UnmappedCode", status=status)
        )
        assert code == expected, status
        assert aws_code == "UnmappedCode"


def test_map_client_error_unknown_status_is_service_error():
    code, _ = helpers._map_client_error(
        _client_error("UnmappedCode", status=418)
    )
    assert code == helpers.SERVICE_ERROR


# --------------------------------------------------------------------- call()


def test_call_refuses_mutation_before_dispatch():
    client = FakeClient()
    with pytest.raises(helpers.ReadOnlyViolation):
        helpers.call(client, "CreateThing", {})
    # The mutation guard runs before any client method is touched.
    assert client.calls == []


def test_call_success_returns_ok_result():
    client = FakeClient()
    client.set_return("get_thing", {"Thing": "ok"})
    r = helpers.call(client, "GetThing", {"Id": "x"})
    assert r["ok"] is True
    assert r["value"] == {"Thing": "ok"}
    # Operation name was xform'd and params forwarded verbatim.
    assert client.calls == [("get_thing", {"Id": "x"})]


def test_call_client_error_is_mapped():
    client = FakeClient()
    client.set_raise("get_thing", _client_error("ThrottlingException", 429))
    r = helpers.call(client, "GetThing", {})
    assert r["ok"] is False
    assert r["code"] == helpers.THROTTLED
    assert r["retriable"] is True
    assert r["aws_code"] == "ThrottlingException"


def test_call_no_credentials():
    client = FakeClient()
    client.set_raise("get_thing", NoCredentialsError())
    r = helpers.call(client, "GetThing", {})
    assert r["code"] == helpers.CREDENTIALS_EXPIRED
    assert r["retriable"] is True


def test_call_endpoint_connection_error_is_network():
    client = FakeClient()
    client.set_raise(
        "get_thing", EndpointConnectionError(endpoint_url="https://x")
    )
    r = helpers.call(client, "GetThing", {})
    assert r["code"] == helpers.NETWORK_ERROR
    assert r["retriable"] is True


def test_call_connection_error_is_network():
    client = FakeClient()
    client.set_raise("get_thing", BotoConnectionError(error="reset"))
    r = helpers.call(client, "GetThing", {})
    assert r["code"] == helpers.NETWORK_ERROR


def test_call_botocore_error_is_service_error():
    client = FakeClient()
    client.set_raise("get_thing", BotoCoreError())
    r = helpers.call(client, "GetThing", {})
    assert r["code"] == helpers.SERVICE_ERROR
    assert r["retriable"] is False


# --------------------------------------------------------------- _render_payload


def test_render_payload_dict_value_folds_in_flags():
    result = helpers.ok_result(
        {"rows": []}, is_exhaustive=True, guidance=["g1"]
    )
    payload = helpers._render_payload(result)
    assert payload["rows"] == []
    assert payload["is_exhaustive"] is True
    assert payload["guidance"] == ["g1"]


def test_render_payload_scalar_value_wrapped():
    payload = helpers._render_payload(helpers.ok_result(42))
    assert payload == {"result": 42}


def test_render_payload_none_value_is_empty_dict():
    payload = helpers._render_payload(helpers.ok_result(None))
    assert payload == {}


def test_render_payload_failure_includes_error_and_retriable():
    result = helpers.err_result(
        helpers.THROTTLED, "slow", value={"partial": True}
    )
    payload = helpers._render_payload(result)
    assert payload["partial"] is True
    assert payload["error"] == "slow"
    assert payload["code"] == helpers.THROTTLED
    assert payload["retriable"] is True


def test_render_payload_does_not_override_existing_value_keys():
    # When value already carries error/code, _render_payload must not clobber.
    result = helpers.err_result(
        helpers.NOT_FOUND, "outer", value={"error": "inner", "code": "INNER"}
    )
    payload = helpers._render_payload(result)
    assert payload["error"] == "inner"
    assert payload["code"] == "INNER"


# ------------------------------------------------------------------ emit_result


def test_emit_result_success_writes_payload_rc0():
    out, err = io.StringIO(), io.StringIO()
    result = helpers.ok_result({"rows": [1, 2]})
    rc = helpers.emit_result(
        "x", result, _parsed_globals(), session=None, stdout=out, stderr=err
    )
    assert rc == helpers.RC_SUCCESS
    assert '"rows"' in out.getvalue()
    assert err.getvalue() == ""


def test_emit_result_operational_failure_rc255_and_stderr():
    out, err = io.StringIO(), io.StringIO()
    result = helpers.err_result(helpers.NOT_FOUND, "missing thing")
    rc = helpers.emit_result(
        "x", result, _parsed_globals(), session=None, stdout=out, stderr=err
    )
    assert rc == helpers.RC_OPERATIONAL_ERROR
    # Payload still printed to stdout so --query keeps working.
    assert "NOT_FOUND" in err.getvalue()
    assert "missing thing" in err.getvalue()


def test_emit_result_param_error_raises_param_validation():
    result = helpers.invalid_input("bad flag")
    with pytest.raises(ParamValidationError):
        helpers.emit_result(
            "x",
            result,
            _parsed_globals(),
            session=None,
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )


def test_emit_result_output_falls_back_to_session_config():
    # parsed_globals.output is None -> read from session config variable.
    out = io.StringIO()
    session = SimpleNamespace(
        get_config_variable=lambda name: "json" if name == "output" else None
    )
    result = helpers.ok_result({"k": "v"})
    rc = helpers.emit_result(
        "x",
        result,
        _parsed_globals(output=None),
        session=session,
        stdout=out,
        stderr=io.StringIO(),
    )
    assert rc == helpers.RC_SUCCESS
    assert '"k"' in out.getvalue()


def test_emit_result_defaults_to_std_streams(monkeypatch):
    captured_out = io.StringIO()
    captured_err = io.StringIO()
    monkeypatch.setattr(helpers.sys, "stdout", captured_out)
    monkeypatch.setattr(helpers.sys, "stderr", captured_err)
    result = helpers.err_result(helpers.SERVICE_ERROR, "boom")
    rc = helpers.emit_result("x", result, _parsed_globals(), session=None)
    assert rc == helpers.RC_OPERATIONAL_ERROR
    assert "boom" in captured_err.getvalue()


# -------------------------------------------------------------- create_read_client


def test_create_read_client_delegates(monkeypatch):
    seen = {}

    def fake_create(session, service_name, parsed_globals):
        seen["args"] = (session, service_name, parsed_globals)
        return "a-client"

    monkeypatch.setattr(
        helpers, "create_client_from_parsed_globals", fake_create
    )
    pg = _parsed_globals()
    client = helpers.create_read_client("sess", "athena", pg)
    assert client == "a-client"
    assert seen["args"] == ("sess", "athena", pg)


def test_raise_invalid_raises_param_validation():
    with pytest.raises(ParamValidationError):
        helpers.raise_invalid("nope")
