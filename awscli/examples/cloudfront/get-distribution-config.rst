The following command gets a distribution config for a CloudFront distribution with the ID ``S11A16G5KZMEQD``::

  aws cloudfront get-distribution-config --id S11A16G5KZMEQD

The distribution ID is available in the output of ``create-distribution`` and ``list-distributions``.

Output::

  {
      "ETag": "E37HOT42DHPVYH",
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
      }
  }