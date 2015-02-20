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
import sys

from dateutil.parser import parse
from dateutil.tz import tzlocal

from awscli.compat import six
from awscli.compat import queue
from awscli.customizations.commands import BasicCommand
from awscli.customizations.s3.comparator import Comparator
from awscli.customizations.s3.fileinfobuilder import FileInfoBuilder
from awscli.customizations.s3.fileformat import FileFormat
from awscli.customizations.s3.filegenerator import FileGenerator
from awscli.customizations.s3.fileinfo import TaskInfo, FileInfo
from awscli.customizations.s3.filters import create_filter
from awscli.customizations.s3.s3handler import S3Handler, S3StreamHandler
from awscli.customizations.s3.utils import find_bucket_key, uni_print, \
    AppendFilter, find_dest_path_comp_key, human_readable_size
from awscli.customizations.s3.syncstrategy.base import MissingFileSync, \
    SizeAndLastModifiedSync, NeverSync
from awscli.customizations.s3 import transferconfig


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
             "Deletes all objects in the bucket including the bucket itself.")}


FOLLOW_SYMLINKS = {'name': 'follow-symlinks', 'action': 'store_true',
                   'default': True, 'group_name': 'follow_symlinks',
                   'help_text': (
                       "Symbolic links are followed "
                       "only when uploading to S3 from the local filesystem. "
                       "Note that S3 does not support symbolic links, so the "
                       "contents of the link target are uploaded under the "
                       "name of the link. When neither ``--follow-symlinks`` "
                       "nor ``--no-follow-symlinks`` is specifed, the default "
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


CONTENT_TYPE = {'name': 'content-type', 'nargs': 1,
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
               "in the command that match the specified pattern")}


ACL = {'name': 'acl', 'nargs': 1,
       'choices': ['private', 'public-read', 'public-read-write',
                   'authenticated-read', 'bucket-owner-read',
                   'bucket-owner-full-control', 'log-delivery-write'],
       'help_text': (
           "Sets the ACL for the object when the command is "
           "performed.  Only accepts values of ``private``, ``public-read``, "
           "``public-read-write``, ``authenticated-read``, "
           "``bucket-owner-read``, ``bucket-owner-full-control`` and "
           "``log-delivery-write``.")}


GRANTS = {
    'name': 'grants', 'nargs': '+',
    'help_text': (
        'Grant specific permissions to individual users or groups. You '
        'can supply a list of grants of the form::<p/>  --grants '
        'Permission=Grantee_Type=Grantee_ID [Permission=Grantee_Type='
        'Grantee_ID ...]<p/>Each value contains the following elements:'
        '<p/><ul><li><code>Permission</code> - Specifies '
        'the granted permissions, and can be set to read, readacl, '
        'writeacl, or full.</li><li><code>Grantee_Type</code> - '
        'Specifies how the grantee is to be identified, and can be set '
        'to uri, emailaddress, or id.</li><li><code>Grantee_ID</code> - '
        'Specifies the grantee based on Grantee_Type.</li></ul>The '
        '<code>Grantee_ID</code> value can be one of:<ul><li><b>uri</b> '
        '- The group\'s URI. For more information, see '
        '<a href="http://docs.aws.amazon.com/AmazonS3/latest/dev/'
        'ACLOverview.html#SpecifyingGrantee">'
        'Who Is a Grantee?</a></li>'
        '<li><b>emailaddress</b> - The account\'s email address.</li>'
        '<li><b>id</b> - The account\'s canonical ID</li></ul>'
        '</li></ul>'
        'For more information on Amazon S3 access control, see '
        '<a href="http://docs.aws.amazon.com/AmazonS3/latest/dev/'
        'UsingAuthAccess.html">Access Control</a>')}


SSE = {'name': 'sse', 'action': 'store_true',
       'help_text': (
           "Enable Server Side Encryption of the object in S3")}


STORAGE_CLASS = {'name': 'storage-class', 'nargs': 1,
                 'choices': ['STANDARD', 'REDUCED_REDUNDANCY'],
                 'help_text': (
                     "The type of storage to use for the object. "
                     "Valid choices are: STANDARD | REDUCED_REDUNDANCY. "
                     "Defaults to 'STANDARD'")}


WEBSITE_REDIRECT = {'name': 'website-redirect', 'nargs': 1,
                    'help_text': (
                        "If the bucket is configured as a website, "
                        "redirects requests for this object to another object "
                        "in the same bucket or to an external URL. Amazon S3 "
                        "stores the value of this header in the object "
                        "metadata.")}


CACHE_CONTROL = {'name': 'cache-control', 'nargs': 1,
                 'help_text': (
                     "Specifies caching behavior along the "
                     "request/reply chain.")}


CONTENT_DISPOSITION = {'name': 'content-disposition', 'nargs': 1,
                       'help_text': (
                           "Specifies presentational information "
                           "for the object.")}


CONTENT_ENCODING = {'name': 'content-encoding', 'nargs': 1,
                    'help_text': (
                        "Specifies what content encodings have been "
                        "applied to the object and thus what decoding "
                        "mechanisms must be applied to obtain the media-type "
                        "referenced by the Content-Type header field.")}


CONTENT_LANGUAGE = {'name': 'content-language', 'nargs': 1,
                    'help_text': ("The language the content is in.")}


SOURCE_REGION = {'name': 'source-region', 'nargs': 1,
                 'help_text': (
                     "When transferring objects from an s3 bucket to an s3 "
                     "bucket, this specifies the region of the source bucket."
                     " Note the region specified by ``--region`` or through "
                     "configuration of the CLI refers to the region of the "
                     "destination bucket.  If ``--source-region`` is not "
                     "specified the region of the source will be the same "
                     "as the region of the destination bucket.")}


EXPIRES = {
    'name': 'expires', 'nargs': 1,
    'help_text': (
        "The date and time at which the object is no longer cacheable.")
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


EXPECTED_SIZE = {'name': 'expected-size',
                 'help_text': (
                     'This argument specifies the expected size of a stream '
                     'in terms of bytes. Note that this argument is needed '
                     'only when a stream is being uploaded to s3 and the size '
                     'is larger than 5GB.  Failure to include this argument '
                     'under these conditions may result in a failed upload. '
                     'due to too many parts in upload.')}


PAGE_SIZE = {'name': 'page-size', 'cli_type_name': 'integer',
             'help_text': (
                 'The number of results to return in each response to a list '
                 'operation. The default value is 1000 (the maximum allowed). '
                 'Using a lower value may help if an operation times out.')}


TRANSFER_ARGS = [DRYRUN, QUIET, RECURSIVE, INCLUDE, EXCLUDE, ACL,
                 FOLLOW_SYMLINKS, NO_FOLLOW_SYMLINKS, NO_GUESS_MIME_TYPE,
                 SSE, STORAGE_CLASS, GRANTS, WEBSITE_REDIRECT, CONTENT_TYPE,
                 CACHE_CONTROL, CONTENT_DISPOSITION, CONTENT_ENCODING,
                 CONTENT_LANGUAGE, EXPIRES, SOURCE_REGION, ONLY_SHOW_ERRORS,
                 PAGE_SIZE]


def get_endpoint(service, region, endpoint_url, verify):
    return service.get_endpoint(region_name=region, endpoint_url=endpoint_url,
                                verify=verify)


def get_client(session, region, endpoint_url, verify):
    return session.create_client('s3', region_name=region,
                                 endpoint_url=endpoint_url, verify=verify)


class S3Command(BasicCommand):
    def _run_main(self, parsed_args, parsed_globals):
        self.service = self._session.get_service('s3')
        self.endpoint = get_endpoint(self.service, parsed_globals.region,
                                     parsed_globals.endpoint_url,
                                     parsed_globals.verify_ssl)
        self.client = get_client(self._session, parsed_globals.region,
                                 parsed_globals.endpoint_url,
                                 parsed_globals.verify_ssl)


class ListCommand(S3Command):
    NAME = 'ls'
    DESCRIPTION = ("List S3 objects and common prefixes under a prefix or "
                   "all S3 buckets. Note that the --output argument "
                   "is ignored for this command.")
    USAGE = "<S3Path> or NONE"
    ARG_TABLE = [{'name': 'paths', 'nargs': '?', 'default': 's3://',
                  'positional_arg': True, 'synopsis': USAGE}, RECURSIVE,
                 PAGE_SIZE, HUMAN_READABLE, SUMMARIZE]
    EXAMPLES = BasicCommand.FROM_FILE('s3/ls.rst')

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
            self._list_all_objects_recursive(bucket, key,
                                             parsed_args.page_size)
        else:
            self._list_all_objects(bucket, key, parsed_args.page_size)
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

    def _list_all_objects(self, bucket, key, page_size=None):
        paginator = self.client.get_paginator('list_objects')
        iterator = paginator.paginate(Bucket=bucket,
                                      Prefix=key, Delimiter='/',
                                      page_size=page_size)
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

    def _list_all_objects_recursive(self, bucket, key, page_size=None):
        paginator = self.client.get_paginator('list_objects')
        iterator = paginator.paginate(Bucket=bucket,
                                      Prefix=key, page_size=page_size)
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
    USAGE = '<S3Path>'
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
        # accidently appends a slash.
        if path.startswith('s3://'):
            path = path[5:]
        if path.endswith('/'):
            path = path[:-1]
        return path


class S3TransferCommand(S3Command):
    def _run_main(self, parsed_args, parsed_globals):
        super(S3TransferCommand, self)._run_main(parsed_args, parsed_globals)
        self._convert_path_args(parsed_args)
        params = self._build_call_parameters(parsed_args, {})
        cmd_params = CommandParameters(self.NAME, params,
                                       self.USAGE)
        cmd_params.add_region(parsed_globals)
        cmd_params.add_endpoint_url(parsed_globals)
        cmd_params.add_verify_ssl(parsed_globals)
        cmd_params.add_page_size(parsed_args)
        cmd_params.add_paths(parsed_args.paths)
        self._handle_rm_force(parsed_globals, cmd_params.parameters)
        runtime_config = transferconfig.RuntimeConfig().build_config(
            **self._session.get_scoped_config().get('s3', {}))
        cmd = CommandArchitecture(self._session, self.NAME,
                                  cmd_params.parameters,
                                  runtime_config)
        cmd.set_endpoints()
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
            if isinstance(path, six.binary_type):
                dec_path = path.decode(sys.getfilesystemencoding())
                enc_path = dec_path.encode('utf-8')
                new_path = enc_path.decode('utf-8')
                parsed_args.paths[i] = new_path

    def _handle_rm_force(self, parsed_globals, parameters):
        """
        This function recursive deletes objects in a bucket if the force
        parameters was thrown when using the remove bucket command.
        """
        # XXX: This shouldn't really be here.  This was originally moved from
        # the CommandParameters class to here, but this is still not the ideal
        # place for this code.  This should be moved
        # to either the CommandArchitecture class, or the RbCommand class where
        # the actual operations against S3 are performed.  This may require
        # some refactoring though to move this to either of those classes.
        # For now, moving this out of CommandParameters allows for that class
        # to be kept simple.
        if 'force' in parameters:
            if parameters['force']:
                bucket = find_bucket_key(parameters['src'][5:])[0]
                path = 's3://' + bucket
                del_objects = RmCommand(self._session)
                del_objects([path, '--recursive'], parsed_globals)


class CpCommand(S3TransferCommand):
    NAME = 'cp'
    DESCRIPTION = "Copies a local file or S3 object to another location " \
                  "locally or in S3."
    USAGE = "<LocalPath> <S3Path> or <S3Path> <LocalPath> " \
            "or <S3Path> <S3Path>"
    ARG_TABLE = [{'name': 'paths', 'nargs': 2, 'positional_arg': True,
                  'synopsis': USAGE}] + TRANSFER_ARGS + [EXPECTED_SIZE]
    EXAMPLES = BasicCommand.FROM_FILE('s3/cp.rst')


class MvCommand(S3TransferCommand):
    NAME = 'mv'
    DESCRIPTION = "Moves a local file or S3 object to " \
                  "another location locally or in S3."
    USAGE = "<LocalPath> <S3Path> or <S3Path> <LocalPath> " \
            "or <S3Path> <S3Path>"
    ARG_TABLE = [{'name': 'paths', 'nargs': 2, 'positional_arg': True,
                  'synopsis': USAGE}] + TRANSFER_ARGS
    EXAMPLES = BasicCommand.FROM_FILE('s3/mv.rst')


class RmCommand(S3TransferCommand):
    NAME = 'rm'
    DESCRIPTION = "Deletes an S3 object."
    USAGE = "<S3Path>"
    ARG_TABLE = [{'name': 'paths', 'nargs': 1, 'positional_arg': True,
                  'synopsis': USAGE}, DRYRUN, QUIET, RECURSIVE, INCLUDE,
                 EXCLUDE, ONLY_SHOW_ERRORS, PAGE_SIZE]
    EXAMPLES = BasicCommand.FROM_FILE('s3/rm.rst')


class SyncCommand(S3TransferCommand):
    NAME = 'sync'
    DESCRIPTION = "Syncs directories and S3 prefixes."
    USAGE = "<LocalPath> <S3Path> or <S3Path> " \
            "<LocalPath> or <S3Path> <S3Path>"
    ARG_TABLE = [{'name': 'paths', 'nargs': 2, 'positional_arg': True,
                  'synopsis': USAGE}] + TRANSFER_ARGS
    EXAMPLES = BasicCommand.FROM_FILE('s3/sync.rst')


class MbCommand(S3TransferCommand):
    NAME = 'mb'
    DESCRIPTION = "Creates an S3 bucket."
    USAGE = "<S3Path>"
    ARG_TABLE = [{'name': 'paths', 'nargs': 1, 'positional_arg': True,
                  'synopsis': USAGE}]
    EXAMPLES = BasicCommand.FROM_FILE('s3/mb.rst')


class RbCommand(S3TransferCommand):
    NAME = 'rb'
    DESCRIPTION = "Deletes an S3 bucket."
    USAGE = "<S3Path>"
    ARG_TABLE = [{'name': 'paths', 'nargs': 1, 'positional_arg': True,
                  'synopsis': USAGE}, FORCE]
    EXAMPLES = BasicCommand.FROM_FILE('s3/rb.rst')


class CommandArchitecture(object):
    """
    This class drives the actual command.  A command is performed in two
    steps.  First a list of instructions is generated.  This list of
    instructions identifies which type of components are required based on the
    name of the command and the parameters passed to the command line.  After
    the instructions are generated the second step involves using the
    lsit of instructions to wire together an assortment of generators to
    perform the command.
    """
    def __init__(self, session, cmd, parameters, runtime_config=None):
        self.session = session
        self.cmd = cmd
        self.parameters = parameters
        self.instructions = []
        self._runtime_config = runtime_config
        self._service = self.session.get_service('s3')
        self._endpoint = None
        self._source_endpoint = None
        self._client = None
        self._source_client = None

    def set_endpoints(self):
        self._endpoint = get_endpoint(
            self._service,
            region=self.parameters['region'],
            endpoint_url=self.parameters['endpoint_url'],
            verify=self.parameters['verify_ssl']
        )
        self._source_endpoint = self._endpoint
        if self.parameters['source_region']:
            if self.parameters['paths_type'] == 's3s3':
                self._source_endpoint = get_endpoint(
                    self._service,
                    region=self.parameters['source_region'][0],
                    endpoint_url=None,
                    verify=self.parameters['verify_ssl']
                )

    def set_clients(self):
        self._client = get_client(
            self.session,
            region=self.parameters['region'],
            endpoint_url=self.parameters['endpoint_url'],
            verify=self.parameters['verify_ssl']
        )
        self._source_client = self._client.clone_client()
        if self.parameters['source_region']:
            if self.parameters['paths_type'] == 's3s3':
                self._source_client = get_client(
                    self.session,
                    region=self.parameters['source_region'][0],
                    endpoint_url=None,
                    verify=self.parameters['verify_ssl']
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
        if self.cmd in ['mb', 'rb'] or self.parameters['is_stream']:
            return False
        else:
            return True

    def choose_sync_strategies(self):
        """Determines the sync strategy for the command.

        It defaults to the default sync strategies but a customizable sync
        strategy can overide the default strategy if it returns the instance
        of its self when the event is emitted.
        """
        sync_strategies = {}
        # Set the default strategies.
        sync_strategies['file_at_src_and_dest_sync_strategy'] = \
            SizeAndLastModifiedSync()
        sync_strategies['file_not_at_dest_sync_strategy'] = MissingFileSync()
        sync_strategies['file_not_at_src_sync_strategy'] = NeverSync()

        # Determine what strategies to overide if any.
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

        cmd_translation = {}
        cmd_translation['locals3'] = {'cp': 'upload', 'sync': 'upload',
                                      'mv': 'move'}
        cmd_translation['s3s3'] = {'cp': 'copy', 'sync': 'copy', 'mv': 'move'}
        cmd_translation['s3local'] = {'cp': 'download', 'sync': 'download',
                                      'mv': 'move'}
        cmd_translation['s3'] = {
            'rm': 'delete',
            'mb': 'make_bucket',
            'rb': 'remove_bucket'
        }
        result_queue = queue.Queue()
        operation_name = cmd_translation[paths_type][self.cmd]
        file_generator = FileGenerator(self._source_client,
                                       operation_name,
                                       self.parameters['follow_symlinks'],
                                       self.parameters['page_size'],
                                       result_queue=result_queue)
        rev_generator = FileGenerator(self._client, '',
                                      self.parameters['follow_symlinks'],
                                      self.parameters['page_size'],
                                      result_queue=result_queue)
        taskinfo = [TaskInfo(src=files['src']['path'],
                             src_type='s3',
                             operation_name=operation_name,
                             service=self._service,
                             endpoint=self._endpoint)]
        stream_dest_path, stream_compare_key = find_dest_path_comp_key(files)
        stream_file_info = [FileInfo(src=files['src']['path'],
                                     dest=stream_dest_path,
                                     compare_key=stream_compare_key,
                                     src_type=files['src']['type'],
                                     dest_type=files['dest']['type'],
                                     operation_name=operation_name,
                                     service=self._service,
                                     endpoint=self._endpoint,
                                     is_stream=True)]
        file_info_builder = FileInfoBuilder(
            self._service, self._endpoint,
            self._source_endpoint, self.parameters)
        s3handler = S3Handler(self.session, self.parameters,
                              runtime_config=self._runtime_config,
                              result_queue=result_queue)
        s3_stream_handler = S3StreamHandler(self.session, self.parameters,
                                            result_queue=result_queue)

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
                            's3_handler': [s3handler]}
        elif self.cmd == 'cp' and self.parameters['is_stream']:
            command_dict = {'setup': [stream_file_info],
                            's3_handler': [s3_stream_handler]}
        elif self.cmd == 'cp':
            command_dict = {'setup': [files],
                            'file_generator': [file_generator],
                            'filters': [create_filter(self.parameters)],
                            'file_info_builder': [file_info_builder],
                            's3_handler': [s3handler]}
        elif self.cmd == 'rm':
            command_dict = {'setup': [files],
                            'file_generator': [file_generator],
                            'filters': [create_filter(self.parameters)],
                            'file_info_builder': [file_info_builder],
                            's3_handler': [s3handler]}
        elif self.cmd == 'mv':
            command_dict = {'setup': [files],
                            'file_generator': [file_generator],
                            'filters': [create_filter(self.parameters)],
                            'file_info_builder': [file_info_builder],
                            's3_handler': [s3handler]}
        elif self.cmd == 'mb':
            command_dict = {'setup': [taskinfo],
                            's3_handler': [s3handler]}
        elif self.cmd == 'rb':
            command_dict = {'setup': [taskinfo],
                            's3_handler': [s3handler]}

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
        if files[0].num_tasks_warned > 0:
            rc = 2
        return rc


class CommandParameters(object):
    """
    This class is used to do some initial error based on the
    parameters and arguments passed to the command line.
    """
    def __init__(self, cmd, parameters, usage):
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
        if 'dir_op' not in parameters:
            self.parameters['dir_op'] = False
        if 'follow_symlinks' not in parameters:
            self.parameters['follow_symlinks'] = True
        if 'source_region' not in parameters:
            self.parameters['source_region'] = None
        if self.cmd in ['sync', 'mb', 'rb']:
            self.parameters['dir_op'] = True

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

    def _validate_streaming_paths(self):
        self.parameters['is_stream'] = False
        if self.parameters['src'] == '-' or self.parameters['dest'] == '-':
            self.parameters['is_stream'] = True
            self.parameters['dir_op'] = False
            self.parameters['only_show_errors'] = True
        if self.parameters['is_stream'] and self.cmd != 'cp':
            raise ValueError("Streaming currently is only compatible with "
                             "single file cp commands")

    def _validate_path_args(self):
        # If we're using a mv command, you can't copy the object onto itself.
        params = self.parameters
        if self.cmd == 'mv' and self._same_path(params['src'], params['dest']):
            raise ValueError("Cannot mv a file onto itself: '%s' - '%s'" % (
                params['src'], params['dest']))

    def _same_path(self, src, dest):
        if not self.parameters['paths_type'] == 's3s3':
            return False
        elif src == dest:
            return True
        elif dest.endswith('/'):
            src_base = os.path.basename(src)
            return src == os.path.join(dest, src_base)

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

    def check_src_path(self, paths):
        """
        This checks the source paths to deem if they are valid.  The check
        performed in S3 is first it lists the objects using the source path.
        If there is an error like the bucket does not exist, the error will be
        caught with ``check_error()`` function.  If the operation is on a
        single object in s3, it checks that a list of object was returned and
        that the first object listed is the name of the specified in the
        command line.  If the operation is on objects under a common prefix,
        it will check that there are common prefixes and objects under
        the specified prefix.
        For local files, it first checks that the path exists.  Then it checks
        that the path is a directory if it is a directory operation or that
        the path is a file if the operation is on a single file.
        """
        src_path = paths[0]
        dir_op = self.parameters['dir_op']
        if not src_path.startswith('s3://'):
            src_path = os.path.abspath(src_path)
            if os.path.exists(src_path):
                if os.path.isdir(src_path) and not dir_op:
                    raise Exception("Error: Requires a local file")
                elif os.path.isfile(src_path) and dir_op:
                    raise Exception("Error: Requires a local directory")
                else:
                    pass
            else:
                raise Exception("Error: Local path does not exist")

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
