# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import time
from concurrent.futures import ThreadPoolExecutor

from s3transfer.exceptions import CancelledError, FatalError
from s3transfer.futures import TransferCoordinator
from s3transfer.manager import TransferConfig, TransferCoordinatorController
from tests import TransferCoordinatorWithInterrupt, unittest


class FutureResultException(Exception):
    pass


class TestTransferConfig(unittest.TestCase):
    def test_exception_on_zero_attr_value(self):
        with self.assertRaises(ValueError):
            TransferConfig(max_request_queue_size=0)


class TestTransferCoordinatorController(unittest.TestCase):
    def setUp(self):
        self.coordinator_controller = TransferCoordinatorController()

    def sleep_then_announce_done(self, transfer_coordinator, sleep_time):
        time.sleep(sleep_time)
        transfer_coordinator.set_result('done')
        transfer_coordinator.announce_done()

    def assert_coordinator_is_cancelled(self, transfer_coordinator):
        self.assertEqual(transfer_coordinator.status, 'cancelled')

    def test_add_transfer_coordinator(self):
        transfer_coordinator = TransferCoordinator()
        # Add the transfer coordinator
        self.coordinator_controller.add_transfer_coordinator(
            transfer_coordinator
        )
        # Ensure that is tracked.
        self.assertEqual(
            self.coordinator_controller.tracked_transfer_coordinators,
            {transfer_coordinator},
        )

    def test_remove_transfer_coordinator(self):
        transfer_coordinator = TransferCoordinator()
        # Add the coordinator
        self.coordinator_controller.add_transfer_coordinator(
            transfer_coordinator
        )
        # Now remove the coordinator
        self.coordinator_controller.remove_transfer_coordinator(
            transfer_coordinator
        )
        # Make sure that it is no longer getting tracked.
        self.assertEqual(
            self.coordinator_controller.tracked_transfer_coordinators, set()
        )

    def test_cancel(self):
        transfer_coordinator = TransferCoordinator()
        # Add the transfer coordinator
        self.coordinator_controller.add_transfer_coordinator(
            transfer_coordinator
        )
        # Cancel with the canceler
        self.coordinator_controller.cancel()
        # Check that coordinator got canceled
        self.assert_coordinator_is_cancelled(transfer_coordinator)

    def test_cancel_with_message(self):
        message = 'my cancel message'
        transfer_coordinator = TransferCoordinator()
        self.coordinator_controller.add_transfer_coordinator(
            transfer_coordinator
        )
        self.coordinator_controller.cancel(message)
        transfer_coordinator.announce_done()
        with self.assertRaisesRegex(CancelledError, message):
            transfer_coordinator.result()

    def test_cancel_with_provided_exception(self):
        message = 'my cancel message'
        transfer_coordinator = TransferCoordinator()
        self.coordinator_controller.add_transfer_coordinator(
            transfer_coordinator
        )
        self.coordinator_controller.cancel(message, exc_type=FatalError)
        transfer_coordinator.announce_done()
        with self.assertRaisesRegex(FatalError, message):
            transfer_coordinator.result()

    def test_wait_for_done_transfer_coordinators(self):
        # Create a coordinator and add it to the canceler
        transfer_coordinator = TransferCoordinator()
        self.coordinator_controller.add_transfer_coordinator(
            transfer_coordinator
        )

        sleep_time = 0.02
        with ThreadPoolExecutor(max_workers=1) as executor:
            # In a separate thread sleep and then set the transfer coordinator
            # to done after sleeping.
            start_time = time.time()
            executor.submit(
                self.sleep_then_announce_done, transfer_coordinator, sleep_time
            )
            # Now call wait to wait for the transfer coordinator to be done.
            self.coordinator_controller.wait()
            end_time = time.time()
            wait_time = end_time - start_time
        # The time waited should not be less than the time it took to sleep in
        # the separate thread because the wait ending should be dependent on
        # the sleeping thread announcing that the transfer coordinator is done.
        self.assertTrue(sleep_time <= wait_time)

    def test_wait_does_not_propogate_exceptions_from_result(self):
        transfer_coordinator = TransferCoordinator()
        transfer_coordinator.set_exception(FutureResultException())
        transfer_coordinator.announce_done()
        try:
            self.coordinator_controller.wait()
        except FutureResultException as e:
            self.fail(f'{e} should not have been raised.')

    def test_wait_can_be_interrupted(self):
        inject_interrupt_coordinator = TransferCoordinatorWithInterrupt()
        self.coordinator_controller.add_transfer_coordinator(
            inject_interrupt_coordinator
        )
        with self.assertRaises(KeyboardInterrupt):
            self.coordinator_controller.wait()
