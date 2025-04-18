**To Reset Control Tower Landing Zone**

The following ``reset-landing-zone`` example resets the AWS Control Tower Landing Zone::

    aws controltower reset-landing-zone \
        --landing-zone-identifier arn:aws:controltower:us-east-1:123456789012:landingzone/13CJG46WZKXXX4X5

Output::

    {
        "operationIdentifier": "73XXXXXX-b2XX-77XX-c6XX-374XXXXXXXXX"
    }

For more information, see `AWS Control Tower Getting Started <https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-with-control-tower.html>`__ in the *AWS Control Tower User Guide*.