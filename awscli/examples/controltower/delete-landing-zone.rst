**To Decommission Landing Zone**

The following ``delete-landing-zone`` example decommissions the AWS Control Tower landing zone ::

    aws controltower delete-landing-zone \
        --landing-zone-identifier arn:aws:controltower:us-east-1:123456789012:landingzone/13CJG46WZKXXX4X5

Output::

    {
        "operationIdentifier": "47XXXXXX-a6XX-82XX-c9XX-432XXXXXXXXX"
    }
For more information, see `Decommission a Landing Zone <https://docs.aws.amazon.com/controltower/latest/userguide/decommission-landing-zone.html>`__ in the *AWS Control Tower User Guide*.