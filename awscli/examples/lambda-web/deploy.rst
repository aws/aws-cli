**Example 1: To create and deploy a starter application**

The following ``deploy`` example creates a TypeScript starter in ``./my-app``
and deploys it. The command creates or reuses an Amazon Simple Storage Service
(Amazon S3) deployment bucket and an AWS Identity and Access Management (IAM)
execution role. It then creates the Web Function and endpoint. The target path
can be new or can identify an existing empty directory. ::

    aws lambda-web deploy \
        --name my-app \
        --hello-world

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-west-2.on.aws
    Console: https://us-west-2.console.aws.amazon.com/lambda/home#/web-functions/my-app

For more information, see `Creating a Lambda Web Function <https://docs.aws.amazon.com/lambda/latest/dg/web-functions-create.html>`__ in the *AWS Lambda Developer Guide*.

**Example 2: To create a Web Function from existing source code**

The following ``deploy`` example creates a Web Function from an existing HTTP
server. The ``--create`` option skips the confirmation prompt. If you omit
``--bucket-name`` or ``--execution-role-arn``, the command creates or reuses
the deployment bucket and execution role as needed. ::

    aws lambda-web deploy \
        --name my-app \
        --code ./app \
        --create

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-west-2.on.aws
    Console: https://us-west-2.console.aws.amazon.com/lambda/home#/web-functions/my-app

For more information, see `Creating a Lambda Web Function <https://docs.aws.amazon.com/lambda/latest/dg/web-functions-create.html>`__ in the *AWS Lambda Developer Guide*.

**Example 3: To deploy new source code**

The following ``deploy`` example deploys a revision to an existing Web
Function and updates its endpoint. ::

    aws lambda-web deploy \
        --name my-app \
        --code ./app

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-west-2.on.aws
    Console: https://us-west-2.console.aws.amazon.com/lambda/home#/web-functions/my-app

For more information, see `Deploying Web Functions <https://docs.aws.amazon.com/lambda/latest/dg/web-functions-deploying.html>`__ in the *AWS Lambda Developer Guide*.

**Example 4: To deploy source code with environment variables**

The following ``deploy`` example deploys new source code and adds or replaces
two application environment variables. ::

    aws lambda-web deploy \
        --name my-app \
        --code ./app \
        --env APP_ENV=staging \
        --env FEATURE_FLAG=on

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-west-2.on.aws
    Console: https://us-west-2.console.aws.amazon.com/lambda/home#/web-functions/my-app

For more information, see `Environment variables <https://docs.aws.amazon.com/lambda/latest/dg/web-functions-revisions-env-vars.html>`__ in the *AWS Lambda Developer Guide*.

**Example 5: To update configuration without uploading source code**

The following ``deploy`` example updates an environment variable and the
request timeout. Because the command omits ``--code``, it reuses the deployed
source code. ::

    aws lambda-web deploy \
        --name my-app \
        --env APP_ENV=production \
        --timeout-seconds 60

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-west-2.on.aws
    Console: https://us-west-2.console.aws.amazon.com/lambda/home#/web-functions/my-app

For more information, see `Configuring Lambda Web Functions <https://docs.aws.amazon.com/lambda/latest/dg/web-functions-configuration.html>`__ in the *AWS Lambda Developer Guide*.

**Example 6: To create another endpoint**

The following ``deploy`` example creates a ``staging`` endpoint for an
existing Web Function and reuses its deployed source code. The ``--create``
option skips the confirmation prompt. ::

    aws lambda-web deploy \
        --name my-app \
        --endpoint-name staging \
        --create

Output::

    https://f6g7h8i9j0.x9y.lambda-web.us-west-2.on.aws
    Console: https://us-west-2.console.aws.amazon.com/lambda/home#/web-functions/my-app

For more information, see `Lambda Web Function endpoints <https://docs.aws.amazon.com/lambda/latest/dg/web-functions-endpoints.html>`__ in the *AWS Lambda Developer Guide*.

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
    Console: https://us-west-2.console.aws.amazon.com/lambda/home#/web-functions/my-app

For more information, see `Multi-Region deployment <https://docs.aws.amazon.com/lambda/latest/dg/web-functions-endpoint-replication.html>`__ in the *AWS Lambda Developer Guide*.

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

    https://a1b2c3d4e5.x9y.lambda-web.us-west-2.on.aws
    Console: https://us-west-2.console.aws.amazon.com/lambda/home#/web-functions/my-app

