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
import six
import sys

from dateutil.parser import parse
from dateutil.tz import tzlocal

from awscli.customizations.commands import BasicCommand
from awscli.customizations.s3.comparator import Comparator
from awscli.customizations.s3.fileinfobuilder import FileInfoBuilder
from awscli.customizations.s3.fileformat import FileFormat
from awscli.customizations.s3.filegenerator import FileGenerator
from awscli.customizations.s3.fileinfo import TaskInfo
from awscli.customizations.s3.filters import create_filter
from awscli.customizations.s3.s3handler import S3Handler
from awscli.customizations.s3.utils import find_bucket_key, uni_print, \
    AppendFilter


RECURSIVE = {'name': 'recursive', 'action': 'store_true', 'dest': 'dir_op',
             'help_text': (
                 "Command is performed on all files or objects "
                 "under the specified directory or prefix.")}

DRYRUN = {'name': 'dryrun', 'action': 'store_true',
          'help_text': (
              "Displays the operations that would be performed using the "
              "specified command without actually running them.")}

DELETE = {'name': 'delete', 'action': 'store_true',
          'help_text': (
              "Files that exist in the destination but not in the source are "
              "deleted during sync.")}

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
           "Sets the ACl for the object when the command is "
           "performed.  Only accepts values of ``private``, ``public-read``, "
           "``public-read-write``, ``authenticated-read``, "
           "``bucket-owner-read``, ``bucket-owner-full-control`` and "
           "``log-delivery-write``.")}

GRANTS = {'name': 'grants', 'nargs': '+',
          'help_text': (
              "Grant specific permissions to individual users or groups. You "
              "can supply a list of grants of the form::<p/>  --grants "
              "Permission=Grantee_Type=Grantee_ID [Permission=Grantee_Type="
              "Grantee_ID ...]<p/>Each value contains the following elements:"
              "<p/><ul><li><code>Permission</code> - Specifies "
              "the granted permissions, and can be set to read, readacl, "
              "writeacl, or full.</li><li><code>Grantee_Type</code> - "
              "Specifies how the grantee is to be identified, and can be set "
              "to uri, emailaddress, or id.</li><li><code>Grantee_ID</code> - "
              "Specifies the grantee based on Grantee_Type.</li></ul>The "
              "<code>Grantee_ID</code> value can be one of:<ul><li><b>uri</b> "
              "- The group's URI. For more information, see "
              '<a href="http://docs.aws.amazon.com/AmazonS3/latest/dev/ACLOverview.html#SpecifyingGrantee">'
              "Who Is a Grantee?</a></li>"
              "<li><b>emailaddress</b> - The account's email address.</li>"
              "<li><b>id</b> - The account's canonical ID</li></ul>"
              "</li></ul>"
              "For more information on Amazon S3 access control, see "
              '<a href="http://docs.aws.amazon.com/AmazonS3/latest/dev/UsingAuthAccess.html">Access Control</a>')}

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

EXPIRES = {'name': 'expires', 'nargs': 1, 'help_text': ("The date and time at "
           "which the object is no longer cacheable.")}

SIZE_ONLY = {'name': 'size-only', 'action': 'store_true',
             'help_text': (
                 'Makes the size of each key the only criteria used to '
                 'decide whether to sync from source to destination.')}

EXACT_TIMESTAMPS = {'name': 'exact-timestamps', 'action': 'store_true',
                    'help_text': (
                        'When syncing from S3 to local, same-sized '
                        'items will be ignored only when the timestamps '
                        'match exactly. The default behavior is to ignore '
                        'same-sized items unless the local version is newer '
                        'than the S3 version.')}

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

TRANSFER_ARGS = [DRYRUN, QUIET, RECURSIVE, INCLUDE, EXCLUDE, ACL,
                 FOLLOW_SYMLINKS, NO_FOLLOW_SYMLINKS, NO_GUESS_MIME_TYPE,
                 SSE, STORAGE_CLASS, GRANTS, WEBSITE_REDIRECT, CONTENT_TYPE,
                 CACHE_CONTROL, CONTENT_DISPOSITION, CONTENT_ENCODING,
                 CONTENT_LANGUAGE, EXPIRES, SOURCE_REGION]

SYNC_ARGS = [DELETE, EXACT_TIMESTAMPS, SIZE_ONLY] + TRANSFER_ARGS


def get_endpoint(service, region, endpoint_url, verify):
    return service.get_endpoint(region_name=region, endpoint_url=endpoint_url,
                                verify=verify)


