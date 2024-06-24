# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
import logging
import sys

from botocore.client import Config
from botocore.utils import is_s3express_bucket, ensure_boolean
from dateutil.parser import parse
from dateutil.tz import tzlocal

from awscli.compat import queue
from awscli.customizations.commands import BasicCommand
from awscli.customizations.s3.comparator import Comparator
from awscli.customizations.s3.fileinfobuilder import FileInfoBuilder
from awscli.customizations.s3.fileformat import FileFormat
from awscli.customizations.s3.filegenerator import FileGenerator
from awscli.customizations.s3.fileinfo import FileInfo
from awscli.customizations.s3.filters import create_filter
from awscli.customizations.s3.s3handler import S3TransferHandlerFactory
from awscli.customizations.s3.utils import find_bucket_key, AppendFilter, \
    find_dest_path_comp_key, human_readable_size, \
    RequestParamsMapper, split_s3_bucket_key, block_unsupported_resources, \
    S3PathResolver
from awscli.customizations.utils import uni_print
from awscli.customizations.s3.syncstrategy.base import MissingFileSync, \
    SizeAndLastModifiedSync, NeverSync
from awscli.customizations.s3 import transferconfig


LOGGER = logging.getLogger(__name__)


RECURSIVE = {'name': 'recursive', 'action': 'store_true', 'dest': 'dir_op',
             'help_text': (
                 "Command is performed on all files or objects "
                 "under the specified directory or prefix.")}


HUMAN_READABLE = {'name': 'human-readable', 'action': 'store_true',
                  'help_text': "Displays file sizes in human readable format."}


SUMMARIZE = {'name': 'summarize', 'action': 'store_true',
             'help_text': (
                 "Displays summary information "
                 "(number of objects, total size).")}


DRYRUN = {'name': 'dryrun', 'action': 'store_true',
          'help_text': (
              "Displays the operations that would be performed using the "
              "specified command without actually running them.")}


QUIET = {'name': 'quiet', 'action': 'store_true',
         'help_text': (
             "Does not display the operations performed from the specified "
             "command.")}


FORCE = {'name': 'force', 'action': 'store_true',
         'help_text': (
             "Deletes all objects in the bucket including the bucket itself. "
             "Note that versioned objects will not be deleted in this "
             "process which would cause the bucket deletion to fail because "
             "the bucket would not be empty. To delete versioned "
             "objects use the ``s3api delete-object`` command with "
             "the ``--version-id`` parameter.")}


FOLLOW_SYMLINKS = {'name': 'follow-symlinks', 'action': 'store_true',
                   'default': True, 'group_name': 'follow_symlinks',
                   'help_text': (
                       "Symbolic links are followed "
                       "only when uploading to S3 from the local filesystem. "
                       "Note that S3 does not support symbolic links, so the "
                       "contents of the link target are uploaded under the "
                       "name of the link. When neither ``--follow-symlinks`` "
                       "nor ``--no-follow-symlinks`` is specified, the default "
                       "is to follow symlinks.")}


NO_FOLLOW_SYMLINKS = {'name': 'no-follow-symlinks', 'action': 'store_false',
                      'dest': 'follow_symlinks', 'default': True,
                      'group_name': 'follow_symlinks'}


NO_GUESS_MIME_TYPE = {'name': 'no-guess-mime-type', 'action': 'store_false',
                      'dest': 'guess_mime_type', 'default': True,
                      'help_text': (
                          "Do not try to guess the mime type for "
                          "uploaded files.  By default the mime type of a "
                          "file is guessed when it is uploaded.")}


CONTENT_TYPE = {'name': 'content-type',
                'help_text': (
                    "Specify an explicit content type for this operation.  "
                    "This value overrides any guessed mime types.")}


EXCLUDE = {'name': 'exclude', 'action': AppendFilter, 'nargs': 1,
           'dest': 'filters',
           'help_text': (
               "Exclude all files or objects from the command that matches "
               "the specified pattern.")}


INCLUDE = {'name': 'include', 'action': AppendFilter, 'nargs': 1,
           'dest': 'filters',
           'help_text': (
               "Don't exclude files or objects "
               "in the command that match the specified pattern. "
               'See <a href="http://docs.aws.amazon.com/cli/latest/reference'
               '/s3/index.html#use-of-exclude-and-include-filters">Use of '
               'Exclude and Include Filters</a> for details.')}


ACL = {'name': 'acl',
       'choices': ['private', 'public-read', 'public-read-write',
                   'authenticated-read', 'aws-exec-read', 'bucket-owner-read',
                   'bucket-owner-full-control', 'log-delivery-write'],
       'help_text': (
           "Sets the ACL for the object when the command is "
           "performed.  If you use this parameter you must have the "
           '"s3:PutObjectAcl" permission included in the list of actions '
           "for your IAM policy. "
           "Only accepts values of ``private``, ``public-read``, "
           "``public-read-write``, ``authenticated-read``, ``aws-exec-read``, "
           "``bucket-owner-read``, ``bucket-owner-full-control`` and "
           "``log-delivery-write``. "
           'See <a href="http://docs.aws.amazon.com/AmazonS3/latest/dev/'
           'acl-overview.html#canned-acl">Canned ACL</a> for details')}


GRANTS = {
    'name': 'grants', 'nargs': '+',
    'help_text': (
        '<p>Grant specific permissions to individual users or groups. You '
        'can supply a list of grants of the form</p><codeblock>--grants '
        'Permission=Grantee_Type=Grantee_ID [Permission=Grantee_Type='
        'Grantee_ID ...]</codeblock>To specify the same permission type '
        'for multiple '
        'grantees, specify the permission as such as <codeblock>--grants '
        'Permission=Grantee_Type=Grantee_ID,Grantee_Type=Grantee_ID,...'
        '</codeblock>Each value contains the following elements:'
        '<ul><li><code>Permission</code> - Specifies '
        'the granted permissions, and can be set to read, readacl, '
        'writeacl, or full.</li><li><code>Grantee_Type</code> - '
        'Specifies how the grantee is to be identified, and can be set '
        'to uri or id.</li><li><code>Grantee_ID</code> - '
        'Specifies the grantee based on Grantee_Type. The '
        '<code>Grantee_ID</code> value can be one of:<ul><li><b>uri</b> '
        '- The group\'s URI. For more information, see '
        '<a href="http://docs.aws.amazon.com/AmazonS3/latest/dev/'
        'ACLOverview.html#SpecifyingGrantee">'
        'Who Is a Grantee?</a></li>'
        '<li><b>id</b> - The account\'s canonical ID</li></ul>'
        '</li></ul>'
        'For more information on Amazon S3 access control, see '
        '<a href="http://docs.aws.amazon.com/AmazonS3/latest/dev/'
        'UsingAuthAccess.html">Access Control</a>')}


