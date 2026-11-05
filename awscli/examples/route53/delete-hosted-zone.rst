**To delete a hosted zone**

The following ``delete-hosted-zone`` example deletes the hosted zone with an ``id`` of ``Z36KTIQEXAMPLE``. ::

    aws route53 delete-hosted-zone \
        --id Z36KTIQEXAMPLE

Output::

    {
        "ChangeInfo": {
            "Id": "/change/C2682N5HEXAMPLE",
            "Status": "PENDING",
            "SubmittedAt": "2014-04-01T19:12:45.384Z"
        }
    }

For more information, see `Deleting a public hosted zone <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/DeleteHostedZone.html>`__ in the *Amazon Route 53 Developer Guide*.
