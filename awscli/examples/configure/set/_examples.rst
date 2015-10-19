Given an empty config file, the following commands::

    $ aws configure set aws_access_key_id default_access_key
    $ aws configure set aws_secret_access_key default_secret_key
    $ aws configure set default.region us-west-2
    $ aws configure set default.ca_bundle /path/to/ca-bundle.pem
    $ aws configure set region us-west-1 --profile testing
    $ aws configure set profile.testing2.region eu-west-1
    $ aws configure set preview.cloudsearch true

will produce the following config file::

    [default]
    region = us-west-2
    ca_bundle = /path/to/ca-bundle.pem

    [profile testing]
    region = us-west-1

    [profile testing2]
    region = eu-west-1

    [preview]
    cloudsearch = true

and the following ``~/.aws/credentials`` file::

    [default]
    aws_access_key_id = default_access_key
    aws_secret_access_key = default_secret_key
