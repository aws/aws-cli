**To list the hosted zones associated with the current AWS account**

The following ``list-hosted-zones`` example lists summary information about the first 100 hosted zones that are associated with the current AWS account. ::

    aws route53 list-hosted-zones

Output::

    {
        "HostedZones": [
            {
                "Id": "/hostedzone/Z1R8UBAEXAMPLE",
                "Name": "example.com.",
                "CallerReference": "2014-04-01-18:47",
                "Config": {
                    "Comment": "command-line version",
                    "PrivateZone": false
                },
                "ResourceRecordSetCount": 2
            }
        ]
    }

If you have more than 100 hosted zones, or if you want to list them in groups smaller than 100, include the ``--max-items`` parameter. For example, to list hosted zones one at a time, use the following command. ::

    aws route53 list-hosted-zones \
        --max-items 1

To view information about the next hosted zone, take the value of ``NextToken`` from the response to the previous command, and include it in the ``--starting-token`` parameter, as shown in the following example. ::

    aws route53 list-hosted-zones \
        --max-items 1 \
        --starting-token Z3M3LMPEXAMPLE

For more information, see `Listing public hosted zones <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/ListInfoOnHostedZone.html>`__ in the *Amazon Route 53 Developer Guide*.
