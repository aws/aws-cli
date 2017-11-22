Given ``~/.aws/credentials`` file after executing ``aws configure`` file::

    [default]
    aws_access_key_id = default_access_key
    aws_secret_access_key = default_secret_key

the following command::

    $ aws configure mfa
    MFA token: 123456

will produce the following credential file::

    [default]
    aws_access_key_id = temporary_access_key
    aws_secret_access_key = temporary_secret_key
    aws_mfa_serial_number = default_mfa_device_serial_number
    aws_access_key_id_saved = default_access_key
    aws_secret_access_key_saved = default_secret_key
    aws_session_token = temporary_session_token

