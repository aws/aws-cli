# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Where a profile keeps its credentials: in the credential daemon or in
files.

``credential_storage = daemon`` or ``file`` records the customer's answer to
the question about moving a profile to the credential daemon. The answer is
saved on the profile. ``AWS_CREDENTIAL_STORAGE`` overrides it. Like every CLI
setting, it isn't inherited from ``[default]``.
"""
