**To delete a connection group**

The following ``delete-connection-group`` example deletes a connection group. The connection group must be disabled and can't be associated with any CloudFront resources. ::

    aws cloudfront delete-connection-group \
        --id cg_2wjLpjbHkLUdhWAjHllcOeABC \
        --if-match ETVPDKIKX0DABC

This command produces no output.

For more information about managing connection groups, see `Create custom connection group (optional) <https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/custom-connection-group.html>`__ in the *Amazon CloudFront Developer Guide*.