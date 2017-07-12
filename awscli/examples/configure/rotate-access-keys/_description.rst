Rotate the current access key, as AccessKeys should not be used more than
90 days. You can then add a crontab entry to automatically renew your keys

The ``aws configure rotate-access-key`` command can be used to renew your
current access key, it will first create a new access key then update the
configuration and finally remove the previous access key.

The ``aws_access_key_id``, ``aws_secret_access_key`` of the new created key
will result in the value being writen to the shared credentials file
(``~/.aws/credentials``).  All other values will be written to the config file
(default location is ``~/.aws/config``).
