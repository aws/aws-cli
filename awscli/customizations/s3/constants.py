# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
MULTI_THRESHOLD = 8 * (1024 ** 2)
CHUNKSIZE = 7 * (1024 ** 2)
NUM_THREADS = 10
QUEUE_TIMEOUT_GET = 1.0
QUEUE_TIMEOUT_WAIT = 0.2
MAX_PARTS = 950
MAX_SINGLE_UPLOAD_SIZE = 5 * (1024 ** 3)
MAX_UPLOAD_SIZE = 5 * (1024 ** 4)
MAX_QUEUE_SIZE = 1000