SSE = {
    'name': 'sse', 'nargs': '?', 'const': 'AES256',
    'choices': ['AES256', 'aws:kms'],
    'help_text': (
        'Specifies server-side encryption of the object in S3. '
        'Valid values are ``AES256`` and ``aws:kms``. If the parameter is '
        'specified but no value is provided, ``AES256`` is used.'
    )
}


SSE_C = {
    'name': 'sse-c', 'nargs': '?', 'const': 'AES256', 'choices': ['AES256'],
    'help_text': (
        'Specifies server-side encryption using customer provided keys '
        'of the the object in S3. ``AES256`` is the only valid value. '
        'If the parameter is specified but no value is provided, '
        '``AES256`` is used. If you provide this value, ``--sse-c-key`` '
        'must be specified as well.'
    )
}


SSE_C_KEY = {
    'name': 'sse-c-key', 'cli_type_name': 'blob',
    'help_text': (
        'The customer-provided encryption key to use to server-side '
        'encrypt the object in S3. If you provide this value, '
        '``--sse-c`` must be specified as well. The key provided should '
        '**not** be base64 encoded.'
    )
}


SSE_KMS_KEY_ID = {
    'name': 'sse-kms-key-id',
    'help_text': (
        'The customer-managed AWS Key Management Service (KMS) key ID that '
        'should be used to server-side encrypt the object in S3. You should '
        'only provide this parameter if you are using a customer managed '
        'customer master key (CMK) and not the AWS managed KMS CMK.'
    )
}


SSE_C_COPY_SOURCE = {
    'name': 'sse-c-copy-source', 'nargs': '?',
    'const': 'AES256', 'choices': ['AES256'],
    'help_text': (
        'This parameter should only be specified when copying an S3 object '
        'that was encrypted server-side with a customer-provided '
        'key. It specifies the algorithm to use when decrypting the source '
        'object. ``AES256`` is the only valid '
        'value. If the parameter is specified but no value is provided, '
        '``AES256`` is used. If you provide this value, '
        '``--sse-c-copy-source-key`` must be specified as well. '
    )
}


SSE_C_COPY_SOURCE_KEY = {
    'name': 'sse-c-copy-source-key', 'cli_type_name': 'blob',
    'help_text': (
        'This parameter should only be specified when copying an S3 object '
        'that was encrypted server-side with a customer-provided '
        'key. Specifies the customer-provided encryption key for Amazon S3 '
        'to use to decrypt the source object. The encryption key provided '
        'must be one that was used when the source object was created. '
        'If you provide this value, ``--sse-c-copy-source`` be specified as '
        'well. The key provided should **not** be base64 encoded.'
    )
}


STORAGE_CLASS = {'name': 'storage-class',
                 'choices': ['STANDARD', 'REDUCED_REDUNDANCY', 'STANDARD_IA',
                             'ONEZONE_IA', 'INTELLIGENT_TIERING', 'GLACIER',
                             'DEEP_ARCHIVE', 'GLACIER_IR'],
                 'help_text': (
                     "The type of storage to use for the object. "
                     "Valid choices are: STANDARD | REDUCED_REDUNDANCY "
                     "| STANDARD_IA | ONEZONE_IA | INTELLIGENT_TIERING "
                     "| GLACIER | DEEP_ARCHIVE | GLACIER_IR. "
                     "Defaults to 'STANDARD'")}


WEBSITE_REDIRECT = {'name': 'website-redirect',
                    'help_text': (
                        "If the bucket is configured as a website, "
                        "redirects requests for this object to another object "
                        "in the same bucket or to an external URL. Amazon S3 "
                        "stores the value of this header in the object "
                        "metadata.")}


CACHE_CONTROL = {'name': 'cache-control',
                 'help_text': (
                     "Specifies caching behavior along the "
                     "request/reply chain.")}


CONTENT_DISPOSITION = {'name': 'content-disposition',
                       'help_text': (
                           "Specifies presentational information "
                           "for the object.")}


CONTENT_ENCODING = {'name': 'content-encoding',
                    'help_text': (
                        "Specifies what content encodings have been "
                        "applied to the object and thus what decoding "
                        "mechanisms must be applied to obtain the media-type "
                        "referenced by the Content-Type header field.")}


CONTENT_LANGUAGE = {'name': 'content-language',
                    'help_text': ("The language the content is in.")}


SOURCE_REGION = {'name': 'source-region',
                 'help_text': (
                     "When transferring objects from an s3 bucket to an s3 "
                     "bucket, this specifies the region of the source bucket."
                     " Note the region specified by ``--region`` or through "
                     "configuration of the CLI refers to the region of the "
                     "destination bucket.  If ``--source-region`` is not "
                     "specified the region of the source will be the same "
                     "as the region of the destination bucket.")}


EXPIRES = {
    'name': 'expires',
    'help_text': (
        "The date and time at which the object is no longer cacheable.")
}


METADATA = {
    'name': 'metadata', 'cli_type_name': 'map',
    'schema': {
        'type': 'map',
        'key': {'type': 'string'},
        'value': {'type': 'string'}
    },
    'help_text': (
        "A map of metadata to store with the objects in S3. This will be "
        "applied to every object which is part of this request. In a sync, this "
        "means that files which haven't changed won't receive the new metadata. "
        "When copying between two s3 locations, the metadata-directive "
        "argument will default to 'REPLACE' unless otherwise specified."
    )
}


METADATA_DIRECTIVE = {
    'name': 'metadata-directive', 'choices': ['COPY', 'REPLACE'],
    'help_text': (
        'Specifies whether the metadata is copied from the source object '
        'or replaced with metadata provided when copying S3 objects. '
        'Note that if the object is copied over in parts, the source '
        'object\'s metadata will not be copied over, no matter the value for '
        '``--metadata-directive``, and instead the desired metadata values '
        'must be specified as parameters on the command line. '
        'Valid values are ``COPY`` and ``REPLACE``. If this parameter is not '
        'specified, ``COPY`` will be used by default. If ``REPLACE`` is used, '
        'the copied object will only have the metadata values that were'
        ' specified by the CLI command. Note that if you are '
        'using any of the following parameters: ``--content-type``, '
        '``content-language``, ``--content-encoding``, '
        '``--content-disposition``, ``--cache-control``, or ``--expires``, you '
        'will need to specify ``--metadata-directive REPLACE`` for '
        'non-multipart copies if you want the copied objects to have the '
        'specified metadata values.')
}


