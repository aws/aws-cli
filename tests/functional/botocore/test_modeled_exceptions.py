# Copyright 2012-2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests import BaseSessionTest, ClientHTTPStubber


class TestModeledExceptions(BaseSessionTest):
    def setUp(self):
        super().setUp()
        self.region = "us-east-1"

    def _create_client(self, service):
        client = self.session.create_client(service, self.region)
        http_stubber = ClientHTTPStubber(client)
        return client, http_stubber

    def test_query_service(self):
        body = (
            b'<ErrorResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">'
            b'<Error><Type>Sender</Type>'
            b'<Name>foobar</Name>'
            b'<Code>AlreadyExists</Code>'
            b'<Message>Template already exists</Message>'
            b'</Error></ErrorResponse>'
        )
        response = {
            'Error': {
                # NOTE: The name and type are also present here as we return
                # the entire Error node as the 'Error' field for query
                'Name': 'foobar',
                'Type': 'Sender',
                'Code': 'AlreadyExists',
                'Message': 'Template already exists',
            },
            'ResponseMetadata': {
                'HTTPStatusCode': 400,
                'HTTPHeaders': {},
                'RetryAttempts': 0,
            },
            # Modeled properties on the exception shape
            'Name': 'foobar',
        }
        ses, http_stubber = self._create_client('ses')
        exception_cls = ses.exceptions.AlreadyExistsException
        with http_stubber as stubber:
            stubber.add_response(status=400, headers={}, body=body)
            with self.assertRaises(exception_cls) as assertion_context:
                template = {
                    'TemplateName': 'foobar',
                    'SubjectPart': 'foo',
                    'TextPart': 'bar',
                }
                ses.create_template(Template=template)
            self.assertEqual(assertion_context.exception.response, response)

    def test_rest_xml_service(self):
        body = (
            b'<?xml version="1.0"?>\n'
            b'<ErrorResponse xmlns="http://cloudfront.amazonaws.com/doc/2019-03-26/">'
            b'<Error><Type>Sender</Type><Code>NoSuchDistribution</Code>'
            b'<Message>The specified distribution does not exist.</Message>'
            b'</Error>'
            b'<RequestId>request-id</RequestId>'
            b'</ErrorResponse>'
        )
        response = {
            'Error': {
                'Type': 'Sender',
                'Code': 'NoSuchDistribution',
                'Message': 'The specified distribution does not exist.',
            },
            'ResponseMetadata': {
                'HTTPStatusCode': 404,
                'HTTPHeaders': {},
                'RequestId': 'request-id',
                'RetryAttempts': 0,
            },
            # Modeled properties on the exception shape
            'Message': 'The specified distribution does not exist.',
        }
        cloudfront, http_stubber = self._create_client('cloudfront')
        exception_cls = cloudfront.exceptions.NoSuchDistribution
        with http_stubber as stubber:
            stubber.add_response(status=404, headers={}, body=body)
            with self.assertRaises(exception_cls) as assertion_context:
                cloudfront.get_distribution(Id='foobar')
            self.assertEqual(assertion_context.exception.response, response)

    def test_rest_json_service(self):
        headers = {
            'x-amzn-RequestId': 'request-id',
            'x-amzn-ErrorType': 'FileSystemAlreadyExists:',
        }
        body = (
            b'{"ErrorCode":"FileSystemAlreadyExists",'
            b'"FileSystemId":"fs-abcabc12",'
            b'"Message":"File system already exists"}'
        )
        response = {
            'Error': {
                'Code': 'FileSystemAlreadyExists',
                'Message': 'File system already exists',
            },
            'ResponseMetadata': {
                'HTTPStatusCode': 409,
                'HTTPHeaders': {
                    'x-amzn-requestid': 'request-id',
                    'x-amzn-errortype': 'FileSystemAlreadyExists:',
                },
                'RequestId': 'request-id',
                'RetryAttempts': 0,
            },
            # Modeled properties on the exception shape
            'ErrorCode': 'FileSystemAlreadyExists',
            'FileSystemId': 'fs-abcabc12',
            'Message': 'File system already exists',
        }
        efs, http_stubber = self._create_client('efs')
        exception_cls = efs.exceptions.FileSystemAlreadyExists
        with http_stubber as stubber:
            stubber.add_response(status=409, headers=headers, body=body)
            with self.assertRaises(exception_cls) as assertion_context:
                efs.create_file_system()
            self.assertEqual(assertion_context.exception.response, response)

    def test_json_service(self):
        headers = {
            'x-amzn-RequestId': 'request-id',
            'x-amzn-id-2': 'id-2',
        }
        body = (
            b'{"__type":"ResourceNotFoundException",'
            b'"message":"Stream not found"}'
        )
        response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Stream not found',
            },
            'ResponseMetadata': {
                'HTTPStatusCode': 400,
                'HTTPHeaders': {
                    'x-amzn-requestid': 'request-id',
                    'x-amzn-id-2': 'id-2',
                },
                'RequestId': 'request-id',
                'RetryAttempts': 0,
            },
            # Modeled properties on the exception shape
            'message': 'Stream not found',
        }
        kinesis, http_stubber = self._create_client('kinesis')
        exception_cls = kinesis.exceptions.ResourceNotFoundException
        with http_stubber as stubber:
            stubber.add_response(status=400, headers=headers, body=body)
            with self.assertRaises(exception_cls) as assertion_context:
                kinesis.describe_stream(StreamName='foobar')
            self.assertEqual(assertion_context.exception.response, response)
