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
from concurrent import futures
from functools import partial
from threading import Event

from s3transfer.futures import BoundedExecutor, TransferCoordinator
from s3transfer.subscribers import BaseSubscriber
from s3transfer.tasks import (
    CompleteMultipartUploadTask,
    CreateMultipartUploadTask,
    SubmissionTask,
    Task,
)
from s3transfer.utils import CallArgs, FunctionContainer, get_callbacks
from tests import (
    BaseSubmissionTaskTest,
    BaseTaskTest,
    RecordingSubscriber,
    unittest,
)


class TaskFailureException(Exception):
    pass


class SuccessTask(Task):
    def _main(
        self, return_value='success', callbacks=None, failure_cleanups=None
    ):
        if callbacks:
            for callback in callbacks:
                callback()
        if failure_cleanups:
            for failure_cleanup in failure_cleanups:
                self._transfer_coordinator.add_failure_cleanup(failure_cleanup)
        return return_value


class FailureTask(Task):
    def _main(self, exception=TaskFailureException):
        raise exception()


class ReturnKwargsTask(Task):
    def _main(self, **kwargs):
        return kwargs


class SubmitMoreTasksTask(Task):
    def _main(self, executor, tasks_to_submit):
        for task_to_submit in tasks_to_submit:
            self._transfer_coordinator.submit(executor, task_to_submit)


class NOOPSubmissionTask(SubmissionTask):
    def _submit(self, transfer_future, **kwargs):
        pass


class ExceptionSubmissionTask(SubmissionTask):
    def _submit(
        self,
        transfer_future,
        executor=None,
        tasks_to_submit=None,
        additional_callbacks=None,
        exception=TaskFailureException,
    ):
        if executor and tasks_to_submit:
            for task_to_submit in tasks_to_submit:
                self._transfer_coordinator.submit(executor, task_to_submit)
        if additional_callbacks:
            for callback in additional_callbacks:
                callback()
        raise exception()


class StatusRecordingTransferCoordinator(TransferCoordinator):
    def __init__(self, transfer_id=None):
        super().__init__(transfer_id)
        self.status_changes = [self._status]

    def set_status_to_queued(self):
        super().set_status_to_queued()
        self._record_status_change()

    def set_status_to_running(self):
        super().set_status_to_running()
        self._record_status_change()

    def _record_status_change(self):
        self.status_changes.append(self._status)


class RecordingStateSubscriber(BaseSubscriber):
    def __init__(self, transfer_coordinator):
        self._transfer_coordinator = transfer_coordinator
        self.status_during_on_queued = None

    def on_queued(self, **kwargs):
        self.status_during_on_queued = self._transfer_coordinator.status