For more information, see `Web Function deployment package <https://docs.aws.amazon.com/lambda/latest/dg/web-functions-configuration-deployment-package.html>`__ in the *AWS Lambda Developer Guide*.

**Example 9: To select the entry file with an environment variable**

The following ``deploy`` example sets ``AWS_LAMBDA_NODEJS_ENTRYPOINT`` so that
the runtime loads ``src/server.mjs`` directly. Do not use
``AWS_LAMBDA_NODEJS_ENTRYPOINT`` and ``--entry-point`` together. ::

    aws lambda-web deploy \
        --name my-app \
        --code ./app \
        --env AWS_LAMBDA_NODEJS_ENTRYPOINT=src/server.mjs

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-west-2.on.aws
    Console: https://us-west-2.console.aws.amazon.com/lambda/home#/web-functions/my-app

For more information, see `Environment variables <https://docs.aws.amazon.com/lambda/latest/dg/web-functions-revisions-env-vars.html>`__ in the *AWS Lambda Developer Guide*.

**Example 10: To create and deploy a Python starter application**

The following ``deploy`` example creates a Python starter in ``./my-api`` and
deploys it with the ``python3.15`` runtime. The starter exposes a WSGI
application object named ``app`` in ``main.py``. Lambda imports ``main:app``
and serves it, so there is no server to configure. ::

    aws lambda-web deploy \
        --name my-api \
        --hello-world \
        --runtime python

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-west-2.on.aws
    Console: https://us-west-2.console.aws.amazon.com/lambda/home#/web-functions/my-api

For more information, see `Creating a Lambda Web Function <https://docs.aws.amazon.com/lambda/latest/dg/web-functions-create.html>`__ in the *AWS Lambda Developer Guide*.

**Example 11: To deploy a Python application with its dependencies**

The following ``deploy`` example deploys a FastAPI application. Web Functions
run on ``arm64``, and ``deploy`` does not install dependencies, so install
them into the project directory for that platform first. Use ``uv`` or
``pip``. When you create a Web Function and omit ``--runtime``, the command
detects a Python project from files such as ``requirements.txt`` or
``main.py``. ::

    uv pip install -r requirements.txt --target . \
        --python-platform aarch64-manylinux_2_34 --python-version 3.15
    aws lambda-web deploy \
        --name my-api \
        --code . \
        --runtime python \
        --create

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-west-2.on.aws
    Console: https://us-west-2.console.aws.amazon.com/lambda/home#/web-functions/my-api

For more information, see `Web Function deployment package <https://docs.aws.amazon.com/lambda/latest/dg/web-functions-configuration-deployment-package.html>`__ in the *AWS Lambda Developer Guide*.

**Example 12: To deploy a Python application with a different entry point**

The following ``deploy`` example deploys a Django project whose application
object is ``application`` in ``mysite/asgi.py``. Specify the entry point as
``module:object``, as you would for uvicorn or gunicorn. The command sets
``AWS_LAMBDA_PYTHON_ENTRYPOINT`` on the revision. To require a specific
interface, set ``--env AWS_LAMBDA_PYTHON_ENTRYPOINT=wsgi:mysite.wsgi:application``
instead of ``--entry-point``. Add the endpoint domain to ``ALLOWED_HOSTS`` in
the Django settings, and to ``CSRF_TRUSTED_ORIGINS`` if forms post to the
application. Otherwise, Django returns HTTP 400 responses. ::

    aws lambda-web deploy \
        --name my-site \
        --code . \
        --entry-point mysite.asgi:application

Output::

    https://a1b2c3d4e5.x9y.lambda-web.us-west-2.on.aws
    Console: https://us-west-2.console.aws.amazon.com/lambda/home#/web-functions/my-site

For more information, see `Environment variables <https://docs.aws.amazon.com/lambda/latest/dg/web-functions-revisions-env-vars.html>`__ in the *AWS Lambda Developer Guide*.

These examples use ``us-west-2`` as the AWS Region for deployment. The command
selects the AWS Region from ``--region``, the ``AWS_DEFAULT_REGION`` environment
variable, or your AWS CLI configuration. You can use a different AWS Region.
Endpoint and console URLs reflect the AWS Region used for the deployment. A
``MultiRegion`` endpoint uses the global endpoint domain. The endpoint
identifiers are fictitious and do not identify live resources.
