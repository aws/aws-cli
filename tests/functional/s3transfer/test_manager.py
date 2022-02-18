# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License'). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the 'license' file accompanying this file. This file is
# distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from io import BytesIO

from botocore.awsrequest import create_request_object

from s3transfer.exceptions import CancelledError, FatalError
from s3transfer.futures import BaseExecutor
from s3transfer.manager import TransferConfig, TransferManager
from tests import StubbedClientTest, mock, skip_if_using_serial_implementation


class ArbitraryException(Exception):
    pass


class SignalTransferringBody(BytesIO):
    """A mocked body with the ability to signal when transfers occur"""

    def __init__(self):
        super().__init__()
        self.signal_transferring_call_count = 0
        self.signal_not_transferring_call_count = 0

    def signal_transferring(self):
        self.signal_transferring_call_count += 1

    def signal_not_transferring(self):
        self.signal_not_transferring_call_count += 1

    def seek(self, where, whence=0):
        pass

    def tell(self):
        return 0

    def read(self, amount=0):
        return b''


class TestTransferManager(StubbedClientTest):
    @skip_if_using_serial_implementation(
        'Exception is thrown once all transfers are submitted. '
        'However for the serial implementation, transfers are performed '
        'in main thread meaning all transfers will complete before the '
        'exception being thrown.'
    )
    def test_error_in_context_manager_cancels_incomplete_transfers(self):
        # The purpose of this test is to make sure if an error is raised
        # in the body of the context manager, incomplete transfers will
        # be cancelled with value of the exception wrapped by a CancelledError

        # NOTE: The fact that delete() was chosen to test this is arbitrary
        # other than it is the easiet to set up for the stubber.
        # The specific operation is not important to the purpose of this test.
        num_transfers = 100
        futures = []
        ref_exception_msg = 'arbitrary exception'

        for _ in range(num_transfers):
            self.stubber.add_response('delete_object', {})

        manager = TransferManager(
            self.client,
            TransferConfig(
                max_request_concurrency=1, max_submission_concurrency=1
            ),
        )
        try:
            with manager:
                for i in range(num_transfers):
                    futures.append(manager.delete('mybucket', 'mykey'))
                raise ArbitraryException(ref_exception_msg)
        except ArbitraryException:
            # At least one of the submitted futures should have been
            # cancelled.
            with self.assertRaisesRegex(FatalError, ref_exception_msg):
                for future in futures:
                    future.result()

    @skip_if_using_serial_implementation(
        'Exception is thrown once all transfers are submitted. '
        'However for the serial implementation, transfers are performed '
        'in main thread meaning all transfers will complete before the '
        'exception being thrown.'
    )
    def test_cntrl_c_in_context_manager_cancels_incomplete_transfers(self):
        # The purpose of this test is to make sure if an error is raised
        # in the body of the context manager, incomplete transfers will
        # be cancelled with value of the exception wrapped by a CancelledError

        # NOTE: The fact that delete() was chosen to test this is arbitrary
        # other than it is the easiet to set up for the stubber.
        # The specific operation is not important to the purpose of this test.
        num_transfers = 100
        futures = []

        for _ in range(num_transfers):
            self.stubber.add_response('delete_object', {})

        manager = TransferManager(
            self.client,
            TransferConfig(
                max_request_concurrency=1, max_submission_concurrency=1
            ),
        )
        try:
            with manager:
                for i in range(num_transfers):
                    futures.append(manager.delete('mybucket', 'mykey'))
                raise KeyboardInterrupt()
        except KeyboardInterrupt:
            # At least one of the submitted futures should have been
            # cancelled.
            with self.assertRaisesRegex(CancelledError, 'KeyboardInterrupt()'):
                for future in futures:
                    future.result()

    def test_enable_disable_callbacks_only_ever_registered_once(self):
        body = SignalTransferringBody()
        request = create_request_object(
            {
                'method': 'PUT',
                'url': 'https://s3.amazonaws.com',
                'body': body,
                'headers': {},
                'context': {},
            }
        )
        # Create two TransferManager's using the same client
        TransferManager(self.client)
        TransferManager(self.client)
        self.client.meta.events.emit(
            'request-created.s3', request=request, operation_name='PutObject'
        )
        # The client should have only have the enable/disable callback
        # handlers registered once depite being used for two different
        # TransferManagers.
        self.assertEqual(
            body.signal_transferring_call_count,
            1,
            'The enable_callback() should have only ever been registered once',
        )
        self.assertEqual(
            body.signal_not_transferring_call_count,
            1,
            'The disable_callback() should have only ever been registered '
            'once',
        )

    def test_use_custom_executor_implementation(self):
        mocked_executor_cls = mock.Mock(BaseExecutor)
        transfer_manager = TransferManager(
            self.client, executor_cls=mocked_executor_cls
        )
        transfer_manager.delete('bucket', 'key')
        self.assertTrue(mocked_executor_cls.return_value.submit.called)

    def test_unicode_exception_in_context_manager(self):
        with self.assertRaises(ArbitraryException):
            with TransferManager(self.client):
                raise ArbitraryException('\u2713')

    def test_client_property(self):
        manager = TransferManager(self.client)
        self.assertIs(manager.client, self.client)

    def test_config_property(self):
        config = TransferConfig()
        manager = TransferManager(self.client, config)
        self.assertIs(manager.config, config)

    def test_can_disable_bucket_validation(self):
        s3_object_lambda_arn = (
            'arn:aws:s3-object-lambda:us-west-2:123456789012:'
            'accesspoint:my-accesspoint'
        )
        config = TransferConfig()
        manager = TransferManager(self.client, config)
        manager.VALIDATE_SUPPORTED_BUCKET_VALUES = False
        manager.delete(s3_object_lambda_arn, 'my-key')
