**To check the availability of a CNAME**

The following ``check-dns-availability`` example checks the availability of the subdomain ``my-cname.elasticbeanstalk.com``. ::

    aws elasticbeanstalk check-dns-availability \
        --cname-prefix my-cname

Output::

    {
        "Available": true,
        "FullyQualifiedCNAME": "my-cname.elasticbeanstalk.com"
    }

For more information, see `Your Elastic Beanstalk environment's Domain name <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/customdomains.html>`__ in the *AWS Elastic Beanstalk Developer Guide*.
