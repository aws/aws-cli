# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


def add_command_descriptions(cmd_dict):
    """
    This function adds descritpions to the various commands along with
    usage.
    """
    cmd_dict['cp']['description'] = "Copies a local file or S3 object to \
                                     another location locally or in S3."
    cmd_dict['cp']['usage'] = "<LocalPath> <S3Path> or <S3Path> <LocalPath> " \
                              "or <S3Path> <S3Path>"

    cmd_dict['mv']['description'] = "Moves a local file or S3 object to " \
                                    "another location locally or in S3."
    cmd_dict['mv']['usage'] = "<LocalPath> <S3Path> or <S3Path> <LocalPath> " \
                              "or <S3Path> <S3Path>"

    cmd_dict['rm']['description'] = "Deletes an S3 object."
    cmd_dict['rm']['usage'] = "<S3Path>"

    cmd_dict['sync']['description'] = "Syncs directories and S3 prefixes."
    cmd_dict['sync']['usage'] = "<LocalPath> <S3Path> or <S3Path> " \
                                "<LocalPath> or <S3Path> <S3Path>"

    cmd_dict['ls']['description'] = "List S3 objects and common prefixes " \
                                    "under a prefix or all S3 buckets."
    cmd_dict['ls']['usage'] = "<S3Path> or NONE"

    cmd_dict['mb']['description'] = "Creates an S3 bucket."
    cmd_dict['mb']['usage'] = "<S3Path>"

    cmd_dict['rb']['description'] = "Deletes an S3 bucket."
    cmd_dict['rb']['usage'] = "<S3Path>"


def add_param_descriptions(params_dict):
    """
    This function adds descriptions to the various parameters that can be
    used in commands.
    """
    params_dict['dryrun']['documents'] = "Displays the operations that " \
        "would be performed using the specified command without actually" \
        "running them."

    params_dict['quiet']['documents'] = "Does not display the operations " \
        "performed from the specified command."

    params_dict['recursive']['documents'] = "Command is performed on all" \
        "files or objects under the specified directory or prefix."

    params_dict['delete']['documents'] = "Files that exist in the " \
        "destination but not in the source are deleted during sync."

    params_dict['exclude']['documents'] = "Exclude all files or objects" \
        " from the command that follow the specified pattern."

    params_dict['include']['documents'] = "Include all files or objects in " \
        "the command that follow the specified pattern."

    params_dict['acl']['documents'] = "Sets the ACl for the object when the " \
        "command is performed.  Only accepts values of ``private``, \
        ``public-read``, or ``public-read-write``."

    params_dict['force']['documents'] = "Deletes all objects in the bucket " \
        "including the bucket itself."

    params_dict['no-guess-mime-type']['documents'] = (
        "Do not try to guess the mime type for uploaded files.  By default the "
        "mime type of a file is guessed when it is uploaded.")

    params_dict['content-type']['documents'] = (
        "Specify an explicit content type for this operation.  "
        "This value overrides any guessed mime types.")

    params_dict['cache-control']['documents'] = \
        "Specifies caching behavior along the request/reply chain."

    params_dict['content-disposition']['documents'] = \
        "Specifies presentational information for the object."
    
    params_dict['content-encoding']['documents'] = (
        "Specifies what content encodings have been "
        "applied to the object and thus what decoding mechanisms "
        "must be applied to obtain the media-type referenced "
        "by the Content-Type header field.")
    
    params_dict['content-language']['documents'] = \
        "The language the content is in."

    params_dict['expires']['documents'] = \
        "The date and time at which the object is no longer cacheable."
    
    params_dict['sse']['documents'] = (
        "Enable Server Side Encryption of the object in S3")

    params_dict['storage-class']['documents'] = (
        "The type of storage to use for the object. "
        "Defaults to 'STANDARD'")

    params_dict['website-redirect']['documents'] = (
        "If the bucket is configured as a website, redirects requests "
        "for this object to another object in the same bucket or to an "
        "external URL. Amazon S3 stores the value of this header in the "
        "object metadata.")

    params_dict['grants']['documents'] = (
        "Grant specific permissions to individual users or groups.  "
        "You can supply a list of grants of the form "
        "``permission=grantee`` where permission is one of: "
        "``read``, ``readacl``, ``writeacp``, ``full``")