INDEX_DOCUMENT = {'name': 'index-document',
                  'help_text': (
                      'A suffix that is appended to a request that is for '
                      'a directory on the website endpoint (e.g. if the '
                      'suffix is index.html and you make a request to '
                      'samplebucket/images/ the data that is returned '
                      'will be for the object with the key name '
                      'images/index.html) The suffix must not be empty and '
                      'must not include a slash character.')}


ERROR_DOCUMENT = {'name': 'error-document',
                  'help_text': (
                      'The object key name to use when '
                      'a 4XX class error occurs.')}


ONLY_SHOW_ERRORS = {'name': 'only-show-errors', 'action': 'store_true',
                    'help_text': (
                        'Only errors and warnings are displayed. All other '
                        'output is suppressed.')}


NO_PROGRESS = {'name': 'no-progress',
               'action': 'store_false',
               'dest': 'progress',
               'help_text': (
                   'File transfer progress is not displayed. This flag '
                   'is only applied when the quiet and only-show-errors '
                   'flags are not provided.')}


EXPECTED_SIZE = {'name': 'expected-size',
                 'help_text': (
                     'This argument specifies the expected size of a stream '
                     'in terms of bytes. Note that this argument is needed '
                     'only when a stream is being uploaded to s3 and the size '
                     'is larger than 50GB.  Failure to include this argument '
                     'under these conditions may result in a failed upload '
                     'due to too many parts in upload.')}


PAGE_SIZE = {'name': 'page-size', 'cli_type_name': 'integer',
             'help_text': (
                 'The number of results to return in each response to a list '
                 'operation. The default value is 1000 (the maximum allowed). '
                 'Using a lower value may help if an operation times out.')}


IGNORE_GLACIER_WARNINGS = {
    'name': 'ignore-glacier-warnings', 'action': 'store_true',
    'help_text': (
        'Turns off glacier warnings. Warnings about an operation that cannot '
        'be performed because it involves copying, downloading, or moving '
        'a glacier object will no longer be printed to standard error and '
        'will no longer cause the return code of the command to be ``2``.'
    )
}


FORCE_GLACIER_TRANSFER = {
    'name': 'force-glacier-transfer', 'action': 'store_true',
    'help_text': (
        'Forces a transfer request on all Glacier objects in a sync or '
        'recursive copy.'
    )
}

REQUEST_PAYER = {
    'name': 'request-payer', 'choices': ['requester'],
    'nargs': '?', 'const': 'requester',
    'help_text': (
        'Confirms that the requester knows that they will be charged '
        'for the request. Bucket owners need not specify this parameter in '
        'their requests. Documentation on downloading objects from requester '
        'pays buckets can be found at '
        'http://docs.aws.amazon.com/AmazonS3/latest/dev/'
        'ObjectsinRequesterPaysBuckets.html'
    )
}

VALIDATE_SAME_S3_PATHS = {
    'name': 'validate-same-s3-paths', 'action': 'store_true',
    'help_text': (
        'Resolves the source and destination S3 URIs to their '
        'underlying buckets and verifies that the file or object '
        'is not being moved onto itself. If you are using any type '
        'of access point ARNs or access point aliases in your S3 URIs, '
        'we strongly recommended using this parameter to help prevent '
        'accidental deletions of the source file or object. This '
        'parameter resolves the underlying buckets of S3 access point '
        'ARNs and aliases, S3 on Outposts access point ARNs, and '
        'Multi-Region Access Point ARNs. S3 on Outposts access point '
        'aliases are not supported. Instead of using this parameter, '
        'you can set the environment variable '
        '``AWS_CLI_S3_MV_VALIDATE_SAME_S3_PATHS`` to ``true``. '
        'NOTE: Path validation requires making additional API calls. '
        'Future updates to this path-validation mechanism might change '
        'which API calls are made.'
    )
}

TRANSFER_ARGS = [DRYRUN, QUIET, INCLUDE, EXCLUDE, ACL,
                 FOLLOW_SYMLINKS, NO_FOLLOW_SYMLINKS, NO_GUESS_MIME_TYPE,
                 SSE, SSE_C, SSE_C_KEY, SSE_KMS_KEY_ID, SSE_C_COPY_SOURCE,
                 SSE_C_COPY_SOURCE_KEY, STORAGE_CLASS, GRANTS,
                 WEBSITE_REDIRECT, CONTENT_TYPE, CACHE_CONTROL,
                 CONTENT_DISPOSITION, CONTENT_ENCODING, CONTENT_LANGUAGE,
                 EXPIRES, SOURCE_REGION, ONLY_SHOW_ERRORS, NO_PROGRESS,
                 PAGE_SIZE, IGNORE_GLACIER_WARNINGS, FORCE_GLACIER_TRANSFER,
                 REQUEST_PAYER]


def get_client(session, region, endpoint_url, verify, config=None):
    return session.create_client('s3', region_name=region,
                                 endpoint_url=endpoint_url, verify=verify,
                                 config=config)


class S3Command(BasicCommand):
    def _run_main(self, parsed_args, parsed_globals):
        self.client = get_client(self._session, parsed_globals.region,
                                 parsed_globals.endpoint_url,
                                 parsed_globals.verify_ssl)


