**To generate an IAM authentication token**

The following ``generate-db-connect-auth-token`` example generates IAM authentication token to connect to a database. ::

    aws dsql generate-db-connect-auth-token \
        --hostname test.us-east-1.prod.sql.dsql.aws.dev \
        --region us-east-1 \
        --expires-in 3600

Output::

    'test.us-east-1.prod.sql.dsql.aws.dev/?Action=DbConnect&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=access_key%2F20241107%2Fus-east-1%2Fdsql%2Faws4_request&X-Amz-Date=20241107T173933Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=b53dae15763139d6a5af5e318b117ff6e66c5ee859b14d44697d159cbe996077'

