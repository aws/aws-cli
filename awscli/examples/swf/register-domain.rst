**To register a domain**

The following ``register-domain`` example registers a new domain. There are two required parameters, ``--name``, which takes the domain name, and ``--workflow-execution-retention-period-in-days``, which takes an integer to specify the number of days to retain workflow execution data on this domain, up to a maximum period of 90 days (for more information, see the `SWF FAQ <https://aws.amazon.com/swf/faqs/#retain_limit>`). Workflow execution data
will not be retained after the specified number of days have passed. ::

    aws swf register-domain \
        --name MyNeatNewDomain \
        --workflow-execution-retention-period-in-days 0

This command produces no output.

When you register a domain, nothing is returned, but you can use ``swf list-domains`` or ``swf describe-domain`` to see the new domain. ::

    aws swf list-domains \
        --registration-status REGISTERED

Output::

    {
        "domainInfos": [
            {
                "status": "REGISTERED",
                "name": "DataFrobotz"
            },
            {
                "status": "REGISTERED",
                "name": "MyNeatNewDomain"
            },
            {
                "status": "REGISTERED",
                "name": "erontest"
            }
        ]
    }

The following example uses ``swf describe-domain`` to see the new domain. ::

    aws swf describe-domain \
        --name MyNeatNewDomain

Output::

    {
        "domainInfo": {
            "status": "REGISTERED",
            "name": "MyNeatNewDomain"
        },
        "configuration": {
            "workflowExecutionRetentionPeriodInDays": "0"
        }
    }

For more information, see `Domains in Amazon SWF <https://docs.aws.amazon.com/amazonswf/latest/developerguide/swf-dev-domains.html>`__ in the *Amazon Simple Workflow Service Developer Guide*.
