Given an empty config file, and a credentials.csv downloaded from IAM the following command::

    $ aws configure import test ./credentials.csv

will produce the following ``~/.aws/credentials`` file::

    [test]
    aws_access_key_id = <access key from csv>
    aws_secret_access_key = <secret access key from csv>
