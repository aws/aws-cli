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

from awscli.testutils import unittest
from awscli.testutils import BaseAWSCommandParamsTest


class TestGetApplicationRevisionLocationArguments(
        BaseAWSCommandParamsTest):

    prefix = 'deploy get-application-revision --application-name foo '

    def test_s3_location(self):
        cmd = self.prefix + '--s3-location bucket=b,key=k,bundleType=zip'
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_etag(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,eTag=1234')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_version(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,version=abcd')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_etag_and_version(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,eTag=1234,version=abcd')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_json(self):
        cmd = self.prefix + (
            '--s3-location {"bucket":"b","key":"k",'
            '"bundleType":"zip","eTag":"1234","version":"abcd"}')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_missing_bucket(self):
        cmd = self.prefix + (
            '--s3-location key=k,'
            'bundleType=zip,eTag=1234,version=abcd')
        self.run_cmd(cmd, 255)

    def test_s3_location_missing_key(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,'
            'bundleType=zip,eTag=1234,version=abcd')
        self.run_cmd(cmd, 255)

    def test_github_location_with_etag(self):
        cmd = self.prefix + (
            '--github-location repository=foo/bar,'
            'commitId=1234')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'GitHub',
                'gitHubLocation': {
                    'repository': 'foo/bar',
                    'commitId': '1234',
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_github_location_json(self):
        cmd = self.prefix + (
            '--github-location {"repository":"foo/bar",'
            '"commitId":"1234"}')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'GitHub',
                'gitHubLocation': {
                    'repository': 'foo/bar',
                    'commitId': '1234',
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_github_location_missing_repository(self):
        cmd = self.prefix + (
            '--github-location '
            'commitId=1234')
        self.run_cmd(cmd, 255)

    def test_github_location_missing_commit_id(self):
        cmd = self.prefix + '--github-location repository=foo/bar'
        self.run_cmd(cmd, 255)


class TestRegisterApplicationRevisionLocationArguments(
        BaseAWSCommandParamsTest):

    prefix = 'deploy register-application-revision --application-name foo '

    def test_s3_location(self):
        cmd = self.prefix + '--s3-location bucket=b,key=k,bundleType=zip'
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_etag(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,eTag=1234')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_version(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,version=abcd')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_etag_and_version(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,eTag=1234,version=abcd')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_json(self):
        cmd = self.prefix + (
            '--s3-location {"bucket":"b","key":"k",'
            '"bundleType":"zip","eTag":"1234","version":"abcd"}')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_missing_bucket(self):
        cmd = self.prefix + (
            '--s3-location key=k,'
            'bundleType=zip,eTag=1234,version=abcd')
        self.run_cmd(cmd, 255)

    def test_s3_location_missing_key(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,'
            'bundleType=zip,eTag=1234,version=abcd')
        self.run_cmd(cmd, 255)

    def test_github_location_with_etag(self):
        cmd = self.prefix + (
            '--github-location repository=foo/bar,'
            'commitId=1234')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'GitHub',
                'gitHubLocation': {
                    'repository': 'foo/bar',
                    'commitId': '1234',
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_github_location_json(self):
        cmd = self.prefix + (
            '--github-location {"repository":"foo/bar",'
            '"commitId":"1234"}')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'GitHub',
                'gitHubLocation': {
                    'repository': 'foo/bar',
                    'commitId': '1234',
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_github_location_missing_repository(self):
        cmd = self.prefix + (
            '--github-location '
            'commitId=1234')
        self.run_cmd(cmd, 255)

    def test_github_location_missing_commit_id(self):
        cmd = self.prefix + '--github-location repository=foo/bar'
        self.run_cmd(cmd, 255)


class TestCreateDeploymentLocationArguments(
        BaseAWSCommandParamsTest):

    prefix = (
        'deploy create-deployment --application-name foo '
        '--deployment-group bar ')

    def test_s3_location(self):
        cmd = self.prefix + '--s3-location bucket=b,key=k,bundleType=zip'
        result = {
            'applicationName': 'foo',
            'deploymentGroupName': 'bar',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_etag(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,eTag=1234')
        result = {
            'applicationName': 'foo',
            'deploymentGroupName': 'bar',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_version(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,version=abcd')
        result = {
            'applicationName': 'foo',
            'deploymentGroupName': 'bar',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_etag_and_version(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,eTag=1234,version=abcd')
        result = {
            'applicationName': 'foo',
            'deploymentGroupName': 'bar',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_json(self):
        cmd = self.prefix + (
            '--s3-location {"bucket":"b","key":"k",'
            '"bundleType":"zip","eTag":"1234","version":"abcd"}')
        result = {
            'applicationName': 'foo',
            'deploymentGroupName': 'bar',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_missing_bucket(self):
        cmd = self.prefix + (
            '--s3-location key=k,'
            'bundleType=zip,eTag=1234,version=abcd')
        self.run_cmd(cmd, 255)

    def test_s3_location_missing_key(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,'
            'bundleType=zip,eTag=1234,version=abcd')
        self.run_cmd(cmd, 255)

    def test_github_location_with_etag(self):
        cmd = self.prefix + (
            '--github-location repository=foo/bar,'
            'commitId=1234')
        result = {
            'applicationName': 'foo',
            'deploymentGroupName': 'bar',
            'revision': {
                'revisionType': 'GitHub',
                'gitHubLocation': {
                    'repository': 'foo/bar',
                    'commitId': '1234',
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_github_location_json(self):
        cmd = self.prefix + (
            '--github-location {"repository":"foo/bar",'
            '"commitId":"1234"}')
        result = {
            'applicationName': 'foo',
            'deploymentGroupName': 'bar',
            'revision': {
                'revisionType': 'GitHub',
                'gitHubLocation': {
                    'repository': 'foo/bar',
                    'commitId': '1234',
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_github_location_missing_repository(self):
        cmd = self.prefix + (
            '--github-location '
            'commitId=1234')
        self.run_cmd(cmd, 255)

    def test_github_location_missing_commit_id(self):
        cmd = self.prefix + '--github-location repository=foo/bar'
        self.run_cmd(cmd, 255)


if __name__ == "__main__":
    unittest.main()