class TestSubmissionTask(BaseSubmissionTaskTest):
    def setUp(self):
        super().setUp()
        self.executor = BoundedExecutor(1000, 5)
        self.call_args = CallArgs(subscribers=[])
        self.transfer_future = self.get_transfer_future(self.call_args)
        self.main_kwargs = {'transfer_future': self.transfer_future}

    def test_transitions_from_not_started_to_queued_to_running(self):
        self.transfer_coordinator = StatusRecordingTransferCoordinator()
        submission_task = self.get_task(
            NOOPSubmissionTask, main_kwargs=self.main_kwargs
        )
        # Status should be queued until submission task has been ran.
        self.assertEqual(self.transfer_coordinator.status, 'not-started')

        submission_task()
        # Once submission task has been ran, the status should now be running.
        self.assertEqual(self.transfer_coordinator.status, 'running')

        # Ensure the transitions were as expected as well.
        self.assertEqual(
            self.transfer_coordinator.status_changes,
            ['not-started', 'queued', 'running'],
        )

    def test_on_queued_callbacks(self):
        submission_task = self.get_task(
            NOOPSubmissionTask, main_kwargs=self.main_kwargs
        )

        subscriber = RecordingSubscriber()
        self.call_args.subscribers.append(subscriber)
        submission_task()
        # Make sure the on_queued callback of the subscriber is called.
        self.assertEqual(
            subscriber.on_queued_calls, [{'future': self.transfer_future}]
        )

    def test_on_queued_status_in_callbacks(self):
        submission_task = self.get_task(
            NOOPSubmissionTask, main_kwargs=self.main_kwargs
        )

        subscriber = RecordingStateSubscriber(self.transfer_coordinator)
        self.call_args.subscribers.append(subscriber)
        submission_task()
        # Make sure the status was queued during on_queued callback.
        self.assertEqual(subscriber.status_during_on_queued, 'queued')

    def test_sets_exception_from_submit(self):
        submission_task = self.get_task(
            ExceptionSubmissionTask, main_kwargs=self.main_kwargs
        )
        submission_task()

        # Make sure the status of the future is failed
        self.assertEqual(self.transfer_coordinator.status, 'failed')

        # Make sure the future propagates the exception encountered in the
        # submission task.
        with self.assertRaises(TaskFailureException):
            self.transfer_future.result()

    def test_catches_and_sets_keyboard_interrupt_exception_from_submit(self):
        self.main_kwargs['exception'] = KeyboardInterrupt
        submission_task = self.get_task(
            ExceptionSubmissionTask, main_kwargs=self.main_kwargs
        )
        submission_task()

        self.assertEqual(self.transfer_coordinator.status, 'failed')
        with self.assertRaises(KeyboardInterrupt):
            self.transfer_future.result()

    def test_calls_done_callbacks_on_exception(self):
        submission_task = self.get_task(
            ExceptionSubmissionTask, main_kwargs=self.main_kwargs
        )

        subscriber = RecordingSubscriber()
        self.call_args.subscribers.append(subscriber)

        # Add the done callback to the callbacks to be invoked when the
        # transfer is done.
        done_callbacks = get_callbacks(self.transfer_future, 'done')
        for done_callback in done_callbacks:
            self.transfer_coordinator.add_done_callback(done_callback)
        submission_task()

        # Make sure the task failed to start
        self.assertEqual(self.transfer_coordinator.status, 'failed')

        # Make sure the on_done callback of the subscriber is called.
        self.assertEqual(
            subscriber.on_done_calls, [{'future': self.transfer_future}]
        )

    def test_calls_failure_cleanups_on_exception(self):
        submission_task = self.get_task(
            ExceptionSubmissionTask, main_kwargs=self.main_kwargs
        )

        # Add the callback to the callbacks to be invoked when the
        # transfer fails.
        invocations_of_cleanup = []
        cleanup_callback = FunctionContainer(
            invocations_of_cleanup.append, 'cleanup happened'
        )
        self.transfer_coordinator.add_failure_cleanup(cleanup_callback)
        submission_task()

        # Make sure the task failed to start
        self.assertEqual(self.transfer_coordinator.status, 'failed')

        # Make sure the cleanup was called.
        self.assertEqual(invocations_of_cleanup, ['cleanup happened'])

    def test_cleanups_only_ran_once_on_exception(self):
        # We want to be able to handle the case where the final task completes
        # and anounces done but there is an error in the submission task
        # which will cause it to need to announce done as well. In this case,
        # we do not want the done callbacks to be invoke more than once.

        final_task = self.get_task(FailureTask, is_final=True)
        self.main_kwargs['executor'] = self.executor
        self.main_kwargs['tasks_to_submit'] = [final_task]

        submission_task = self.get_task(
            ExceptionSubmissionTask, main_kwargs=self.main_kwargs
        )

        subscriber = RecordingSubscriber()
        self.call_args.subscribers.append(subscriber)

        # Add the done callback to the callbacks to be invoked when the
        # transfer is done.
        done_callbacks = get_callbacks(self.transfer_future, 'done')
        for done_callback in done_callbacks:
            self.transfer_coordinator.add_done_callback(done_callback)

        submission_task()

        # Make sure the task failed to start
        self.assertEqual(self.transfer_coordinator.status, 'failed')

        # Make sure the on_done callback of the subscriber is called only once.
        self.assertEqual(
            subscriber.on_done_calls, [{'future': self.transfer_future}]
        )

    def test_done_callbacks_only_ran_once_on_exception(self):
        # We want to be able to handle the case where the final task completes
        # and anounces done but there is an error in the submission task
        # which will cause it to need to announce done as well. In this case,
        # we do not want the failure cleanups to be invoked more than once.

        final_task = self.get_task(FailureTask, is_final=True)
        self.main_kwargs['executor'] = self.executor
        self.main_kwargs['tasks_to_submit'] = [final_task]

        submission_task = self.get_task(
            ExceptionSubmissionTask, main_kwargs=self.main_kwargs
        )

        # Add the callback to the callbacks to be invoked when the
        # transfer fails.
        invocations_of_cleanup = []
        cleanup_callback = FunctionContainer(
            invocations_of_cleanup.append, 'cleanup happened'
        )
        self.transfer_coordinator.add_failure_cleanup(cleanup_callback)
        submission_task()

        # Make sure the task failed to start
        self.assertEqual(self.transfer_coordinator.status, 'failed')

        # Make sure the cleanup was called only once.
        self.assertEqual(invocations_of_cleanup, ['cleanup happened'])

    def test_handles_cleanups_submitted_in_other_tasks(self):
        invocations_of_cleanup = []
        event = Event()
        cleanup_callback = FunctionContainer(
            invocations_of_cleanup.append, 'cleanup happened'
        )
        # We want the cleanup to be added in the execution of the task and
        # still be executed by the submission task when it fails.
        task = self.get_task(
            SuccessTask,
            main_kwargs={
                'callbacks': [event.set],
                'failure_cleanups': [cleanup_callback],
            },
        )

        self.main_kwargs['executor'] = self.executor
        self.main_kwargs['tasks_to_submit'] = [task]
        self.main_kwargs['additional_callbacks'] = [event.wait]

        submission_task = self.get_task(
            ExceptionSubmissionTask, main_kwargs=self.main_kwargs
        )

        submission_task()
        self.assertEqual(self.transfer_coordinator.status, 'failed')

        # Make sure the cleanup was called even though the callback got
        # added in a completely different task.
        self.assertEqual(invocations_of_cleanup, ['cleanup happened'])

    def test_waits_for_tasks_submitted_by_other_tasks_on_exception(self):
        # In this test, we want to make sure that any tasks that may be
        # submitted in another task complete before we start performing
        # cleanups.
        #
        # This is tested by doing the following:
        #
        # ExecutionSubmissionTask
        #   |
        #   +--submits-->SubmitMoreTasksTask
        #                   |
        #                   +--submits-->SuccessTask
        #                                  |
        #                                  +-->sleeps-->adds failure cleanup
        #
        # In the end, the failure cleanup of the SuccessTask should be ran
        # when the ExecutionSubmissionTask fails. If the
        # ExeceptionSubmissionTask did not run the failure cleanup it is most
        # likely that it did not wait for the SuccessTask to complete, which
        # it needs to because the ExeceptionSubmissionTask does not know
        # what failure cleanups it needs to run until all spawned tasks have
        # completed.
        invocations_of_cleanup = []
        event = Event()
        cleanup_callback = FunctionContainer(
            invocations_of_cleanup.append, 'cleanup happened'
        )

        cleanup_task = self.get_task(
            SuccessTask,
            main_kwargs={
                'callbacks': [event.set],
                'failure_cleanups': [cleanup_callback],
            },
        )
        task_for_submitting_cleanup_task = self.get_task(
            SubmitMoreTasksTask,
            main_kwargs={
                'executor': self.executor,
                'tasks_to_submit': [cleanup_task],
            },
        )

        self.main_kwargs['executor'] = self.executor
        self.main_kwargs['tasks_to_submit'] = [
            task_for_submitting_cleanup_task
        ]
        self.main_kwargs['additional_callbacks'] = [event.wait]

        submission_task = self.get_task(
            ExceptionSubmissionTask, main_kwargs=self.main_kwargs
        )

        submission_task()
        self.assertEqual(self.transfer_coordinator.status, 'failed')
        self.assertEqual(invocations_of_cleanup, ['cleanup happened'])

    def test_submission_task_announces_done_if_cancelled_before_main(self):
        invocations_of_done = []
        done_callback = FunctionContainer(
            invocations_of_done.append, 'done announced'
        )
        self.transfer_coordinator.add_done_callback(done_callback)

        self.transfer_coordinator.cancel()
        submission_task = self.get_task(
            NOOPSubmissionTask, main_kwargs=self.main_kwargs
        )
        submission_task()

        # Because the submission task was cancelled before being run
        # it did not submit any extra tasks so a result it is responsible
        # for making sure it announces done as nothing else will.
        self.assertEqual(invocations_of_done, ['done announced'])