class ListCommand(S3Command):
    NAME = 'ls'
    DESCRIPTION = ("List S3 objects and common prefixes under a prefix or "
                   "all S3 buckets. Note that the --output and --no-paginate "
                   "arguments are ignored for this command.")
    USAGE = "<S3Uri> or NONE"
    ARG_TABLE = [{'name': 'paths', 'nargs': '?', 'default': 's3://',
                  'positional_arg': True, 'synopsis': USAGE}, RECURSIVE,
                 PAGE_SIZE, HUMAN_READABLE, SUMMARIZE, REQUEST_PAYER]

    def _run_main(self, parsed_args, parsed_globals):
        super(ListCommand, self)._run_main(parsed_args, parsed_globals)
        self._empty_result = False
        self._at_first_page = True
        self._size_accumulator = 0
        self._total_objects = 0
        self._human_readable = parsed_args.human_readable
        path = parsed_args.paths
        if path.startswith('s3://'):
            path = path[5:]
        bucket, key = find_bucket_key(path)
        if not bucket:
            self._list_all_buckets()
        elif parsed_args.dir_op:
            # Then --recursive was specified.
            self._list_all_objects_recursive(
                bucket, key, parsed_args.page_size, parsed_args.request_payer)
        else:
            self._list_all_objects(
                bucket, key, parsed_args.page_size, parsed_args.request_payer)
        if parsed_args.summarize:
            self._print_summary()
        if key:
            # User specified a key to look for. We should return an rc of one
            # if there are no matching keys and/or prefixes or return an rc
            # of zero if there are matching keys or prefixes.
            return self._check_no_objects()
        else:
            # This covers the case when user is trying to list all of of
            # the buckets or is trying to list the objects of a bucket
            # (without specifying a key). For both situations, a rc of 0
            # should be returned because applicable errors are supplied by
            # the server (i.e. bucket not existing). These errors will be
            # thrown before reaching the automatic return of rc of zero.
            return 0

    def _list_all_objects(self, bucket, key, page_size=None,
                          request_payer=None):
        paginator = self.client.get_paginator('list_objects_v2')
        paging_args = {
            'Bucket': bucket, 'Prefix': key, 'Delimiter': '/',
            'PaginationConfig': {'PageSize': page_size}
        }
        if request_payer is not None:
            paging_args['RequestPayer'] = request_payer
        iterator = paginator.paginate(**paging_args)
        for response_data in iterator:
            self._display_page(response_data)

    def _display_page(self, response_data, use_basename=True):
        common_prefixes = response_data.get('CommonPrefixes', [])
        contents = response_data.get('Contents', [])
        if not contents and not common_prefixes:
            self._empty_result = True
            return
        for common_prefix in common_prefixes:
            prefix_components = common_prefix['Prefix'].split('/')
            prefix = prefix_components[-2]
            pre_string = "PRE".rjust(30, " ")
            print_str = pre_string + ' ' + prefix + '/\n'
            uni_print(print_str)
        for content in contents:
            last_mod_str = self._make_last_mod_str(content['LastModified'])
            self._size_accumulator += int(content['Size'])
            self._total_objects += 1
            size_str = self._make_size_str(content['Size'])
            if use_basename:
                filename_components = content['Key'].split('/')
                filename = filename_components[-1]
            else:
                filename = content['Key']
            print_str = last_mod_str + ' ' + size_str + ' ' + \
                filename + '\n'
            uni_print(print_str)
        self._at_first_page = False

    def _list_all_buckets(self):
        response_data = self.client.list_buckets()
        buckets = response_data['Buckets']
        for bucket in buckets:
            last_mod_str = self._make_last_mod_str(bucket['CreationDate'])
            print_str = last_mod_str + ' ' + bucket['Name'] + '\n'
            uni_print(print_str)

    def _list_all_objects_recursive(self, bucket, key, page_size=None,
                                    request_payer=None):
        paginator = self.client.get_paginator('list_objects_v2')
        paging_args = {
            'Bucket': bucket, 'Prefix': key,
            'PaginationConfig': {'PageSize': page_size}
        }
        if request_payer is not None:
            paging_args['RequestPayer'] = request_payer
        iterator = paginator.paginate(**paging_args)
        for response_data in iterator:
            self._display_page(response_data, use_basename=False)

    def _check_no_objects(self):
        if self._empty_result and self._at_first_page:
            # Nothing was returned in the first page of results when listing
            # the objects.
            return 1
        return 0

    def _make_last_mod_str(self, last_mod):
        """
        This function creates the last modified time string whenever objects
        or buckets are being listed
        """
        last_mod = parse(last_mod)
        last_mod = last_mod.astimezone(tzlocal())
        last_mod_tup = (str(last_mod.year), str(last_mod.month).zfill(2),
                        str(last_mod.day).zfill(2),
                        str(last_mod.hour).zfill(2),
                        str(last_mod.minute).zfill(2),
                        str(last_mod.second).zfill(2))
        last_mod_str = "%s-%s-%s %s:%s:%s" % last_mod_tup
        return last_mod_str.ljust(19, ' ')

    def _make_size_str(self, size):
        """
        This function creates the size string when objects are being listed.
        """
        if self._human_readable:
            size_str = human_readable_size(size)
        else:
            size_str = str(size)
        return size_str.rjust(10, ' ')

    def _print_summary(self):
        """
        This function prints a summary of total objects and total bytes
        """
        print_str = str(self._total_objects)
        uni_print("\nTotal Objects: ".rjust(15, ' ') + print_str + "\n")
        if self._human_readable:
            print_str = human_readable_size(self._size_accumulator)
        else:
            print_str = str(self._size_accumulator)
        uni_print("Total Size: ".rjust(15, ' ') + print_str + "\n")


class WebsiteCommand(S3Command):
    NAME = 'website'
    DESCRIPTION = 'Set the website configuration for a bucket.'
    USAGE = '<S3Uri>'
    ARG_TABLE = [{'name': 'paths', 'nargs': 1, 'positional_arg': True,
                  'synopsis': USAGE}, INDEX_DOCUMENT, ERROR_DOCUMENT]

    def _run_main(self, parsed_args, parsed_globals):
        super(WebsiteCommand, self)._run_main(parsed_args, parsed_globals)
        bucket = self._get_bucket_name(parsed_args.paths[0])
        website_configuration = self._build_website_configuration(parsed_args)
        self.client.put_bucket_website(
            Bucket=bucket, WebsiteConfiguration=website_configuration)
        return 0

    def _build_website_configuration(self, parsed_args):
        website_config = {}
        if parsed_args.index_document is not None:
            website_config['IndexDocument'] = \
                {'Suffix': parsed_args.index_document}
        if parsed_args.error_document is not None:
            website_config['ErrorDocument'] = \
                {'Key': parsed_args.error_document}
        return website_config

    def _get_bucket_name(self, path):
        # We support either:
        # s3://bucketname
        # bucketname
        #
        # We also strip off the trailing slash if a user
        # accidentally appends a slash.
        if path.startswith('s3://'):
            path = path[5:]
        if path.endswith('/'):
            path = path[:-1]
        block_unsupported_resources(path)
        return path


class PresignCommand(S3Command):
    NAME = 'presign'
    DESCRIPTION = (
        "Generate a pre-signed URL for an Amazon S3 object. This allows "
        "anyone who receives the pre-signed URL to retrieve the S3 object "
        "with an HTTP GET request. For sigv4 requests the region needs to be "
        "configured explicitly."
    )
    USAGE = "<S3Uri>"
    ARG_TABLE = [{'name': 'path',
                  'positional_arg': True, 'synopsis': USAGE},
                 {'name': 'expires-in', 'default': 3600,
                  'cli_type_name': 'integer',
                  'help_text': (
                      'Number of seconds until the pre-signed '
                      'URL expires.  Default is 3600 seconds.')}]

    def _run_main(self, parsed_args, parsed_globals):
        super(PresignCommand, self)._run_main(parsed_args, parsed_globals)
        path = parsed_args.path
        if path.startswith('s3://'):
            path = path[5:]
        bucket, key = find_bucket_key(path)
        url = self.client.generate_presigned_url(
            'get_object',
            {'Bucket': bucket, 'Key': key},
            ExpiresIn=parsed_args.expires_in
        )
        uni_print(url)
        uni_print('\n')
        return 0


