**To retrieve keys and values for a cost allocation tag**

The following ``get-tags`` example retrieves all cost allocation tags with a key of "Project" and a value that contains "secretProject". ::

    aws ce get-tags \
        --search-string secretProject \
        --time-period Start=2017-01-01,End=2017-05-18 \
        --tag-key Project

Output::

    {
        "ReturnSize": 2,
        "Tags": [
            "secretProject1",
            "secretProject2"
        ],
        "TotalSize": 2
    }

For more information, see `Organizing and tracking costs using AWS cost allocation tags <https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-alloc-tags.html>`__ in the *AWS Billing User Guide*.
