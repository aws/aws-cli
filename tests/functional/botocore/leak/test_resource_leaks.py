# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests import BaseClientDriverTest


class TestDoesNotLeakMemory(BaseClientDriverTest):
    # The user doesn't need to have credentials configured
    # in order to run the functional tests for resource leaks.
    # If we don't set this value and a user doesn't have creds
    # configured, each create_client() call will have to go through
    # the EC2 Instance Metadata provider's timeout, which can add
    # a substantial amount of time to the total test run time.
    INJECT_DUMMY_CREDS = True
    # We're making up numbers here, but let's say arbitrarily
    # that the memory can't increase by more than 10MB.
    MAX_GROWTH_BYTES = 10 * 1024 * 1024

    def test_create_single_client_memory_constant(self):
        self.cmd('create_client', 's3')
        self.cmd('free_clients')
        self.record_memory()
        for _ in range(100):
            self.cmd('create_client', 's3')
            self.cmd('free_clients')
        self.record_memory()
        start, end = self.memory_samples
        self.assertTrue((end - start) < self.MAX_GROWTH_BYTES, (end - start))

    def test_create_memory_clients_in_loop(self):
        # We need to first create clients and free then before
        # recording our memory samples.  This is because of two reasons:
        # 1. Caching.  Some of the botocore internals will cache data, so
        #    the first client created will consume more memory than subsequent
        #    clients.  We're interested in growing memory, not total
        #    memory usage (for now), so we we care about the memory in the
        #    steady state case.
        # 2. Python memory allocation.  Due to how python allocates memory
        #    via it's small object allocator, arena's aren't freed until the
        #    entire 256kb isn't in use.  If a single allocation in a single
        #    pool in a single arena is still in use, the arena is not
        #    freed.  This case is easy to hit, and pretty much any
        #    fragmentation guarantees this case is hit.  The best we can
        #    do is verify that memory that's released back to python's
        #    allocator (but not to the OS) is at least reused in subsequent
        #    requests to create botocore clients.
        self.cmd('create_multiple_clients', '200', 's3')
        self.cmd('free_clients')
        self.record_memory()
        # 500 clients in batches of 50.
        for _ in range(10):
            self.cmd('create_multiple_clients', '50', 's3')
            self.cmd('free_clients')
        self.record_memory()
        start, end = self.memory_samples
        self.assertTrue((end - start) < self.MAX_GROWTH_BYTES, (end - start))

    def test_create_single_waiter_memory_constant(self):
        self.cmd('create_waiter', 's3', 'bucket_exists')
        self.cmd('free_waiters')
        self.record_memory()
        for _ in range(100):
            self.cmd('create_waiter', 's3', 'bucket_exists')
            self.cmd('free_waiters')
        self.record_memory()
        start, end = self.memory_samples
        self.assertTrue((end - start) < self.MAX_GROWTH_BYTES, (end - start))

    def test_create_memory_waiters_in_loop(self):
        # See ``test_create_memory_clients_in_loop`` to understand why
        # waiters are first initialized and then freed. Same reason applies.
        self.cmd('create_multiple_waiters', '200', 's3', 'bucket_exists')
        self.cmd('free_waiters')
        self.record_memory()
        # 500 waiters in batches of 50.
        for _ in range(10):
            self.cmd(
                'create_multiple_waiters', '50', 's3', 'bucket_exists')
            self.cmd('free_waiters')
        self.record_memory()
        start, end = self.memory_samples
        self.assertTrue((end - start) < self.MAX_GROWTH_BYTES, (end - start))

    def test_create_single_paginator_memory_constant(self):
        self.cmd('create_paginator', 's3', 'list_objects')
        self.cmd('free_paginators')
        self.record_memory()
        for _ in range(100):
            self.cmd('create_paginator', 's3', 'list_objects')
            self.cmd('free_paginators')
        self.record_memory()
        start, end = self.memory_samples
        self.assertTrue((end - start) < self.MAX_GROWTH_BYTES, (end - start))

    def test_create_memory_paginators_in_loop(self):
        # See ``test_create_memory_clients_in_loop`` to understand why
        # paginators are first initialized and then freed. Same reason applies.
        self.cmd('create_multiple_paginators', '200', 's3', 'list_objects')
        self.cmd('free_paginators')
        self.record_memory()
        # 500 waiters in batches of 50.
        for _ in range(10):
            self.cmd(
                'create_multiple_paginators', '50', 's3', 'list_objects')
            self.cmd('free_paginators')
        self.record_memory()
        start, end = self.memory_samples
        self.assertTrue((end - start) < self.MAX_GROWTH_BYTES, (end - start))
