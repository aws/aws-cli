# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class SupplyChainError(Exception):
    """Base exception for supply chain commands"""
    pass


class SBOMGenerationError(SupplyChainError):
    """Exception raised when SBOM generation fails"""
    pass


class ScanError(SupplyChainError):
    """Exception raised when vulnerability scanning fails"""
    pass


class AttestationError(SupplyChainError):
    """Exception raised when attestation operations fail"""
    pass


class PolicyViolationError(SupplyChainError):
    """Exception raised when a supply chain policy is violated"""
    pass


class ResourceNotFoundError(SupplyChainError):
    """Exception raised when a requested resource is not found"""
    pass


class InvalidFormatError(SupplyChainError):
    """Exception raised when an invalid format is specified"""
    pass


class UploadError(SupplyChainError):
    """Exception raised when uploading to S3 fails"""
    pass