class S3TransferCommand(S3Command):
    def _run_main(self, parsed_args, parsed_globals):
        super(S3TransferCommand, self)._run_main(parsed_args, parsed_globals)
        self._convert_path_args(parsed_args)
        params = self._build_call_parameters(parsed_args, {})
        cmd_params = CommandParameters(self.NAME, params,
                                       self.USAGE,
                                       self._session,
                                       parsed_globals)
        cmd_params.add_region(parsed_globals)
        cmd_params.add_endpoint_url(parsed_globals)
        cmd_params.add_verify_ssl(parsed_globals)
        cmd_params.add_page_size(parsed_args)
        cmd_params.add_paths(parsed_args.paths)

        runtime_config = transferconfig.RuntimeConfig().build_config(
            **self._session.get_scoped_config().get('s3', {}))
        cmd = CommandArchitecture(self._session, self.NAME,
                                  cmd_params.parameters,
                                  runtime_config)
        cmd.set_clients()
        cmd.create_instructions()
        return cmd.run()

    def _build_call_parameters(self, args, command_params):
        """
        This takes all of the commands in the name space and puts them
        into a dictionary
        """
        for name, value in vars(args).items():
            command_params[name] = value
        return command_params

    def _convert_path_args(self, parsed_args):
        if not isinstance(parsed_args.paths, list):
            parsed_args.paths = [parsed_args.paths]
        for i in range(len(parsed_args.paths)):
            path = parsed_args.paths[i]
            if isinstance(path, bytes):
                dec_path = path.decode(sys.getfilesystemencoding())
                enc_path = dec_path.encode('utf-8')
                new_path = enc_path.decode('utf-8')
                parsed_args.paths[i] = new_path


class CpCommand(S3TransferCommand):
    NAME = 'cp'
    DESCRIPTION = "Copies a local file or S3 object to another location " \
                  "locally or in S3."
    USAGE = "<LocalPath> <S3Uri> or <S3Uri> <LocalPath> " \
            "or <S3Uri> <S3Uri>"
    ARG_TABLE = [{'name': 'paths', 'nargs': 2, 'positional_arg': True,
                  'synopsis': USAGE}] + TRANSFER_ARGS + \
                [METADATA, METADATA_DIRECTIVE, EXPECTED_SIZE, RECURSIVE]


class MvCommand(S3TransferCommand):
    NAME = 'mv'
    DESCRIPTION = BasicCommand.FROM_FILE('s3', 'mv', '_description.rst')
    USAGE = "<LocalPath> <S3Uri> or <S3Uri> <LocalPath> " \
            "or <S3Uri> <S3Uri>"
    ARG_TABLE = [{'name': 'paths', 'nargs': 2, 'positional_arg': True,
                  'synopsis': USAGE}] + TRANSFER_ARGS +\
                [METADATA, METADATA_DIRECTIVE, RECURSIVE, VALIDATE_SAME_S3_PATHS]


class RmCommand(S3TransferCommand):
    NAME = 'rm'
    DESCRIPTION = "Deletes an S3 object."
    USAGE = "<S3Uri>"
    ARG_TABLE = [{'name': 'paths', 'nargs': 1, 'positional_arg': True,
                  'synopsis': USAGE}, DRYRUN, QUIET, RECURSIVE, REQUEST_PAYER,
                 INCLUDE, EXCLUDE, ONLY_SHOW_ERRORS, PAGE_SIZE]


class SyncCommand(S3TransferCommand):
    NAME = 'sync'
    DESCRIPTION = "Syncs directories and S3 prefixes. Recursively copies " \
                  "new and updated files from the source directory to " \
                  "the destination. Only creates folders in the destination " \
                  "if they contain one or more files."
    USAGE = "<LocalPath> <S3Uri> or <S3Uri> " \
            "<LocalPath> or <S3Uri> <S3Uri>"
    ARG_TABLE = [{'name': 'paths', 'nargs': 2, 'positional_arg': True,
                  'synopsis': USAGE}] + TRANSFER_ARGS + \
                [METADATA, METADATA_DIRECTIVE]


class MbCommand(S3Command):
    NAME = 'mb'
    DESCRIPTION = "Creates an S3 bucket."
    USAGE = "<S3Uri>"
    ARG_TABLE = [{'name': 'path', 'positional_arg': True, 'synopsis': USAGE}]

    def _run_main(self, parsed_args, parsed_globals):
        super(MbCommand, self)._run_main(parsed_args, parsed_globals)

        if not parsed_args.path.startswith('s3://'):
            raise TypeError("%s\nError: Invalid argument type" % self.USAGE)
        bucket, _ = split_s3_bucket_key(parsed_args.path)

        bucket_config = {'LocationConstraint': self.client.meta.region_name}
        params = {'Bucket': bucket}
        if self.client.meta.region_name != 'us-east-1':
            params['CreateBucketConfiguration'] = bucket_config

        # TODO: Consolidate how we handle return codes and errors
        try:
            self.client.create_bucket(**params)
            uni_print("make_bucket: %s\n" % bucket)
            return 0
        except Exception as e:
            uni_print(
                "make_bucket failed: %s %s\n" % (parsed_args.path, e),
                sys.stderr
            )
            return 1


class RbCommand(S3Command):
    NAME = 'rb'
    DESCRIPTION = (
        "Deletes an empty S3 bucket. A bucket must be completely empty "
        "of objects and versioned objects before it can be deleted. "
        "However, the ``--force`` parameter can be used to delete "
        "the non-versioned objects in the bucket before the bucket is "
        "deleted."
    )
    USAGE = "<S3Uri>"
    ARG_TABLE = [{'name': 'path', 'positional_arg': True,
                  'synopsis': USAGE}, FORCE]

    def _run_main(self, parsed_args, parsed_globals):
        super(RbCommand, self)._run_main(parsed_args, parsed_globals)

        if not parsed_args.path.startswith('s3://'):
            raise TypeError("%s\nError: Invalid argument type" % self.USAGE)
        bucket, key = split_s3_bucket_key(parsed_args.path)

        if key:
            raise ValueError('Please specify a valid bucket name only.'
                             ' E.g. s3://%s' % bucket)

        if parsed_args.force:
            self._force(parsed_args.path, parsed_globals)

        try:
            self.client.delete_bucket(Bucket=bucket)
            uni_print("remove_bucket: %s\n" % bucket)
            return 0
        except Exception as e:
            uni_print(
                "remove_bucket failed: %s %s\n" % (parsed_args.path, e),
                sys.stderr
            )
            return 1

    def _force(self, path, parsed_globals):
        """Calls rm --recursive on the given path."""
        rm = RmCommand(self._session)
        rc = rm([path, '--recursive'], parsed_globals)
        if rc != 0:
            raise RuntimeError(
                "remove_bucket failed: Unable to delete all objects in the "
                "bucket, bucket will not be deleted.")


