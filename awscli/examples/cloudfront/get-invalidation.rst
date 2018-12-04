The following command retrieves an invalidation with the ID ``YNY2LI2BVJ4NJU`` for a CloudFront web distribution with the ID ``S11A16G5KZMEQD``::

  aws cloudfront get-invalidation --id YNY2LI2BVJ4NJU --distribution-id S11A16G5KZMEQD

The distribution ID is available in the output of ``create-distribution`` and ``list-distributions``. The invalidation ID is available in the output of ``create-invalidation`` and ``list-invalidations``.

Output::

  {
      "Invalidation": {
          "Status": "Completed",
          "InvalidationBatch": {
              "Paths": {
                  "Items": [
                      "/index.html",
                      "/error.html"
                  ],
                  "Quantity": 2
              },
              "CallerReference": "my-invalidation-2015-09-01"
          },
          "Id": "YNY2LI2BVJ4NJU",
          "CreateTime": "2015-08-31T21:15:52.042Z"
      }
  }
