**To Create Control Tower Landing Zone**

The following ``create-landing-zone`` example creates AWS Control Tower Landing Zone ::

    aws controltower create-landing-zone \
        --landing-zone-version 3.3 \
        --manifest "file://LandingZoneManifest.json"

Output::

    {
        "arn": "arn:aws:controltower:us-east-1:123456789012:landingzone/13CJG46WZKXXX4X5",
        "operationIdentifier": "55XXXXXX-e2XX-41XX-a7XX-446XXXXXXXXX"
    }

For more information, see `AWS Control Tower Getting Started <https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-with-control-tower.html>`__ in the *AWS Control Tower User Guide*.