class CommandArchitecture(object):
    """
    This class drives the actual command.  A command is performed in two
    steps.  First a list of instructions is generated.  This list of
    instructions identifies which type of components are required based on the
    name of the command and the parameters passed to the command line.  After
    the instructions are generated the second step involves using the
    list of instructions to wire together an assortment of generators to
    perform the command.
    """
    def __init__(self, session, cmd, parameters, runtime_config=None):
        self.session = session
        self.cmd = cmd
        self.parameters = parameters
        self.instructions = []
        self._runtime_config = runtime_config
        self._endpoint = None
        self._source_endpoint = None
        self._client = None
        self._source_client = None

    def set_clients(self):
        client_config = None
        if self.parameters.get('sse') == 'aws:kms':
            client_config = Config(signature_version='s3v4')
        self._client = get_client(
            self.session,
            region=self.parameters['region'],
            endpoint_url=self.parameters['endpoint_url'],
            verify=self.parameters['verify_ssl'],
            config=client_config
        )
        self._source_client = get_client(
            self.session,
            region=self.parameters['region'],
            endpoint_url=self.parameters['endpoint_url'],
            verify=self.parameters['verify_ssl'],
            config=client_config
        )
        if self.parameters['source_region']:
            if self.parameters['paths_type'] == 's3s3':
                self._source_client = get_client(
                    self.session,
                    region=self.parameters['source_region'],
                    endpoint_url=None,
                    verify=self.parameters['verify_ssl'],
                    config=client_config
                )

    def create_instructions(self):
        """
        This function creates the instructions based on the command name and
        extra parameters.  Note that all commands must have an s3_handler
        instruction in the instructions and must be at the end of the
        instruction list because it sends the request to S3 and does not
        yield anything.
        """
        if self.needs_filegenerator():
            self.instructions.append('file_generator')
            if self.parameters.get('filters'):
                self.instructions.append('filters')
            if self.cmd == 'sync':
                self.instructions.append('comparator')
            self.instructions.append('file_info_builder')
        self.instructions.append('s3_handler')

    def needs_filegenerator(self):
        return not self.parameters['is_stream']

    def choose_sync_strategies(self):
        """Determines the sync strategy for the command.

        It defaults to the default sync strategies but a customizable sync
        strategy can override the default strategy if it returns the instance
        of its self when the event is emitted.
        """
        sync_strategies = {}
        # Set the default strategies.
        sync_strategies['file_at_src_and_dest_sync_strategy'] = \
            SizeAndLastModifiedSync()
        sync_strategies['file_not_at_dest_sync_strategy'] = MissingFileSync()
        sync_strategies['file_not_at_src_sync_strategy'] = NeverSync()

        # Determine what strategies to override if any.
        responses = self.session.emit(
            'choosing-s3-sync-strategy', params=self.parameters)
        if responses is not None:
            for response in responses:
                override_sync_strategy = response[1]
                if override_sync_strategy is not None:
                    sync_type = override_sync_strategy.sync_type
                    sync_type += '_sync_strategy'
                    sync_strategies[sync_type] = override_sync_strategy

        return sync_strategies

    def run(self):
        """
        This function wires together all of the generators and completes
        the command.  First a dictionary is created that is indexed first by
        the command name.  Then using the instruction, another dictionary
        can be indexed to obtain the objects corresponding to the
        particular instruction for that command.  To begin the wiring,
        either a ``FileFormat`` or ``TaskInfo`` object, depending on the
        command, is put into a list.  Then the function enters a while loop
        that pops off an instruction.  It then determines the object needed
        and calls the call function of the object using the list as the input.
        Depending on the number of objects in the input list and the number
        of components in the list corresponding to the instruction, the call
        method of the component can be called two different ways.  If the
        number of inputs is equal to the number of components a 1:1 mapping of
        inputs to components is used when calling the call function.  If the
        there are more inputs than components, then a 2:1 mapping of inputs to
        components is used where the component call method takes two inputs
        instead of one.  Whatever files are yielded from the call function
        is appended to a list and used as the input for the next repetition
        of the while loop until there are no more instructions.
        """
        src = self.parameters['src']
        dest = self.parameters['dest']
        paths_type = self.parameters['paths_type']
        files = FileFormat().format(src, dest, self.parameters)
        rev_files = FileFormat().format(dest, src, self.parameters)

        cmd_translation = {
            'locals3': 'upload',
            's3s3': 'copy',
            's3local': 'download',
            's3': 'delete'
        }
        result_queue = queue.Queue()
        operation_name = cmd_translation[paths_type]

        fgen_kwargs = {
            'client': self._source_client, 'operation_name': operation_name,
            'follow_symlinks': self.parameters['follow_symlinks'],
            'page_size': self.parameters['page_size'],
            'result_queue': result_queue,
        }
        rgen_kwargs = {
            'client': self._client, 'operation_name': '',
            'follow_symlinks': self.parameters['follow_symlinks'],
            'page_size': self.parameters['page_size'],
            'result_queue': result_queue,
        }

        fgen_request_parameters = \
            self._get_file_generator_request_parameters_skeleton()
        self._map_request_payer_params(fgen_request_parameters)
        self._map_sse_c_params(fgen_request_parameters, paths_type)
        fgen_kwargs['request_parameters'] = fgen_request_parameters

        rgen_request_parameters =  \
            self._get_file_generator_request_parameters_skeleton()
        self._map_request_payer_params(rgen_request_parameters)
        rgen_kwargs['request_parameters'] = rgen_request_parameters

        file_generator = FileGenerator(**fgen_kwargs)
        rev_generator = FileGenerator(**rgen_kwargs)
        stream_dest_path, stream_compare_key = find_dest_path_comp_key(files)
        stream_file_info = [FileInfo(src=files['src']['path'],
                                     dest=stream_dest_path,
                                     compare_key=stream_compare_key,
                                     src_type=files['src']['type'],
                                     dest_type=files['dest']['type'],
                                     operation_name=operation_name,
                                     client=self._client,
                                     is_stream=True)]
        file_info_builder = FileInfoBuilder(
            self._client, self._source_client, self.parameters)

        s3_transfer_handler = S3TransferHandlerFactory(
            self.parameters, self._runtime_config)(
                self._client, result_queue)

        sync_strategies = self.choose_sync_strategies()

        command_dict = {}
        if self.cmd == 'sync':
            command_dict = {'setup': [files, rev_files],
                            'file_generator': [file_generator,
                                               rev_generator],
                            'filters': [create_filter(self.parameters),
                                        create_filter(self.parameters)],
                            'comparator': [Comparator(**sync_strategies)],
                            'file_info_builder': [file_info_builder],
                            's3_handler': [s3_transfer_handler]}
        elif self.cmd == 'cp' and self.parameters['is_stream']:
            command_dict = {'setup': [stream_file_info],
                            's3_handler': [s3_transfer_handler]}
        elif self.cmd == 'cp':
            command_dict = {'setup': [files],
                            'file_generator': [file_generator],
                            'filters': [create_filter(self.parameters)],
                            'file_info_builder': [file_info_builder],
                            's3_handler': [s3_transfer_handler]}
        elif self.cmd == 'rm':
            command_dict = {'setup': [files],
                            'file_generator': [file_generator],
                            'filters': [create_filter(self.parameters)],
                            'file_info_builder': [file_info_builder],
                            's3_handler': [s3_transfer_handler]}
        elif self.cmd == 'mv':
            command_dict = {'setup': [files],
                            'file_generator': [file_generator],
                            'filters': [create_filter(self.parameters)],
                            'file_info_builder': [file_info_builder],
                            's3_handler': [s3_transfer_handler]}

        files = command_dict['setup']
        while self.instructions:
            instruction = self.instructions.pop(0)
            file_list = []
            components = command_dict[instruction]
            for i in range(len(components)):
                if len(files) > len(components):
                    file_list.append(components[i].call(*files))
                else:
                    file_list.append(components[i].call(files[i]))
            files = file_list
        # This is kinda quirky, but each call through the instructions
        # will replaces the files attr with the return value of the
        # file_list.  The very last call is a single list of
        # [s3_handler], and the s3_handler returns the number of
        # tasks failed and the number of tasks warned.
        # This means that files[0] now contains a namedtuple with
        # the number of failed tasks and the number of warned tasks.
        # In terms of the RC, we're keeping it simple and saying
        # that > 0 failed tasks will give a 1 RC and > 0 warned
        # tasks will give a 2 RC.  Otherwise a RC of zero is returned.
        rc = 0
        if files[0].num_tasks_failed > 0:
            rc = 1
        elif files[0].num_tasks_warned > 0:
            rc = 2
        return rc

    def _get_file_generator_request_parameters_skeleton(self):
        return {
            'HeadObject': {},
            'ListObjects': {},
            'ListObjectsV2': {}
        }

    def _map_request_payer_params(self, request_parameters):
        RequestParamsMapper.map_head_object_params(
            request_parameters['HeadObject'], {
                'request_payer': self.parameters.get('request_payer')
            }
        )
        RequestParamsMapper.map_list_objects_v2_params(
            request_parameters['ListObjectsV2'], {
                'request_payer': self.parameters.get('request_payer')
            }
        )

    def _map_sse_c_params(self, request_parameters, paths_type):
        # SSE-C may be needed for HeadObject for copies/downloads/deletes
        # If the operation is s3 to s3, the FileGenerator should use the
        # copy source key and algorithm. Otherwise, use the regular
        # SSE-C key and algorithm. Note the reverse FileGenerator does
        # not need any of these because it is used only for sync operations
        # which only use ListObjects which does not require HeadObject.
        RequestParamsMapper.map_head_object_params(
            request_parameters['HeadObject'], self.parameters)
        if paths_type == 's3s3':
            RequestParamsMapper.map_head_object_params(
                request_parameters['HeadObject'], {
                    'sse_c': self.parameters.get('sse_c_copy_source'),
                    'sse_c_key': self.parameters.get('sse_c_copy_source_key')
                }
            )


