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
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from s3transfer.exceptions import (
    CancelledError,
    FatalError,
    TransferNotDoneError,
)
from s3transfer.futures import (
    BaseExecutor,
    BoundedExecutor,
    ExecutorFuture,
    NonThreadedExecutor,
    NonThreadedExecutorFuture,
    TransferCoordinator,
    TransferFuture,
    TransferMeta,
)
from s3transfer.tasks import Task
from s3transfer.utils import (
    FunctionContainer,
    NoResourcesAvailable,
    TaskSemaphore,
)
from tests import (
    RecordingExecutor,
    TransferCoordinatorWithInterrupt,
    mock,
    unittest,
)


def return_call_args(*args, **kwargs):
    return args, kwargs


def raise_exception(exception):
    raise exception


def get_exc_info(exception):
    try:
        raise_exception(exception)
    except Exception:
        return sys.exc_info()


class RecordingTransferCoordinator(TransferCoordinator):
    def __init__(self):
        self.all_transfer_futures_ever_associated = set()
        super().__init__()

    def add_associated_future(self, future):
        self.all_transfer_futures_ever_associated.add(future)
        super().add_associated_future(future)


class ReturnFooTask(Task):
    def _main(self, **kwargs):
        return 'foo'


class SleepTask(Task):
    def _main(self, sleep_time, **kwargs):
        time.sleep(sleep_time)


class TestTransferFuture(unittest.TestCase):
    def setUp(self):
        self.meta = TransferMeta()
        self.coordinator = TransferCoordinator()
        self.future = self._get_transfer_future()

    def _get_transfer_future(self, **kwargs):
        components = {
            'meta': self.meta,
            'coordinator': self.coordinator,
        }
        for component_name, component in kwargs.items():
            components[component_name] = component
        return TransferFuture(**components)

    def test_meta(self):
        self.assertIs(self.future.meta, self.meta)

    def test_done(self):
        self.assertFalse(self.future.done())
        self.coordinator.set_result(None)
        self.assertTrue(self.future.done())

    def test_result(self):
        result = 'foo'
        self.coordinator.set_result(result)
        self.coordinator.announce_done()
        self.assertEqual(self.future.result(), result)

    def test_keyboard_interrupt_on_result_does_not_block(self):
        # This should raise a KeyboardInterrupt when result is called on it.
        self.coordinator = TransferCoordinatorWithInterrupt()
        self.future = self._get_transfer_future()

        # result() should not block and immediately raise the keyboard
        # interrupt exception.
        with self.assertRaises(KeyboardInterrupt):
            self.future.result()

    def test_cancel(self):
        self.future.cancel()
        self.assertTrue(self.future.done())
        self.assertEqual(self.coordinator.status, 'cancelled')

    def test_set_exception(self):
        # Set the result such that there is no exception
        self.coordinator.set_result('result')
        self.coordinator.announce_done()
        self.assertEqual(self.future.result(), 'result')

        self.future.set_exception(ValueError())
        with self.assertRaises(ValueError):
            self.future.result()

    def test_set_exception_only_after_done(self):
        with self.assertRaises(TransferNotDoneError):
            self.future.set_exception(ValueError())

        self.coordinator.set_result('result')
        self.coordinator.announce_done()
        self.future.set_exception(ValueError())
        with self.assertRaises(ValueError):
            self.future.result()


class TestTransferMeta(unittest.TestCase):
    def setUp(self):
        self.transfer_meta = TransferMeta()

    def test_size(self):
        self.assertEqual(self.transfer_meta.size, None)
        self.transfer_meta.provide_transfer_size(5)
        self.assertEqual(self.transfer_meta.size, 5)

    def test_call_args(self):
        call_args = object()
        transfer_meta = TransferMeta(call_args)
        # Assert the that call args provided is the same as is returned
        self.assertIs(transfer_meta.call_args, call_args)

    def test_transfer_id(self):
        transfer_meta = TransferMeta(transfer_id=1)
        self.assertEqual(transfer_meta.transfer_id, 1)

    def test_user_context(self):
        self.transfer_meta.user_context['foo'] = 'bar'
        self.assertEqual(self.transfer_meta.user_context, {'foo': 'bar'})


