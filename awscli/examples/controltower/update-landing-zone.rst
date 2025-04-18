**To Update Control Tower Landing Zone**

The following ``update-landing-zone`` example updates AWS Control Tower landing zone ::

    aws controltower update-landing-zone \
        --landing-zone-identifier arn:aws:controltower:us-east-1:123456789012:landingzone/13CJG46WZKXXX4X5 \
        --landing-zone-version 3.3 \
        --manifest "file://UpdateLandingZoneManifest.json"

Output::

    {
        "operationIdentifier": "53XXXXXX-b2XX-97XX-c6XX-474XXXXXXXXX"
    }
For more information, see `AWS Control Tower Getting Started <https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-with-control-tower.html>`__ in the *AWS Control Tower User Guide*.