class CommandParameters(object):
    """
    This class is used to do some initial error based on the
    parameters and arguments passed to the command line.
    """
    def __init__(self, cmd, parameters, usage,
                 session=None, parsed_globals=None):
        """
        Stores command name and parameters.  Ensures that the ``dir_op`` flag
        is true if a certain command is being used.

        :param cmd: The name of the command, e.g. "rm".
        :param parameters: A dictionary of parameters.
        :param usage: A usage string

        """
        self.cmd = cmd
        self.parameters = parameters
        self.usage = usage
        self._session = session
        self._parsed_globals = parsed_globals
        if 'dir_op' not in parameters:
            self.parameters['dir_op'] = False
        if 'follow_symlinks' not in parameters:
            self.parameters['follow_symlinks'] = True
        if 'source_region' not in parameters:
            self.parameters['source_region'] = None
        if self.cmd in ['sync', 'mb', 'rb']:
            self.parameters['dir_op'] = True
        if self.cmd == 'mv':
            self.parameters['is_move'] = True
        else:
            self.parameters['is_move'] = False

    def add_paths(self, paths):
        """
        Reformats the parameters dictionary by including a key and
        value for the source and the destination.  If a destination is
        not used the destination is the same as the source to ensure
        the destination always have some value.
        """
        self.check_path_type(paths)
        self._normalize_s3_trailing_slash(paths)
        src_path = paths[0]
        self.parameters['src'] = src_path
        if len(paths) == 2:
            self.parameters['dest'] = paths[1]
        elif len(paths) == 1:
            self.parameters['dest'] = paths[0]
        self._validate_streaming_paths()
        self._validate_path_args()
        self._validate_sse_c_args()
        self._validate_not_s3_express_bucket_for_sync()

    def _validate_not_s3_express_bucket_for_sync(self):
        if self.cmd == 'sync' and \
            (self._is_s3express_path(self.parameters['src']) or
             self._is_s3express_path(self.parameters['dest'])):
            raise ValueError(
                "Cannot use sync command with a directory bucket."
            )

    def _is_s3express_path(self, path):
        if path.startswith("s3://"):
            bucket = split_s3_bucket_key(path)[0]
            return is_s3express_bucket(bucket)
        return False

    def _validate_streaming_paths(self):
        self.parameters['is_stream'] = False
        if self.parameters['src'] == '-' or self.parameters['dest'] == '-':
            if self.cmd != 'cp' or self.parameters.get('dir_op'):
                raise ValueError(
                    "Streaming currently is only compatible with "
                    "non-recursive cp commands"
                )
            self.parameters['is_stream'] = True
            self.parameters['dir_op'] = False
            self.parameters['only_show_errors'] = True

    def _validate_path_args(self):
        # If we're using a mv command, you can't copy the object onto itself.
        params = self.parameters
        if self.cmd == 'mv' and params['paths_type']=='s3s3':
            self._raise_if_mv_same_paths(params['src'], params['dest'])
            if self._should_validate_same_underlying_s3_paths():
                self._validate_same_underlying_s3_paths()
            if self._should_emit_validate_s3_paths_warning():
                self._emit_validate_s3_paths_warning()

        # If the user provided local path does not exist, hard fail because
        # we know that we will not be able to upload the file.
        if 'locals3' == params['paths_type'] and not params['is_stream']:
            if not os.path.exists(params['src']):
                raise RuntimeError(
                    'The user-provided path %s does not exist.' %
                    params['src'])
        # If the operation is downloading to a directory that does not exist,
        # create the directories so no warnings are thrown during the syncing
        # process.
        elif 's3local' == params['paths_type'] and params['dir_op']:
            if not os.path.exists(params['dest']):
                os.makedirs(params['dest'])

    def _same_path(self, src, dest):
        if not self.parameters['paths_type'] == 's3s3':
            return False
        elif src == dest:
            return True
        elif dest.endswith('/'):
            src_base = os.path.basename(src)
            return src == os.path.join(dest, src_base)

    def _same_key(self, src, dest):
        _, src_key = split_s3_bucket_key(src)
        _, dest_key = split_s3_bucket_key(dest)
        return self._same_path(f'/{src_key}', f'/{dest_key}')

    def _validate_same_s3_paths_enabled(self):
        validate_env_var = ensure_boolean(
            os.environ.get('AWS_CLI_S3_MV_VALIDATE_SAME_S3_PATHS'))
        return (self.parameters.get('validate_same_s3_paths') or
                validate_env_var)

    def _should_emit_validate_s3_paths_warning(self):
        is_same_key = self._same_key(
            self.parameters['src'], self.parameters['dest'])
        src_has_underlying_path = S3PathResolver.has_underlying_s3_path(
            self.parameters['src'])
        dest_has_underlying_path = S3PathResolver.has_underlying_s3_path(
            self.parameters['dest'])
        return (is_same_key and not self._validate_same_s3_paths_enabled() and
                (src_has_underlying_path or dest_has_underlying_path))

    def _emit_validate_s3_paths_warning(self):
        msg = (
            "warning: Provided s3 paths may resolve to same underlying "
            "s3 object(s) and result in deletion instead of being moved. "
            "To resolve and validate underlying s3 paths are not the same, "
            "specify the --validate-same-s3-paths flag or set the "
            "AWS_CLI_S3_MV_VALIDATE_SAME_S3_PATHS environment variable to true. "
            "To resolve s3 outposts access point path, the arn must be "
            "used instead of the alias.\n"
        )
        uni_print(msg, sys.stderr)

    def _should_validate_same_underlying_s3_paths(self):
        is_same_key = self._same_key(
            self.parameters['src'], self.parameters['dest'])
        return is_same_key and self._validate_same_s3_paths_enabled()

    def _validate_same_underlying_s3_paths(self):
        src_paths = S3PathResolver.from_session(
            self._session,
            self.parameters.get('source_region', self._parsed_globals.region),
            self._parsed_globals.verify_ssl
        ).resolve_underlying_s3_paths(self.parameters['src'])
        dest_paths = S3PathResolver.from_session(
            self._session,
            self._parsed_globals.region,
            self._parsed_globals.verify_ssl
        ).resolve_underlying_s3_paths(self.parameters['dest'])
        for src_path in src_paths:
            for dest_path in dest_paths:
                self._raise_if_mv_same_paths(src_path, dest_path)

    def _raise_if_mv_same_paths(self, src, dest):
        if self._same_path(src, dest):
            raise ValueError(
                "Cannot mv a file onto itself: "
                f"{self.parameters['src']} - {self.parameters['dest']}"
            )

    def _normalize_s3_trailing_slash(self, paths):
        for i, path in enumerate(paths):
            if path.startswith('s3://'):
                bucket, key = find_bucket_key(path[5:])
                if not key and not path.endswith('/'):
                    # If only a bucket was specified, we need
                    # to normalize the path and ensure it ends
                    # with a '/', s3://bucket -> s3://bucket/
                    path += '/'
                    paths[i] = path

    def check_path_type(self, paths):
        """
        This initial check ensures that the path types for the specified
        command is correct.
        """
        template_type = {'s3s3': ['cp', 'sync', 'mv'],
                         's3local': ['cp', 'sync', 'mv'],
                         'locals3': ['cp', 'sync', 'mv'],
                         's3': ['mb', 'rb', 'rm'],
                         'local': [], 'locallocal': []}
        paths_type = ''
        usage = "usage: aws s3 %s %s" % (self.cmd,
                                         self.usage)
        for i in range(len(paths)):
            if paths[i].startswith('s3://'):
                paths_type = paths_type + 's3'
            else:
                paths_type = paths_type + 'local'
        if self.cmd in template_type[paths_type]:
            self.parameters['paths_type'] = paths_type
        else:
            raise TypeError("%s\nError: Invalid argument type" % usage)

    def add_region(self, parsed_globals):
        self.parameters['region'] = parsed_globals.region

    def add_endpoint_url(self, parsed_globals):
        """
        Adds endpoint_url to the parameters.
        """
        if 'endpoint_url' in parsed_globals:
            self.parameters['endpoint_url'] = getattr(parsed_globals,
                                                      'endpoint_url')
        else:
            self.parameters['endpoint_url'] = None

    def add_verify_ssl(self, parsed_globals):
        self.parameters['verify_ssl'] = parsed_globals.verify_ssl

    def add_page_size(self, parsed_args):
        self.parameters['page_size'] = getattr(parsed_args, 'page_size', None)

    def _validate_sse_c_args(self):
        self._validate_sse_c_arg()
        self._validate_sse_c_arg('sse_c_copy_source')
        self._validate_sse_c_copy_source_for_paths()

    def _validate_sse_c_arg(self, sse_c_type='sse_c'):
        sse_c_key_type = sse_c_type + '_key'
        sse_c_type_param = '--' + sse_c_type.replace('_', '-')
        sse_c_key_type_param = '--' + sse_c_key_type.replace('_', '-')
        if self.parameters.get(sse_c_type):
            if not self.parameters.get(sse_c_key_type):
                raise ValueError(
                    'It %s is specified, %s must be specified '
                    'as well.' % (sse_c_type_param, sse_c_key_type_param)
                )
        if self.parameters.get(sse_c_key_type):
            if not self.parameters.get(sse_c_type):
                raise ValueError(
                    'It %s is specified, %s must be specified '
                    'as well.' % (sse_c_key_type_param, sse_c_type_param)
                )

    def _validate_sse_c_copy_source_for_paths(self):
        if self.parameters.get('sse_c_copy_source'):
            if self.parameters['paths_type'] != 's3s3':
                raise ValueError(
                    '--sse-c-copy-source is only supported for '
                    'copy operations.'
                )
