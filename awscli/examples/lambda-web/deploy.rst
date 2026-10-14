These examples use ``us-east-1`` as the AWS Region for deployment. The command
selects the AWS Region from ``--region``, the ``AWS_DEFAULT_REGION`` environment
variable, or your AWS CLI configuration. You can use a different AWS Region.
Endpoint and console URLs reflect the AWS Region used for the deployment. A
``MultiRegion`` endpoint uses the global endpoint domain. The endpoint
identifiers are fictitious and do not identify live resources.


**Example 1: To create and deploy a starter application**

The following ``deploy`` example creates a TypeScript starter in ``./my-app``
and deploys it. The command creates or reuses an Amazon Simple Storage Service
(Amazon S3) deployment bucket and an AWS Identity and Access Management (IAM)
execution role. It then creates the Web Function and endpoint. The target path
can be new or can identify an existing empty directory. ::

    aws lambda-web deploy --name my-app --hello-world

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-east-1.on.aws
    Console: https://us-east-1.console.aws.amazon.com/lambda/home#/web-functions/my-app

**Example 2: To create a Web Function from existing source code**

The following ``deploy`` example creates a Web Function from an existing HTTP
server. The ``--create`` option skips the confirmation prompt. If you omit
``--bucket-name`` or ``--execution-role-arn``, the command creates or reuses
the deployment bucket and execution role as needed. ::

    aws lambda-web deploy --name my-app --code ./app --create

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-east-1.on.aws
    Console: https://us-east-1.console.aws.amazon.com/lambda/home#/web-functions/my-app

**Example 3: To deploy new source code**

The following ``deploy`` example deploys a revision to an existing Web
Function and updates its endpoint. ::

    aws lambda-web deploy --name my-app --code ./app

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-east-1.on.aws
    Console: https://us-east-1.console.aws.amazon.com/lambda/home#/web-functions/my-app

**Example 4: To deploy source code with environment variables**

The following ``deploy`` example deploys new source code and adds or replaces
two application environment variables. ::

    aws lambda-web deploy \
        --name my-app \
        --code ./app \
        --env APP_ENV=staging \
        --env FEATURE_FLAG=on

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-east-1.on.aws
    Console: https://us-east-1.console.aws.amazon.com/lambda/home#/web-functions/my-app

**Example 5: To update configuration without uploading source code**

The following ``deploy`` example updates an environment variable and the
request timeout. Because the command omits ``--code``, it reuses the deployed
source code. ::

    aws lambda-web deploy \
        --name my-app \
        --env APP_ENV=production \
        --timeout-seconds 60

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-east-1.on.aws
    Console: https://us-east-1.console.aws.amazon.com/lambda/home#/web-functions/my-app

**Example 6: To create another endpoint**

The following ``deploy`` example creates a ``staging`` endpoint for an
existing Web Function and reuses its deployed source code. The ``--create``
option skips the confirmation prompt. ::

    aws lambda-web deploy \
        --name my-app \
        --endpoint-name staging \
        --create

Output::

    https://f6g7h8i9j0.x9y.lambda-web.us-east-1.on.aws
    Console: https://us-east-1.console.aws.amazon.com/lambda/home#/web-functions/my-app

**Example 7: To create a MultiRegion endpoint**

The following ``deploy`` example creates a ``MultiRegion`` endpoint in two AWS
Regions for an existing Web Function and reuses its deployed source code. The
``--create`` option skips the confirmation prompt. ::

    aws lambda-web deploy \
        --name my-app \
        --endpoint-name global \
        --endpoint-type MultiRegion \
        --regions us-east-1,us-west-2 \
        --create

Output::

    https://k1l2m3n4o5.lambda-web.global.on.aws
    Console: https://us-east-1.console.aws.amazon.com/lambda/home#/web-functions/my-app

**Example 8: To deploy a built entry file with its dependencies**

The following ``deploy`` example packages the project root and uses
``dist/index.js`` as the entry file. Using ``--code .`` instead of
``--code ./dist`` includes dependencies such as ``node_modules`` that are
outside the output directory. The command does not bundle the application.

If you omit ``--entry-point``, the command checks the ``main`` and ``exports``
fields in ``package.json``, then checks common entry files. ::

    aws lambda-web deploy \
        --name my-app \
        --code . \
        --entry-point dist/index.js

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-east-1.on.aws
    Console: https://us-east-1.console.aws.amazon.com/lambda/home#/web-functions/my-app

**Example 9: To select the entry file with an environment variable**

The following ``deploy`` example sets ``AWS_LAMBDA_NODEJS_ENTRYPOINT`` so that
the runtime loads ``src/server.mjs`` directly. Do not use
``AWS_LAMBDA_NODEJS_ENTRYPOINT`` and ``--entry-point`` together. ::

    aws lambda-web deploy \
        --name my-app \
        --code ./app \
        --env AWS_LAMBDA_NODEJS_ENTRYPOINT=src/server.mjs

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-east-1.on.aws
    Console: https://us-east-1.console.aws.amazon.com/lambda/home#/web-functions/my-app
