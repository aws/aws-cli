**To list CloudFront invalidations**

The following ``list-invalidations`` example gets a list of the invalidations for the CloudFront
distribution with the ID ``EDFDVBD6EXAMPLE``. ::

    aws cloudfront list-invalidations \
        --distribution-id EDFDVBD6EXAMPLE

Output::

    {
        "InvalidationList": {
            "Marker": "",
            "Items": [
                {
                    "Status": "Completed",
                    "Id": "YNY2LI2BVJ4NJU",
                    "CreateTime": "2019-08-31T21:15:52.042Z"
                }
            ],
            "IsTruncated": false,
            "MaxItems": 100,
            "Quantity": 1
        }
    }

For more information, see `Invalidate files to remove content <https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html>`__ in the *Amazon CloudFront Developer Guide*.
