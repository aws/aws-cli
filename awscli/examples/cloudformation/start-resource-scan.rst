**To start a resource scan**

The following ``start-resource-scan`` example starts a resource scan that scans all existing resources in the current account and Region. ::

    aws cloudformation start-resource-scan

Output::

    {
        "ResourceScanId":
          "arn:aws:cloudformation:us-east-1:123456789012:resourceScan/0a699f15-489c-43ca-a3ef-3e6ecfa5da60"
    }

For more information, see `Start a resource scan with CloudFormation IaC generator <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/iac-generator-start-resource-scan.html>`__ in the *AWS CloudFormation User Guide*.
