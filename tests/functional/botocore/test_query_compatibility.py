# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.


from tests import ClientHTTPStubber, patch_load_service_model

TEST_QUERY_COMPAT_SERVICE_MODEL = {
    "version": "2.0",
    "documentation": "This is a test service.",
    "metadata": {
        "apiVersion": "2023-01-01",
        "endpointPrefix": "test",
        "protocol": "json",
        "protocols": ["json", "query"],
        "jsonVersion": "1.0",
        "serviceFullName": "Test Service",
        "serviceId": "Test Service",
        "signatureVersion": "v4",
        "signingName": "testservice",
        "targetPrefix": "testservice",
        "uid": "testservice-2025-01-01",
    },
    "operations": {
        "QueryCompatOperation": {
            "name": "QueryCompatOperation",
            "http": {"method": "POST", "requestUri": "/QueryCompatOperation"},
            "input": {"shape": "SomeInput"},
            "output": {"shape": "SomeOutput"},
            "errors": [{"shape": "QueryErrorType"}],
        }
    },
    "shapes": {
        "SomeInput": {
            "type": "structure",
        },
        "SomeOutput": {
            "type": "structure",
        },
        "QueryErrorType": {
            "type": "structure",
            "members": {
                "message": {
                    "shape": "ErrorMessage",
                }
            },
            "error": {
                "code": "QueryErrorCode",
                "httpStatusCode": 404,
                "senderFault": True,
            },
            "exception": True,
        },
        "ErrorMessage": {"type": "string"},
    },
}

TEST_QUERY_COMPAT_RULESET = {
    "version": "1.0",
    "parameters": {},
    "rules": [
        {
            "conditions": [],
            "type": "endpoint",
            "endpoint": {
                "url": "https://foo.bar",
                "properties": {},
                "headers": {},
            },
        }
    ],
}


def test_generic_query_compatibility(
    patched_session,
    monkeypatch,
):
    patch_load_service_model(
        patched_session,
        monkeypatch,
        TEST_QUERY_COMPAT_SERVICE_MODEL,
        TEST_QUERY_COMPAT_RULESET,
    )
    client = patched_session.create_client(
        "testservice", region_name="us-west-2"
    )
    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(
            status=400,
            body=b'{"__type":"com.amazonaws.testService#QueryErrorType","message":"Message for query compatible error"}',
            headers={'x-amzn-query-error': 'QueryErrorCode;Sender'},
        )
        try:
            client.query_compat_operation()
            assert False, "Expected a QueryError, but wasn't thrown"
        except client.exceptions.QueryErrorType as e:
            assert e.response['Error']['Code'] == 'QueryErrorCode'
            assert e.response['Error']['QueryErrorCode'] == 'QueryErrorType'
            assert e.response['Error']['Type'] == 'Sender'
            assert e.response['ResponseMetadata']['HTTPStatusCode'] == 400


# SQS was the first service to migrate protocols, and has some unique behavior.
# We need to check that we are maintaining backwards compatibility with the error code,
# type, and query error code
def test_sqs_query_compatibility(
    patched_session,
):
    client = patched_session.create_client('sqs', region_name='us-east-1')
    with ClientHTTPStubber(client, strict=True) as http_stubber:
        http_stubber.add_response(
            status=400,
            body=b'{"__type":"com.amazonaws.sqs#QueueDoesNotExist","message":"The specified queue does not exist."}',
            headers={
                'x-amzn-query-error': 'AWS.SimpleQueueService.NonExistentQueue;Sender'
            },
        )
        try:
            client.delete_queue(QueueUrl="not-a-real-queue")
            assert False, "Expected a QueueDoesNotExist, but wasn't thrown"
        except client.exceptions.QueueDoesNotExist as e:
            assert (
                e.response['Error']['Code']
                == 'AWS.SimpleQueueService.NonExistentQueue'
            )
            assert e.response['Error']['QueryErrorCode'] == 'QueueDoesNotExist'
            assert e.response['Error']['Type'] == 'Sender'
            assert e.response['ResponseMetadata']['HTTPStatusCode'] == 400
