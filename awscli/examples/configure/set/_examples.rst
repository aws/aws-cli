Given an empty config file, the following commands::

    $ aws configure set aws_access_key_id default_access_key
    $ aws configure set aws_secret_access_key default_secret_key
    $ aws configure set default.region us-west-2
    $ aws configure set region us-west-1 --profile testing
    $ aws configure set profile.testing2.region eu-west-1
    $ aws configure set preview.cloudsearch true

will produce the following config file::

    [default]
    aws_access_key_id = default_access_key
    aws_secret_access_key = default_secret_key
    region = us-west-2

    [profile testing]
    region = us-west-1

    [profile testing2]
    region = eu-west-1

    [preview]
    cloudsearch = true