class S3Command(BasicCommand):
    def _run_main(self, parsed_args, parsed_globals):
        self.service = self._session.get_service('s3')
        self.endpoint = get_endpoint(self.service, parsed_globals.region,
                                     parsed_globals.endpoint_url,
                                     parsed_globals.verify_ssl)


class ListCommand(S3Command):
    NAME = 'ls'
    DESCRIPTION = ("List S3 objects and common prefixes under a prefix or "
                   "all S3 buckets. Note that the --output argument "
                   "is ignored for this command.")
    USAGE = "<S3Path> or NONE"
    ARG_TABLE = [{'name': 'paths', 'nargs': '?', 'default': 's3://',
                  'positional_arg': True, 'synopsis': USAGE}, RECURSIVE]
    EXAMPLES = BasicCommand.FROM_FILE('s3/ls.rst')

    def _run_main(self, parsed_args, parsed_globals):
        super(ListCommand, self)._run_main(parsed_args, parsed_globals)
        path = parsed_args.paths
        if path.startswith('s3://'):
            path = path[5:]
        bucket, key = find_bucket_key(path)
        if not bucket:
            self._list_all_buckets()
        elif parsed_args.dir_op:
            # Then --recursive was specified.
            self._list_all_objects_recursive(bucket, key)
        else:
            self._list_all_objects(bucket, key)
        return 0

    def _list_all_objects(self, bucket, key):

        operation = self.service.get_operation('ListObjects')
        iterator = operation.paginate(self.endpoint, bucket=bucket,
                                      prefix=key, delimiter='/')
        for _, response_data in iterator:
            self._display_page(response_data)

    def _display_page(self, response_data, use_basename=True):
        common_prefixes = response_data['CommonPrefixes']
        contents = response_data['Contents']
        for common_prefix in common_prefixes:
            prefix_components = common_prefix['Prefix'].split('/')
            prefix = prefix_components[-2]
            pre_string = "PRE".rjust(30, " ")
            print_str = pre_string + ' ' + prefix + '/\n'
            uni_print(print_str)
            sys.stdout.flush()
        for content in contents:
            last_mod_str = self._make_last_mod_str(content['LastModified'])
            size_str = self._make_size_str(content['Size'])
            if use_basename:
                filename_components = content['Key'].split('/')
                filename = filename_components[-1]
            else:
                filename = content['Key']
            print_str = last_mod_str + ' ' + size_str + ' ' + \
                filename + '\n'
            uni_print(print_str)
            sys.stdout.flush()

    def _list_all_buckets(self):
        operation = self.service.get_operation('ListBuckets')
        response_data = operation.call(self.endpoint)[1]
        buckets = response_data['Buckets']
        for bucket in buckets:
            last_mod_str = self._make_last_mod_str(bucket['CreationDate'])
            print_str = last_mod_str + ' ' + bucket['Name'] + '\n'
            uni_print(print_str)
            sys.stdout.flush()

    def _list_all_objects_recursive(self, bucket, key):
        operation = self.service.get_operation('ListObjects')
        iterator = operation.paginate(self.endpoint, bucket=bucket,
                                      prefix=key)
        for _, response_data in iterator:
            self._display_page(response_data, use_basename=False)

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
        size_str = str(size)
        return size_str.rjust(10, ' ')


class WebsiteCommand(S3Command):
    DESCRIPTION = 'Set the website configuration for a bucket.'
    USAGE = 's3://bucket [--index-document|--error-document] value'
    ARG_TABLE = [{'name': 'paths', 'nargs': 1, 'positional_arg': True,
                  'synopsis': USAGE}, INDEX_DOCUMENT, ERROR_DOCUMENT]

    def _run_main(self, parsed_args, parsed_globals):
        super(WebsiteCommand, self)._run_main(parsed_args, parsed_globals)
        operation = self.service.get_operation('PutBucketWebsite')
        bucket = self._get_bucket_name(parsed_args.paths[0])
        website_configuration = self._build_website_configuration(parsed_args)
        operation.call(self.endpoint, bucket=bucket,
                       website_configuration=website_configuration)
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
        cmd_params = CommandParameters(self._session, self.NAME, params,
                                       self.USAGE)
        cmd_params.add_region(parsed_globals)
        cmd_params.add_endpoint_url(parsed_globals)
        cmd_params.add_verify_ssl(parsed_globals)
        cmd_params.add_paths(parsed_args.paths)
        cmd_params.check_force(parsed_globals)
        cmd = CommandArchitecture(self._session, self.NAME,
                                  cmd_params.parameters)
        cmd.set_endpoints()
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


