The following command creates an invalidation for a CloudFront distribution with the ID ``S11A16G5KZMEQD``::

  aws cloudfront create-invalidation --invalidation-batch file://invbatch.json --distribution-id S11A16G5KZMEQD

The distribution ID is available in the output of ``create-distribution`` and ``list-distributions``.

The file ``invbatch.json`` is a JSON document in the current folder that specifies two paths to invalidate::

  {
    "Paths": {
      "Quantity": 2,
      "Items": ["/index.html", "/error.html"]
    },
    "CallerReference": "my-invalidation-2015-09-01"
  }

Output::

  {
      "Invalidation": {
          "Status": "InProgress",
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
      },
      "Location": "https://cloudfront.amazonaws.com/2015-04-17/distribution/S11A16G5KZMEQD/invalidation/YNY2LI2BVJ4NJU"
  }