class TestTransferCoordinator(unittest.TestCase):
    def setUp(self):
        self.transfer_coordinator = TransferCoordinator()

    def test_transfer_id(self):
        transfer_coordinator = TransferCoordinator(transfer_id=1)
        self.assertEqual(transfer_coordinator.transfer_id, 1)

    def test_repr(self):
        transfer_coordinator = TransferCoordinator(transfer_id=1)
        self.assertEqual(
            repr(transfer_coordinator), 'TransferCoordinator(transfer_id=1)'
        )

    def test_initial_status(self):
        # A TransferCoordinator with no progress should have the status
        # of not-started
        self.assertEqual(self.transfer_coordinator.status, 'not-started')

    def test_set_status_to_queued(self):
        self.transfer_coordinator.set_status_to_queued()
        self.assertEqual(self.transfer_coordinator.status, 'queued')

    def test_cannot_set_status_to_queued_from_done_state(self):
        self.transfer_coordinator.set_exception(RuntimeError)
        with self.assertRaises(RuntimeError):
            self.transfer_coordinator.set_status_to_queued()

    def test_status_running(self):
        self.transfer_coordinator.set_status_to_running()
        self.assertEqual(self.transfer_coordinator.status, 'running')

    def test_cannot_set_status_to_running_from_done_state(self):
        self.transfer_coordinator.set_exception(RuntimeError)
        with self.assertRaises(RuntimeError):
            self.transfer_coordinator.set_status_to_running()

    def test_set_result(self):
        success_result = 'foo'
        self.transfer_coordinator.set_result(success_result)
        self.transfer_coordinator.announce_done()
        # Setting result should result in a success state and the return value
        # that was set.
        self.assertEqual(self.transfer_coordinator.status, 'success')
        self.assertEqual(self.transfer_coordinator.result(), success_result)

    def test_set_exception(self):
        exception_result = RuntimeError
        self.transfer_coordinator.set_exception(exception_result)
        self.transfer_coordinator.announce_done()
        # Setting an exception should result in a failed state and the return
        # value should be the raised exception
        self.assertEqual(self.transfer_coordinator.status, 'failed')
        self.assertEqual(self.transfer_coordinator.exception, exception_result)
        with self.assertRaises(exception_result):
            self.transfer_coordinator.result()

    def test_exception_cannot_override_done_state(self):
        self.transfer_coordinator.set_result('foo')
        self.transfer_coordinator.set_exception(RuntimeError)
        # It status should be success even after the exception is set because
        # success is a done state.
        self.assertEqual(self.transfer_coordinator.status, 'success')

    def test_exception_can_override_done_state_with_override_flag(self):
        self.transfer_coordinator.set_result('foo')
        self.transfer_coordinator.set_exception(RuntimeError, override=True)
        self.assertEqual(self.transfer_coordinator.status, 'failed')

    def test_cancel(self):
        self.assertEqual(self.transfer_coordinator.status, 'not-started')
        self.transfer_coordinator.cancel()
        # This should set the state to cancelled and raise the CancelledError
        # exception and should have also set the done event so that result()
        # is no longer set.
        self.assertEqual(self.transfer_coordinator.status, 'cancelled')
        with self.assertRaises(CancelledError):
            self.transfer_coordinator.result()

    def test_cancel_can_run_done_callbacks_that_uses_result(self):
        exceptions = []

        def capture_exception(transfer_coordinator, captured_exceptions):
            try:
                transfer_coordinator.result()
            except Exception as e:
                captured_exceptions.append(e)

        self.assertEqual(self.transfer_coordinator.status, 'not-started')
        self.transfer_coordinator.add_done_callback(
            capture_exception, self.transfer_coordinator, exceptions
        )
        self.transfer_coordinator.cancel()

        self.assertEqual(len(exceptions), 1)
        self.assertIsInstance(exceptions[0], CancelledError)

    def test_cancel_with_message(self):
        message = 'my message'
        self.transfer_coordinator.cancel(message)
        self.transfer_coordinator.announce_done()
        with self.assertRaisesRegex(CancelledError, message):
            self.transfer_coordinator.result()

    def test_cancel_with_provided_exception(self):
        message = 'my message'
        self.transfer_coordinator.cancel(message, exc_type=FatalError)
        self.transfer_coordinator.announce_done()
        with self.assertRaisesRegex(FatalError, message):
            self.transfer_coordinator.result()

    def test_cancel_cannot_override_done_state(self):
        self.transfer_coordinator.set_result('foo')
        self.transfer_coordinator.cancel()
        # It status should be success even after cancel is called because
        # success is a done state.
        self.assertEqual(self.transfer_coordinator.status, 'success')

    def test_set_result_can_override_cancel(self):
        self.transfer_coordinator.cancel()
        # Result setting should override any cancel or set exception as this
        # is always invoked by the final task.
        self.transfer_coordinator.set_result('foo')
        self.transfer_coordinator.announce_done()
        self.assertEqual(self.transfer_coordinator.status, 'success')

    def test_submit(self):
        # Submit a callable to the transfer coordinator. It should submit it
        # to the executor.
        executor = RecordingExecutor(
            BoundedExecutor(1, 1, {'my-tag': TaskSemaphore(1)})
        )
        task = ReturnFooTask(self.transfer_coordinator)
        future = self.transfer_coordinator.submit(executor, task, tag='my-tag')
        executor.shutdown()
        # Make sure the future got submit and executed as well by checking its
        # result value which should include the provided future tag.
        self.assertEqual(
            executor.submissions,
            [{'block': True, 'tag': 'my-tag', 'task': task}],
        )
        self.assertEqual(future.result(), 'foo')

    def test_association_and_disassociation_on_submit(self):
        self.transfer_coordinator = RecordingTransferCoordinator()

        # Submit a callable to the transfer coordinator.
        executor = BoundedExecutor(1, 1)
        task = ReturnFooTask(self.transfer_coordinator)
        future = self.transfer_coordinator.submit(executor, task)
        executor.shutdown()

        # Make sure the future that got submitted was associated to the
        # transfer future at some point.
        self.assertEqual(
            self.transfer_coordinator.all_transfer_futures_ever_associated,
            {future},
        )

        # Make sure the future got disassociated once the future is now done
        # by looking at the currently associated futures.
        self.assertEqual(self.transfer_coordinator.associated_futures, set())

    def test_done(self):
        # These should result in not done state:
        # queued
        self.assertFalse(self.transfer_coordinator.done())
        # running
        self.transfer_coordinator.set_status_to_running()
        self.assertFalse(self.transfer_coordinator.done())

        # These should result in done state:
        # failed
        self.transfer_coordinator.set_exception(Exception)
        self.assertTrue(self.transfer_coordinator.done())

        # success
        self.transfer_coordinator.set_result('foo')
        self.assertTrue(self.transfer_coordinator.done())

        # cancelled
        self.transfer_coordinator.cancel()
        self.assertTrue(self.transfer_coordinator.done())

    def test_result_waits_until_done(self):
        execution_order = []

        def sleep_then_set_result(transfer_coordinator, execution_order):
            time.sleep(0.05)
            execution_order.append('setting_result')
            transfer_coordinator.set_result(None)
            self.transfer_coordinator.announce_done()

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                sleep_then_set_result,
                self.transfer_coordinator,
                execution_order,
            )
            self.transfer_coordinator.result()
            execution_order.append('after_result')

        # The result() call should have waited until the other thread set
        # the result after sleeping for 0.05 seconds.
        self.assertTrue(execution_order, ['setting_result', 'after_result'])

    def test_failure_cleanups(self):
        args = (1, 2)
        kwargs = {'foo': 'bar'}

        second_args = (2, 4)
        second_kwargs = {'biz': 'baz'}

        self.transfer_coordinator.add_failure_cleanup(
            return_call_args, *args, **kwargs
        )
        self.transfer_coordinator.add_failure_cleanup(
            return_call_args, *second_args, **second_kwargs
        )

        # Ensure the callbacks got added.
        self.assertEqual(len(self.transfer_coordinator.failure_cleanups), 2)

        result_list = []
        # Ensure they will get called in the correct order.
        for cleanup in self.transfer_coordinator.failure_cleanups:
            result_list.append(cleanup())
        self.assertEqual(
            result_list, [(args, kwargs), (second_args, second_kwargs)]
        )

    def test_associated_futures(self):
        first_future = object()
        # Associate one future to the transfer
        self.transfer_coordinator.add_associated_future(first_future)
        associated_futures = self.transfer_coordinator.associated_futures
        # The first future should be in the returned list of futures.
        self.assertEqual(associated_futures, {first_future})

        second_future = object()
        # Associate another future to the transfer.
        self.transfer_coordinator.add_associated_future(second_future)
        # The association should not have mutated the returned list from
        # before.
        self.assertEqual(associated_futures, {first_future})

        # Both futures should be in the returned list.
        self.assertEqual(
            self.transfer_coordinator.associated_futures,
            {first_future, second_future},
        )

    def test_done_callbacks_on_done(self):
        done_callback_invocations = []
        callback = FunctionContainer(
            done_callback_invocations.append, 'done callback called'
        )

        # Add the done callback to the transfer.
        self.transfer_coordinator.add_done_callback(callback)

        # Announce that the transfer is done. This should invoke the done
        # callback.
        self.transfer_coordinator.announce_done()
        self.assertEqual(done_callback_invocations, ['done callback called'])

        # If done is announced again, we should not invoke the callback again
        # because done has already been announced and thus the callback has
        # been ran as well.
        self.transfer_coordinator.announce_done()
        self.assertEqual(done_callback_invocations, ['done callback called'])

    def test_failure_cleanups_on_done(self):
        cleanup_invocations = []
        callback = FunctionContainer(
            cleanup_invocations.append, 'cleanup called'
        )

        # Add the failure cleanup to the transfer.
        self.transfer_coordinator.add_failure_cleanup(callback)

        # Announce that the transfer is done. This should invoke the failure
        # cleanup.
        self.transfer_coordinator.announce_done()
        self.assertEqual(cleanup_invocations, ['cleanup called'])

        # If done is announced again, we should not invoke the cleanup again
        # because done has already been announced and thus the cleanup has
        # been ran as well.
        self.transfer_coordinator.announce_done()
        self.assertEqual(cleanup_invocations, ['cleanup called'])


