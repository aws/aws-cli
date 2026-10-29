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
"""Shared mechanism for read-only, multi-call aggregating CLI commands.

Some services expose an operational question that no single API answers: "run
this query to completion and give me every row", "investigate this alarm", "tell
me why this service is unhealthy". Answering it means several read-only API
calls, bounded polling, and one summarized result. This package provides that
common machinery so each such command stays a thin, service-scoped verb:

* :mod:`helpers` -- a read-only botocore ``call`` wrapper (errors as data, refuses
  any mutating operation), plain-dict result factories, and a JSON emitter that
  maps a result to a CLI exit code.
* :mod:`poll` -- :class:`~.poll.BoundedPoller`, a monotonic, bounded poll clock
  with capped backoff for start-query/poll lifecycles that have no botocore waiter.
* :mod:`output` -- output caps (field truncation, series capping) that record
  every clamp so trimming is visible, never silent.

Nothing here is service-specific; the commands live under their owning service's
customization namespace and build on these primitives. The service-specific name
resolvers that used to live here now live with their owning commands (Athena's
workgroup resolver and CloudWatch's alarm resolver).
"""
