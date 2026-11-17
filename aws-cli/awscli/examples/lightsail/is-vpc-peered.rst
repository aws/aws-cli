**To identify if your Amazon Lightsail virtual private cloud is peered**

The following ``is-vpc-peered`` example returns the peering status of the Amazon Lightsail virtual private cloud (VPC) for the current AWS Region. ::

    aws lightsail is-vpc-peered

Output::

    {
        "isPeered": true
    }

For more information, see `Connect Lightsail resources to AWS services using VPC peering <https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-set-up-vpc-peering-with-aws-resources.html>`__ in the *Amazon Lightsail User Guide*.