class TestBoundedExecutor(unittest.TestCase):
    def setUp(self):
        self.coordinator = TransferCoordinator()
        self.tag_semaphores = {}
        self.executor = self.get_executor()

    def get_executor(self, max_size=1, max_num_threads=1):
        return BoundedExecutor(max_size, max_num_threads, self.tag_semaphores)

    def get_task(self, task_cls, main_kwargs=None):
        return task_cls(self.coordinator, main_kwargs=main_kwargs)

    def get_sleep_task(self, sleep_time=0.01):
        return self.get_task(SleepTask, main_kwargs={'sleep_time': sleep_time})

    def add_semaphore(self, task_tag, count):
        self.tag_semaphores[task_tag] = TaskSemaphore(count)

    def assert_submit_would_block(self, task, tag=None):
        with self.assertRaises(NoResourcesAvailable):
            self.executor.submit(task, tag=tag, block=False)

    def assert_submit_would_not_block(self, task, tag=None, **kwargs):
        try:
            self.executor.submit(task, tag=tag, block=False)
        except NoResourcesAvailable:
            self.fail(
                'Task {} should not have been blocked. Caused by:\n{}'.format(
                    task, traceback.format_exc()
                )
            )

    def add_done_callback_to_future(self, future, fn, *args, **kwargs):
        callback_for_future = FunctionContainer(fn, *args, **kwargs)
        future.add_done_callback(callback_for_future)

    def test_submit_single_task(self):
        # Ensure we can submit a task to the executor
        task = self.get_task(ReturnFooTask)
        future = self.executor.submit(task)

        # Ensure what we get back is a Future
        self.assertIsInstance(future, ExecutorFuture)
        # Ensure the callable got executed.
        self.assertEqual(future.result(), 'foo')

    @unittest.skipIf(
        os.environ.get('USE_SERIAL_EXECUTOR'),
        "Not supported with serial executor tests",
    )
    def test_executor_blocks_on_full_capacity(self):
        first_task = self.get_sleep_task()
        second_task = self.get_sleep_task()
        self.executor.submit(first_task)
        # The first task should be sleeping for a substantial period of
        # time such that on the submission of the second task, it will
        # raise an error saying that it cannot be submitted as the max
        # capacity of the semaphore is one.
        self.assert_submit_would_block(second_task)

    def test_executor_clears_capacity_on_done_tasks(self):
        first_task = self.get_sleep_task()
        second_task = self.get_task(ReturnFooTask)

        # Submit a task.
        future = self.executor.submit(first_task)

        # Submit a new task when the first task finishes. This should not get
        # blocked because the first task should have finished clearing up
        # capacity.
        self.add_done_callback_to_future(
            future, self.assert_submit_would_not_block, second_task
        )

        # Wait for it to complete.
        self.executor.shutdown()

    @unittest.skipIf(
        os.environ.get('USE_SERIAL_EXECUTOR'),
        "Not supported with serial executor tests",
    )
    def test_would_not_block_when_full_capacity_in_other_semaphore(self):
        first_task = self.get_sleep_task()

        # Now let's create a new task with a tag and so it uses different
        # semaphore.
        task_tag = 'other'
        other_task = self.get_sleep_task()
        self.add_semaphore(task_tag, 1)

        # Submit the normal first task
        self.executor.submit(first_task)

        # Even though The first task should be sleeping for a substantial
        # period of time, the submission of the second task should not
        # raise an error because it should use a different semaphore
        self.assert_submit_would_not_block(other_task, task_tag)

        # Another submission of the other task though should raise
        # an exception as the capacity is equal to one for that tag.
        self.assert_submit_would_block(other_task, task_tag)

    def test_shutdown(self):
        slow_task = self.get_sleep_task()
        future = self.executor.submit(slow_task)
        self.executor.shutdown()
        # Ensure that the shutdown waits until the task is done
        self.assertTrue(future.done())

    @unittest.skipIf(
        os.environ.get('USE_SERIAL_EXECUTOR'),
        "Not supported with serial executor tests",
    )
    def test_shutdown_no_wait(self):
        slow_task = self.get_sleep_task()
        future = self.executor.submit(slow_task)
        self.executor.shutdown(False)
        # Ensure that the shutdown returns immediately even if the task is
        # not done, which it should not be because it it slow.
        self.assertFalse(future.done())

    def test_replace_underlying_executor(self):
        mocked_executor_cls = mock.Mock(BaseExecutor)
        executor = BoundedExecutor(10, 1, {}, mocked_executor_cls)
        executor.submit(self.get_task(ReturnFooTask))
        self.assertTrue(mocked_executor_cls.return_value.submit.called)


