**To describe database schemas**

The following ``describe-schemas`` example lists the available tables at an endpoint. ::

    aws dms describe-schemas \
        --endpoint-arn "arn:aws:dms:us-west-2:123456789012:endpoint:6GGI6YPWWGAYUVLKIB732KEVWA"

Output::

    {
        "Schemas": [
            "prodrep"
        ]
    }

For more information, see `Working with AWS DMS endpoints <https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Endpoints.html>`__ in the *AWS Database Migration Service User Guide*.

