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

from awscli.argprocess import unpack_cli_arg
from awscli.arguments import CustomArgument
from awscli.arguments import create_argument_model_from_schema

S3_LOCATION_ARG_DESCRIPTION = {
    'name': 's3-location',
    'required': False,
    'help_text': (
        'Information about the location of the application revision in Amazon '
        'S3. You must specify the bucket, the key, and bundleType. '
        'Optionally, you can also specify an eTag and version.'
    )
}

S3_LOCATION_SCHEMA = {
    "type": "object",
    "properties": {
        "bucket": {
            "type": "string",
            "description": "The Amazon S3 bucket name.",
            "required": True
        },
        "key": {
            "type": "string",
            "description": "The Amazon S3 object key name.",
            "required": True
        },
        "bundleType": {
            "type": "string",
            "description": "The format of the bundle stored in Amazon S3.",
            "enum": ["tar", "tgz", "zip"],
            "required": True
        },
        "eTag": {
            "type": "string",
            "description": "The Amazon S3 object eTag.",
            "required": False
        },
        "version": {
            "type": "string",
            "description": "The Amazon S3 object version.",
            "required": False
        }
    }
}

GITHUB_LOCATION_ARG_DESCRIPTION = {
    'name': 'github-location',
    'required': False,
    'help_text': (
        'Information about the location of the application revision in '
        'GitHub. You must specify the repository and commit ID that '
        'references the application revision. For the repository, use the '
        'format GitHub-account/repository-name or GitHub-org/repository-name. '
        'For the commit ID, use the SHA1 Git commit reference.'
    )
}

GITHUB_LOCATION_SCHEMA = {
    "type": "object",
    "properties": {
        "repository": {
            "type": "string",
            "description": (
                "The GitHub account or organization and repository. Specify "
                "as GitHub-account/repository or GitHub-org/repository."
            ),
            "required": True
        },
        "commitId": {
            "type": "string",
            "description": "The SHA1 Git commit reference.",
            "required": True
        }
    }
}


def modify_revision_arguments(argument_table, session, **kwargs):
    s3_model = create_argument_model_from_schema(S3_LOCATION_SCHEMA)
    argument_table[S3_LOCATION_ARG_DESCRIPTION['name']] = (
        S3LocationArgument(
            argument_model=s3_model,
            session=session,
            **S3_LOCATION_ARG_DESCRIPTION
        )
    )
    github_model = create_argument_model_from_schema(GITHUB_LOCATION_SCHEMA)
    argument_table[GITHUB_LOCATION_ARG_DESCRIPTION['name']] = (
        GitHubLocationArgument(
            argument_model=github_model,
            session=session,
            **GITHUB_LOCATION_ARG_DESCRIPTION
        )
    )
    argument_table['revision'].required = False


class LocationArgument(CustomArgument):
    def __init__(self, session, *args, **kwargs):
        super(LocationArgument, self).__init__(*args, **kwargs)
        self._session = session

    def add_to_params(self, parameters, value):
        if value is None:
            return
        parsed = self._session.emit_first_non_none_response(
            'process-cli-arg.codedeploy.%s' % self.name,
            param=self.argument_model,
            cli_argument=self,
            value=value,
            operation=None
        )
        if parsed is None:
            parsed = unpack_cli_arg(self, value)
        parameters['revision'] = self.build_revision_location(parsed)

    def build_revision_location(self, value_dict):
        """
        Repack the input structure into a revisionLocation.
        """
        raise NotImplementedError("build_revision_location")


class S3LocationArgument(LocationArgument):
    def build_revision_location(self, value_dict):
        required = ['bucket', 'key', 'bundleType']
        valid = lambda k: value_dict.get(k, False)
        if not all(map(valid, required)):
            raise RuntimeError(
                '--s3-location must specify bucket, key and bundleType.'
            )
        revision = {
            "revisionType": "S3",
            "s3Location": {
                "bucket": value_dict['bucket'],
                "key": value_dict['key'],
                "bundleType": value_dict['bundleType']
            }
        }
        if 'eTag' in value_dict:
            revision['s3Location']['eTag'] = value_dict['eTag']
        if 'version' in value_dict:
            revision['s3Location']['version'] = value_dict['version']
        return revision


class GitHubLocationArgument(LocationArgument):
    def build_revision_location(self, value_dict):
        required = ['repository', 'commitId']
        valid = lambda k: value_dict.get(k, False)
        if not all(map(valid, required)):
            raise RuntimeError(
                '--github-location must specify repository and commitId.'
            )
        return {
            "revisionType": "GitHub",
            "gitHubLocation": {
                "repository": value_dict['repository'],
                "commitId": value_dict['commitId']
            }
        }
