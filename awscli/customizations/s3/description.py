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