class TestExecutorFuture(unittest.TestCase):
    def test_result(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(return_call_args, 'foo', biz='baz')
            wrapped_future = ExecutorFuture(future)
        self.assertEqual(wrapped_future.result(), (('foo',), {'biz': 'baz'}))

    def test_done(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(return_call_args, 'foo', biz='baz')
            wrapped_future = ExecutorFuture(future)
        self.assertTrue(wrapped_future.done())

    def test_add_done_callback(self):
        done_callbacks = []
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(return_call_args, 'foo', biz='baz')
            wrapped_future = ExecutorFuture(future)
            wrapped_future.add_done_callback(
                FunctionContainer(done_callbacks.append, 'called')
            )
        self.assertEqual(done_callbacks, ['called'])


class TestNonThreadedExecutor(unittest.TestCase):
    def test_submit(self):
        executor = NonThreadedExecutor()
        future = executor.submit(return_call_args, 1, 2, foo='bar')
        self.assertIsInstance(future, NonThreadedExecutorFuture)
        self.assertEqual(future.result(), ((1, 2), {'foo': 'bar'}))

    def test_submit_with_exception(self):
        executor = NonThreadedExecutor()
        future = executor.submit(raise_exception, RuntimeError())
        self.assertIsInstance(future, NonThreadedExecutorFuture)
        with self.assertRaises(RuntimeError):
            future.result()

    def test_submit_with_exception_and_captures_info(self):
        exception = ValueError('message')
        tb = get_exc_info(exception)[2]
        future = NonThreadedExecutor().submit(raise_exception, exception)
        try:
            future.result()
            # An exception should have been raised
            self.fail('Future should have raised a ValueError')
        except ValueError:
            actual_tb = sys.exc_info()[2]
            last_frame = traceback.extract_tb(actual_tb)[-1]
            last_expected_frame = traceback.extract_tb(tb)[-1]
            self.assertEqual(last_frame, last_expected_frame)


class TestNonThreadedExecutorFuture(unittest.TestCase):
    def setUp(self):
        self.future = NonThreadedExecutorFuture()

    def test_done_starts_false(self):
        self.assertFalse(self.future.done())

    def test_done_after_setting_result(self):
        self.future.set_result('result')
        self.assertTrue(self.future.done())

    def test_done_after_setting_exception(self):
        self.future.set_exception_info(Exception(), None)
        self.assertTrue(self.future.done())

    def test_result(self):
        self.future.set_result('result')
        self.assertEqual(self.future.result(), 'result')

    def test_exception_result(self):
        exception = ValueError('message')
        self.future.set_exception_info(exception, None)
        with self.assertRaisesRegex(ValueError, 'message'):
            self.future.result()

    def test_exception_result_doesnt_modify_last_frame(self):
        exception = ValueError('message')
        tb = get_exc_info(exception)[2]
        self.future.set_exception_info(exception, tb)
        try:
            self.future.result()
            # An exception should have been raised
            self.fail()
        except ValueError:
            actual_tb = sys.exc_info()[2]
            last_frame = traceback.extract_tb(actual_tb)[-1]
            last_expected_frame = traceback.extract_tb(tb)[-1]
            self.assertEqual(last_frame, last_expected_frame)

    def test_done_callback(self):
        done_futures = []
        self.future.add_done_callback(done_futures.append)
        self.assertEqual(done_futures, [])
        self.future.set_result('result')
        self.assertEqual(done_futures, [self.future])

    def test_done_callback_after_done(self):
        self.future.set_result('result')
        done_futures = []
        self.future.add_done_callback(done_futures.append)
        self.assertEqual(done_futures, [self.future])
