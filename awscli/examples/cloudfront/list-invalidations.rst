**To list CloudFront invalidations**

The following command retrieves a list of invalidations for a CloudFront web distribution with the ID ``S11A16G5KZMEQD``::

  aws cloudfront list-invalidations --distribution-id S11A16G5KZMEQD

The distribution ID is available in the output of ``create-distribution`` and ``list-distributions``.

Output::

  {
      "InvalidationList": {
          "Marker": "",
          "Items": [
              {
                  "Status": "Completed",
                  "Id": "YNY2LI2BVJ4NJU",
                  "CreateTime": "2015-08-31T21:15:52.042Z"
              }
          ],
          "IsTruncated": false,
          "MaxItems": 100,
          "Quantity": 1
      }
  }
