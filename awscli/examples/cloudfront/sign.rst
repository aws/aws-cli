**To sign a CloudFront URL**

The following example signs a CloudFront URL. To sign a URL, you need the key
pair ID (called the **Access Key ID** in the AWS Management Console) and the
private key of the trusted signer's CloudFront key pair. For more information
about signed URLs, see `Serving Private Content with Signed URLs and Signed
Cookies
<https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/PrivateContent.html>`_
in the *Amazon CloudFront Developer Guide*.

::

    aws cloudfront sign \
        --url https://d111111abcdef8.cloudfront.net/private-content/private-file.html \
        --key-pair-id APKAEIBAERJR2EXAMPLE \
        --private-key file://cf-signer-priv-key.pem \
        --date-less-than 2020-01-01

Output::

    https://d111111abcdef8.cloudfront.net/private-content/private-file.html?Expires=1577836800&Signature=nEXK7Kby47XKeZQKVc6pwkif6oZc-JWSpDkH0UH7EBGGqvgurkecCbgL5VfUAXyLQuJxFwRQWscz-owcq9KpmewCXrXQbPaJZNi9XSNwf4YKurPDQYaRQawKoeenH0GFteRf9ELK-Bs3nljTLjtbgzIUt7QJNKXcWr8AuUYikzGdJ4-qzx6WnxXfH~fxg4-GGl6l2kgCpXUB6Jx6K~Y3kpVOdzUPOIqFLHAnJojbhxqrVejomZZ2XrquDvNUCCIbePGnR3d24UPaLXG4FKOqNEaWDIBXu7jUUPwOyQCvpt-GNvjRJxqWf93uMobeMOiVYahb-e0KItiQewGcm0eLZQ__&Key-Pair-Id=APKAEIBAERJR2EXAMPLE

**To sign a CloudFront URL using SHA-256**

The following example signs a CloudFront URL using the SHA-256 hash
algorithm, which is recommended for its stronger security posture. The signed
URL includes the ``Hash-Algorithm`` query parameter so that CloudFront verifies
the signature with SHA-256. ::

    aws cloudfront sign \
        --url https://d111111abcdef8.cloudfront.net/private-content/private-file.html \
        --key-pair-id APKAEIBAERJR2EXAMPLE \
        --private-key file://cf-signer-priv-key.pem \
        --date-less-than 2020-01-01 \
        --hash-algorithm SHA256

Output::

    https://d111111abcdef8.cloudfront.net/private-content/private-file.html?Expires=1577836800&Signature=Ws0f2ZmbKkQYTsvoN0T4zNFcYDqQSt6fnlIK2eL~ai2ihqe8vREVnUdKWgD9EYmJ8aSBRlXTb3kHLppdPgFwY7bYEyDrkyqLN2LmA9jk0mwB~T3UCbL2l6bBGUYmSSkZzq2YGRxLxgxfkRSR-cB-Tlk0FYyhbrHBGfkDYzbZN0k_&Key-Pair-Id=APKAEIBAERJR2EXAMPLE&Hash-Algorithm=SHA256

**To sign a CloudFront URL with a wildcard policy resource**

The following example signs a policy for every object under ``/videos/`` and
applies the signature to a specific URL. Because the policy resource contains a
wildcard, a custom policy is used and included in the signed URL. The same
``Policy``, ``Signature`` and ``Key-Pair-Id`` query parameters can be reused
for any URL matching the policy resource. ::

    aws cloudfront sign \
        --url https://d111111abcdef8.cloudfront.net/videos/intro.mp4 \
        --policy-resource "https://d111111abcdef8.cloudfront.net/videos/*" \
        --key-pair-id APKAEIBAERJR2EXAMPLE \
        --private-key file://cf-signer-priv-key.pem \
        --date-less-than 2020-01-01

Output::

    https://d111111abcdef8.cloudfront.net/videos/intro.mp4?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9kMTExMTExYWJjZGVmOC5jbG91ZGZyb250Lm5ldC92aWRlb3MvKiIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTU3NzgzNjgwMH19fV19&Signature=Hu~7UBBFt4Q2z1bKUmRq7o2vwrIJDw6H0Lv4HDZ-Mkn2y~y~8ktcWNkbuCN6FT7hRq0YTVbU8qp4yxX1T4ICtHmYaIpfiGAqWS2PMrUkbXx5ckfk5GHAKIKsJ6oYS-EqLl0cOiYiEb8O8fuRPbdeSP62DBoo-LaM~PTgAGH-M5c_&Key-Pair-Id=APKAEIBAERJR2EXAMPLE
