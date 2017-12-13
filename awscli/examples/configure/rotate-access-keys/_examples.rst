Given an existing config file::

    [default]
    aws_access_key_id = default_access_key
    aws_secret_access_key = default_secret_key

    [other]
    aws_access_key_id = other_access_key
    aws_secret_access_key = other_secret_key

The following commands::

    $ aws configure rotate-access-key

will produce the following config file::

    [default]
    aws_access_key_id = renew_access_key
    aws_secret_access_key = renew_secret_key

    [other]
    aws_access_key_id = other_access_key
    aws_secret_access_key = other_secret_key

Then the following commands::

    $ aws --profile=other configure rotate-access-key

will produce the following config file::

    [default]
    aws_access_key_id = renew_access_key
    aws_secret_access_key = renew_secret_key

    [other]
    aws_access_key_id = renew_other_access_key
    aws_secret_access_key = renew_other_secret_key
