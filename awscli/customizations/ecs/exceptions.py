# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class ECSError(Exception):
    """ Base class for all ECSErrors."""
    fmt = 'An unspecified error occurred'

    def __init__(self, **kwargs):
        msg = self.fmt.format(**kwargs)
        super(ECSError, self).__init__(msg)
        self.kwargs = kwargs


class MissingPropertyError(ECSError):
    fmt = \
        "Error: Resource '{resource}' must include property '{prop_name}'"


class FileLoadError(ECSError):
    fmt = "Error: Unable to load file at {file_path}: {error}"


class InvalidPlatformError(ECSError):
    fmt = "Error: {resource} '{name}' must support 'ECS' compute platform"


class InvalidProperyError(ECSError):
    fmt = ("Error: deployment group '{dg_name}' does not target "
           "ECS {resource} '{resource_name}'")


class InvalidServiceError(ECSError):
    fmt = "Error: Service '{service}' not found in cluster '{cluster}'"


class ServiceClientError(ECSError):
    fmt = "Failed to {action}:\n{error}"