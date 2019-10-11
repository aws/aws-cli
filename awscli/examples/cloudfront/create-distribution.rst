**To create a CloudFront Web Distribution**

You can create a CloudFront web distribution for an S3 domain (such as
my-bucket.s3.amazonaws.com) or for a custom domain (such as example.com).
The following command shows an example for an S3 domain, and optionally also
specifies a default root object::

  aws cloudfront create-distribution \
    --origin-domain-name my-bucket.s3.amazonaws.com \
    --default-root-object index.html

Or you can use the following command together with a JSON document to do the
same thing::

  aws cloudfront create-distribution --distribution-config file://distconfig.json

The file ``distconfig.json`` is a JSON document in the current folder that defines a CloudFront distribution::

  {
    "CallerReference": "my-distribution-2015-09-01",
    "Aliases": {
      "Quantity": 0
    },
    "DefaultRootObject": "index.html",
    "Origins": {
      "Quantity": 1,
      "Items": [
        {
          "Id": "my-origin",
          "DomainName": "my-bucket.s3.amazonaws.com",
          "S3OriginConfig": {
            "OriginAccessIdentity": ""
          }
        }
      ]
    },
    "DefaultCacheBehavior": {
      "TargetOriginId": "my-origin",
      "ForwardedValues": {
        "QueryString": true,
        "Cookies": {
          "Forward": "none"
        }
      },
      "TrustedSigners": {
        "Enabled": false,
        "Quantity": 0
      },
      "ViewerProtocolPolicy": "allow-all",
      "MinTTL": 3600
    },
    "CacheBehaviors": {
      "Quantity": 0
    },
    "Comment": "",
    "Logging": {
      "Enabled": false,
      "IncludeCookies": true,
      "Bucket": "",
      "Prefix": ""
    },
    "PriceClass": "PriceClass_All",
    "Enabled": true
  }


Output::

  {
      "Distribution": {
          "Status": "InProgress",
          "DomainName": "d2wkuj2w9l34gt.cloudfront.net",
          "InProgressInvalidationBatches": 0,
          "DistributionConfig": {
              "Comment": "",
              "CacheBehaviors": {
                  "Quantity": 0
              },
              "Logging": {
                  "Bucket": "",
                  "Prefix": "",
                  "Enabled": false,
                  "IncludeCookies": false
              },
              "Origins": {
                  "Items": [
                      {
                          "OriginPath": "",
                          "S3OriginConfig": {
                              "OriginAccessIdentity": ""
                          },
                          "Id": "my-origin",
                          "DomainName": "my-bucket.s3.amazonaws.com"
                      }
                  ],
                  "Quantity": 1
              },
              "DefaultRootObject": "",
              "PriceClass": "PriceClass_All",
              "Enabled": true,
              "DefaultCacheBehavior": {
                  "TrustedSigners": {
                      "Enabled": false,
                      "Quantity": 0
                  },
                  "TargetOriginId": "my-origin",
                  "ViewerProtocolPolicy": "allow-all",
                  "ForwardedValues": {
                      "Headers": {
                          "Quantity": 0
                      },
                      "Cookies": {
                          "Forward": "none"
                      },
                      "QueryString": true
                  },
                  "MaxTTL": 31536000,
                  "SmoothStreaming": false,
                  "DefaultTTL": 86400,
                  "AllowedMethods": {
                      "Items": [
                          "HEAD",
                          "GET"
                      ],
                      "CachedMethods": {
                          "Items": [
                              "HEAD",
                              "GET"
                          ],
                          "Quantity": 2
                      },
                      "Quantity": 2
                  },
                  "MinTTL": 3600
              },
              "CallerReference": "my-distribution-2015-09-01",
              "ViewerCertificate": {
                  "CloudFrontDefaultCertificate": true,
                  "MinimumProtocolVersion": "SSLv3"
              },
              "CustomErrorResponses": {
                  "Quantity": 0
              },
              "Restrictions": {
                  "GeoRestriction": {
                      "RestrictionType": "none",
                      "Quantity": 0
                  }
              },
              "Aliases": {
                  "Quantity": 0
              }
          },
          "ActiveTrustedSigners": {
              "Enabled": false,
              "Quantity": 0
          },
          "LastModifiedTime": "2015-08-31T21:11:29.093Z",
          "Id": "S11A16G5KZMEQD"
      },
      "ETag": "E37HOT42DHPVYH",
      "Location": "https://cloudfront.amazonaws.com/2015-04-17/distribution/S11A16G5KZMEQD"
  }