class TestTask(unittest.TestCase):
    def setUp(self):
        self.transfer_id = 1
        self.transfer_coordinator = TransferCoordinator(
            transfer_id=self.transfer_id
        )

    def test_repr(self):
        main_kwargs = {'bucket': 'mybucket', 'param_to_not_include': 'foo'}
        task = ReturnKwargsTask(
            self.transfer_coordinator, main_kwargs=main_kwargs
        )
        # The repr should not include the other parameter because it is not
        # a desired parameter to include.
        self.assertEqual(
            repr(task),
            'ReturnKwargsTask(transfer_id={}, {})'.format(
                self.transfer_id, {'bucket': 'mybucket'}
            ),
        )

    def test_transfer_id(self):
        task = SuccessTask(self.transfer_coordinator)
        # Make sure that the id is the one provided to the id associated
        # to the transfer coordinator.
        self.assertEqual(task.transfer_id, self.transfer_id)

    def test_context_status_transitioning_success(self):
        # The status should be set to running.
        self.transfer_coordinator.set_status_to_running()
        self.assertEqual(self.transfer_coordinator.status, 'running')

        # If a task is called, the status still should be running.
        SuccessTask(self.transfer_coordinator)()
        self.assertEqual(self.transfer_coordinator.status, 'running')

        # Once the final task is called, the status should be set to success.
        SuccessTask(self.transfer_coordinator, is_final=True)()
        self.assertEqual(self.transfer_coordinator.status, 'success')

    def test_context_status_transitioning_failed(self):
        self.transfer_coordinator.set_status_to_running()

        SuccessTask(self.transfer_coordinator)()
        self.assertEqual(self.transfer_coordinator.status, 'running')

        # A failure task should result in the failed status
        FailureTask(self.transfer_coordinator)()
        self.assertEqual(self.transfer_coordinator.status, 'failed')

        # Even if the final task comes in and succeeds, it should stay failed.
        SuccessTask(self.transfer_coordinator, is_final=True)()
        self.assertEqual(self.transfer_coordinator.status, 'failed')

    def test_result_setting_for_success(self):
        override_return = 'foo'
        SuccessTask(self.transfer_coordinator)()
        SuccessTask(
            self.transfer_coordinator,
            main_kwargs={'return_value': override_return},
            is_final=True,
        )()

        # The return value for the transfer future should be of the final
        # task.
        self.assertEqual(self.transfer_coordinator.result(), override_return)

    def test_result_setting_for_error(self):
        FailureTask(self.transfer_coordinator)()

        # If another failure comes in, the result should still throw the
        # original exception when result() is eventually called.
        FailureTask(
            self.transfer_coordinator, main_kwargs={'exception': Exception}
        )()

        # Even if a success task comes along, the result of the future
        # should be the original exception
        SuccessTask(self.transfer_coordinator, is_final=True)()
        with self.assertRaises(TaskFailureException):
            self.transfer_coordinator.result()

    def test_done_callbacks_success(self):
        callback_results = []
        SuccessTask(
            self.transfer_coordinator,
            done_callbacks=[
                partial(callback_results.append, 'first'),
                partial(callback_results.append, 'second'),
            ],
        )()
        # For successful tasks, the done callbacks should get called.
        self.assertEqual(callback_results, ['first', 'second'])

    def test_done_callbacks_failure(self):
        callback_results = []
        FailureTask(
            self.transfer_coordinator,
            done_callbacks=[
                partial(callback_results.append, 'first'),
                partial(callback_results.append, 'second'),
            ],
        )()
        # For even failed tasks, the done callbacks should get called.
        self.assertEqual(callback_results, ['first', 'second'])

        # Callbacks should continue to be called even after a related failure
        SuccessTask(
            self.transfer_coordinator,
            done_callbacks=[
                partial(callback_results.append, 'third'),
                partial(callback_results.append, 'fourth'),
            ],
        )()
        self.assertEqual(
            callback_results, ['first', 'second', 'third', 'fourth']
        )

    def test_failure_cleanups_on_failure(self):
        callback_results = []
        self.transfer_coordinator.add_failure_cleanup(
            callback_results.append, 'first'
        )
        self.transfer_coordinator.add_failure_cleanup(
            callback_results.append, 'second'
        )
        FailureTask(self.transfer_coordinator)()
        # The failure callbacks should have not been called yet because it
        # is not the last task
        self.assertEqual(callback_results, [])

        # Now the failure callbacks should get called.
        SuccessTask(self.transfer_coordinator, is_final=True)()
        self.assertEqual(callback_results, ['first', 'second'])

    def test_no_failure_cleanups_on_success(self):
        callback_results = []
        self.transfer_coordinator.add_failure_cleanup(
            callback_results.append, 'first'
        )
        self.transfer_coordinator.add_failure_cleanup(
            callback_results.append, 'second'
        )
        SuccessTask(self.transfer_coordinator, is_final=True)()
        # The failure cleanups should not have been called because no task
        # failed for the transfer context.
        self.assertEqual(callback_results, [])

    def test_passing_main_kwargs(self):
        main_kwargs = {'foo': 'bar', 'baz': 'biz'}
        ReturnKwargsTask(
            self.transfer_coordinator, main_kwargs=main_kwargs, is_final=True
        )()
        # The kwargs should have been passed to the main()
        self.assertEqual(self.transfer_coordinator.result(), main_kwargs)

    def test_passing_pending_kwargs_single_futures(self):
        pending_kwargs = {}
        ref_main_kwargs = {'foo': 'bar', 'baz': 'biz'}

        # Pass some tasks to an executor
        with futures.ThreadPoolExecutor(1) as executor:
            pending_kwargs['foo'] = executor.submit(
                SuccessTask(
                    self.transfer_coordinator,
                    main_kwargs={'return_value': ref_main_kwargs['foo']},
                )
            )
            pending_kwargs['baz'] = executor.submit(
                SuccessTask(
                    self.transfer_coordinator,
                    main_kwargs={'return_value': ref_main_kwargs['baz']},
                )
            )

        # Create a task that depends on the tasks passed to the executor
        ReturnKwargsTask(
            self.transfer_coordinator,
            pending_main_kwargs=pending_kwargs,
            is_final=True,
        )()
        # The result should have the pending keyword arg values flushed
        # out.
        self.assertEqual(self.transfer_coordinator.result(), ref_main_kwargs)

    def test_passing_pending_kwargs_list_of_futures(self):
        pending_kwargs = {}
        ref_main_kwargs = {'foo': ['first', 'second']}

        # Pass some tasks to an executor
        with futures.ThreadPoolExecutor(1) as executor:
            first_future = executor.submit(
                SuccessTask(
                    self.transfer_coordinator,
                    main_kwargs={'return_value': ref_main_kwargs['foo'][0]},
                )
            )
            second_future = executor.submit(
                SuccessTask(
                    self.transfer_coordinator,
                    main_kwargs={'return_value': ref_main_kwargs['foo'][1]},
                )
            )
            # Make the pending keyword arg value a list
            pending_kwargs['foo'] = [first_future, second_future]

        # Create a task that depends on the tasks passed to the executor
        ReturnKwargsTask(
            self.transfer_coordinator,
            pending_main_kwargs=pending_kwargs,
            is_final=True,
        )()
        # The result should have the pending keyword arg values flushed
        # out in the expected order.
        self.assertEqual(self.transfer_coordinator.result(), ref_main_kwargs)

    def test_passing_pending_and_non_pending_kwargs(self):
        main_kwargs = {'nonpending_value': 'foo'}
        pending_kwargs = {}
        ref_main_kwargs = {
            'nonpending_value': 'foo',
            'pending_value': 'bar',
            'pending_list': ['first', 'second'],
        }

        # Create the pending tasks
        with futures.ThreadPoolExecutor(1) as executor:
            pending_kwargs['pending_value'] = executor.submit(
                SuccessTask(
                    self.transfer_coordinator,
                    main_kwargs={
                        'return_value': ref_main_kwargs['pending_value']
                    },
                )
            )

            first_future = executor.submit(
                SuccessTask(
                    self.transfer_coordinator,
                    main_kwargs={
                        'return_value': ref_main_kwargs['pending_list'][0]
                    },
                )
            )
            second_future = executor.submit(
                SuccessTask(
                    self.transfer_coordinator,
                    main_kwargs={
                        'return_value': ref_main_kwargs['pending_list'][1]
                    },
                )
            )
            # Make the pending keyword arg value a list
            pending_kwargs['pending_list'] = [first_future, second_future]

        # Create a task that depends on the tasks passed to the executor
        # and just regular nonpending kwargs.
        ReturnKwargsTask(
            self.transfer_coordinator,
            main_kwargs=main_kwargs,
            pending_main_kwargs=pending_kwargs,
            is_final=True,
        )()
        # The result should have all of the kwargs (both pending and
        # nonpending)
        self.assertEqual(self.transfer_coordinator.result(), ref_main_kwargs)

    def test_single_failed_pending_future(self):
        pending_kwargs = {}

        # Pass some tasks to an executor. Make one successful and the other
        # a failure.
        with futures.ThreadPoolExecutor(1) as executor:
            pending_kwargs['foo'] = executor.submit(
                SuccessTask(
                    self.transfer_coordinator,
                    main_kwargs={'return_value': 'bar'},
                )
            )
            pending_kwargs['baz'] = executor.submit(
                FailureTask(self.transfer_coordinator)
            )

        # Create a task that depends on the tasks passed to the executor
        ReturnKwargsTask(
            self.transfer_coordinator,
            pending_main_kwargs=pending_kwargs,
            is_final=True,
        )()
        # The end result should raise the exception from the initial
        # pending future value
        with self.assertRaises(TaskFailureException):
            self.transfer_coordinator.result()

    def test_single_failed_pending_future_in_list(self):
        pending_kwargs = {}

        # Pass some tasks to an executor. Make one successful and the other
        # a failure.
        with futures.ThreadPoolExecutor(1) as executor:
            first_future = executor.submit(
                SuccessTask(
                    self.transfer_coordinator,
                    main_kwargs={'return_value': 'bar'},
                )
            )
            second_future = executor.submit(
                FailureTask(self.transfer_coordinator)
            )

            pending_kwargs['pending_list'] = [first_future, second_future]

        # Create a task that depends on the tasks passed to the executor
        ReturnKwargsTask(
            self.transfer_coordinator,
            pending_main_kwargs=pending_kwargs,
            is_final=True,
        )()
        # The end result should raise the exception from the initial
        # pending future value in the list
        with self.assertRaises(TaskFailureException):
            self.transfer_coordinator.result()


