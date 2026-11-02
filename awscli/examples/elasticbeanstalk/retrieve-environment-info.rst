**To retrieve tailed logs**

The following ``retrieve-environment-info`` example retrieves a link to logs from an environment named ``my-env``. ::

    aws elasticbeanstalk retrieve-environment-info \
        --environment-name my-env \
        --info-type tail

Output::

    {
        "EnvironmentInfo": [
            {
                "SampleTimestamp": "2015-08-20T22:23:17.703Z",
                "Message": "https://elasticbeanstalk-us-west-2-0123456789012.s3.amazonaws.com/resources/environments/logs/tail/e-fyqyju3yjs/i-09c1c867/TailLogs-1440109397703.out?AWSAccessKeyId=AKGPT4J56IAJ2EUBL5CQ&Expires=1440195891&Signature=n%2BEalOV6A2HIOx4Rcfb7LT16bBM%3D",
                "InfoType": "tail",
                "Ec2InstanceId": "i-09c1c867"
            }
        ]
    }

View the link in a browser. Prior to retrieval, logs must be requested with `request-environment-info <https://docs.aws.amazon.com/cli/latest/reference/elasticbeanstalk/request-environment-info.html>`__.

For more information, see `Viewing logs from Amazon EC2 instances in your Elastic Beanstalk environment <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.logging.html>`__ in the *AWS Elastic Beanstalk Developer Guide*.
