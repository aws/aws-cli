**To list your services**

The following ``list-services`` example lists the services owned or shared with the calling account. The ``--query`` option scopes the results to the Amazon Resource Names (ARN) of the services. ::

    aws vpc-lattice list-services \
        --query items[*].arn

Output::

    [
        "arn:aws:vpc-lattice:us-west-2:123456789012:service/svc-0285b53b2eEXAMPLE",
        "arn:aws:vpc-lattice:us-west-2:123456789111:service/svc-0b8ac96550EXAMPLE"
    ]

For more information, see `Services <https://docs.aws.amazon.com/vpc-lattice/latest/ug/services.html>`__ in the *Amazon VPC Lattice User Guide*.