class BaseMultipartTaskTest(BaseTaskTest):
    def setUp(self):
        super().setUp()
        self.bucket = 'mybucket'
        self.key = 'foo'


class TestCreateMultipartUploadTask(BaseMultipartTaskTest):
    def test_main(self):
        upload_id = 'foo'
        extra_args = {'Metadata': {'foo': 'bar'}}
        response = {'UploadId': upload_id}
        task = self.get_task(
            CreateMultipartUploadTask,
            main_kwargs={
                'client': self.client,
                'bucket': self.bucket,
                'key': self.key,
                'extra_args': extra_args,
            },
        )
        self.stubber.add_response(
            method='create_multipart_upload',
            service_response=response,
            expected_params={
                'Bucket': self.bucket,
                'Key': self.key,
                'Metadata': {'foo': 'bar'},
            },
        )
        result_id = task()
        self.stubber.assert_no_pending_responses()
        # Ensure the upload id returned is correct
        self.assertEqual(upload_id, result_id)

        # Make sure that the abort was added as a cleanup failure
        self.assertEqual(len(self.transfer_coordinator.failure_cleanups), 1)

        # Make sure if it is called, it will abort correctly
        self.stubber.add_response(
            method='abort_multipart_upload',
            service_response={},
            expected_params={
                'Bucket': self.bucket,
                'Key': self.key,
                'UploadId': upload_id,
            },
        )
        self.transfer_coordinator.failure_cleanups[0]()
        self.stubber.assert_no_pending_responses()


