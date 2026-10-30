**To describe all events**

The following ``describe-events`` example returns all events. By default, the output is in JSON format. ::

    aws redshift describe-events

Output::

    {
        "Events": [
            {
                "Date": "2013-01-22T19:17:03.640Z",
                "SourceIdentifier": "myclusterparametergroup",
                "Message": "Cluster parameter group myclusterparametergroup has been created.",
                "SourceType": "cluster-parameter-group"
            }
        ]
    }

You can also obtain the same information in text format using the ``--output text`` option. ::

    aws redshift describe-events \
        --output text

Output::

    2013-01-22T19:17:03.640Z    myclusterparametergroup Cluster parameter group myclusterparametergroup has been created.       cluster-parameter-group


