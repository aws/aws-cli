# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class SigninError(Exception):
    """ Base class for all SigninErrors."""
    fmt = 'An unspecified error occurred'

    def __init__(self, **kwargs):
        msg = self.fmt.format(**kwargs)
        super(SigninError, self).__init__(msg)
        self.kwargs = kwargs


class NonTemporaryCredentialsError(SigninError):
    fmt = ("Error: The current profile contains long-term credentials. You may"
           " only signin with temporary credentials.")


class SessionDurationOutOfRangeError(SigninError):
    fmt = ("Error: The specified Session Duration must be 900 seconds (15"
           " minutes) to 43200 seconds (12 hours).")


class FederationResponseError(SigninError):
    fmt = "Error: AWS Federation Endpoint: {msg}"