class CpCommand(S3TransferCommand):
    NAME = 'cp'
    DESCRIPTION = "Copies a local file or S3 object to another location " \
                  "locally or in S3."
    USAGE = "<LocalPath> <S3Path> or <S3Path> <LocalPath> " \
            "or <S3Path> <S3Path>"
    ARG_TABLE = [{'name': 'paths', 'nargs': 2, 'positional_arg': True,
                  'synopsis': USAGE}] + TRANSFER_ARGS
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
                 EXCLUDE]
    EXAMPLES = BasicCommand.FROM_FILE('s3/rm.rst')


class SyncCommand(S3TransferCommand):
    NAME = 'sync'
    DESCRIPTION = "Syncs directories and S3 prefixes."
    USAGE = "<LocalPath> <S3Path> or <S3Path> " \
            "<LocalPath> or <S3Path> <S3Path>"
    ARG_TABLE = [{'name': 'paths', 'nargs': 2, 'positional_arg': True,
                  'synopsis': USAGE}] + SYNC_ARGS
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
    def __init__(self, session, cmd, parameters):
        self.session = session
        self.cmd = cmd
        self.parameters = parameters
        self.instructions = []
        self._service = self.session.get_service('s3')
        self._endpoint = None
        self._source_endpoint = None

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

    def create_instructions(self):
        """
        This function creates the instructions based on the command name and
        extra parameters.  Note that all commands must have an s3_handler
        instruction in the instructions and must be at the end of the
        instruction list because it sends the request to S3 and does not
        yield anything.
        """
        if self.cmd not in ['mb', 'rb']:
            self.instructions.append('file_generator')
        if self.parameters.get('filters'):
            self.instructions.append('filters')
        if self.cmd == 'sync':
            self.instructions.append('comparator')
        if self.cmd not in ['mb', 'rb']:
            self.instructions.append('file_info_builder')
        self.instructions.append('s3_handler')

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
        operation_name = cmd_translation[paths_type][self.cmd]
        file_generator = FileGenerator(self._service,
                                       self._source_endpoint,
                                       operation_name,
                                       self.parameters['follow_symlinks'])
        rev_generator = FileGenerator(self._service, self._endpoint, '',
                                      self.parameters['follow_symlinks'])
        taskinfo = [TaskInfo(src=files['src']['path'],
                             src_type='s3',
                             operation_name=operation_name,
                             service=self._service,
                             endpoint=self._endpoint)]
        file_info_builder = FileInfoBuilder(self._service, self._endpoint,
                                 self._source_endpoint, self.parameters) 
        s3handler = S3Handler(self.session, self.parameters)

        command_dict = {}
        if self.cmd == 'sync':
            command_dict = {'setup': [files, rev_files],
                            'file_generator': [file_generator,
                                               rev_generator],
                            'filters': [create_filter(self.parameters),
                                        create_filter(self.parameters)],
                            'comparator': [Comparator(self.parameters)],
                            'file_info_builder': [file_info_builder],
                            's3_handler': [s3handler]}
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
        # tasks failed.  This means that files[0] now contains
        # the number of failed tasks.  In terms of the RC, we're
        # keeping it simple and saying that > 0 failed tasks
        # will give a 1 RC.
        rc = 0
        if files[0] > 0:
            rc = 1
        return rc


class CommandParameters(object):
    """
    This class is used to do some initial error based on the
    parameters and arguments passed to the command line.
    """
    def __init__(self, session, cmd, parameters, usage):
        """
        Stores command name and parameters.  Ensures that the ``dir_op`` flag
        is true if a certain command is being used.
        """
        self.session = session
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
        self._validate_path_args()

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

    def _verify_bucket_exists(self, bucket_name):
        session = self.session
        service = session.get_service('s3')
        endpoint = service.get_endpoint(self.parameters['region'])
        operation = service.get_operation('ListObjects')
        # This will raise an exception if the bucket does not exist.
        operation.call(endpoint, bucket=bucket_name, max_keys=0)

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

    def check_force(self, parsed_globals):
        """
        This function recursive deletes objects in a bucket if the force
        parameters was thrown when using the remove bucket command.
        """
        if 'force' in self.parameters:
            if self.parameters['force']:
                bucket = find_bucket_key(self.parameters['src'][5:])[0]
                path = 's3://' + bucket
                try:
                    del_objects = RmCommand(self.session)
                    del_objects([path, '--recursive'], parsed_globals)
                except:
                    pass

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