class TestCompleteMultipartUploadTask(BaseMultipartTaskTest):
    def test_main(self):
        upload_id = 'my-id'
        parts = [{'ETag': 'etag', 'PartNumber': 0}]
        task = self.get_task(
            CompleteMultipartUploadTask,
            main_kwargs={
                'client': self.client,
                'bucket': self.bucket,
                'key': self.key,
                'upload_id': upload_id,
                'parts': parts,
                'extra_args': {},
            },
        )
        self.stubber.add_response(
            method='complete_multipart_upload',
            service_response={},
            expected_params={
                'Bucket': self.bucket,
                'Key': self.key,
                'UploadId': upload_id,
                'MultipartUpload': {'Parts': parts},
            },
        )
        task()
        self.stubber.assert_no_pending_responses()

    def test_includes_extra_args(self):
        upload_id = 'my-id'
        parts = [{'ETag': 'etag', 'PartNumber': 0}]
        task = self.get_task(
            CompleteMultipartUploadTask,
            main_kwargs={
                'client': self.client,
                'bucket': self.bucket,
                'key': self.key,
                'upload_id': upload_id,
                'parts': parts,
                'extra_args': {'RequestPayer': 'requester'},
            },
        )
        self.stubber.add_response(
            method='complete_multipart_upload',
            service_response={},
            expected_params={
                'Bucket': self.bucket,
                'Key': self.key,
                'UploadId': upload_id,
                'MultipartUpload': {'Parts': parts},
                'RequestPayer': 'requester',
            },
        )
        task()
        self.stubber.assert_no_pending_responses()
