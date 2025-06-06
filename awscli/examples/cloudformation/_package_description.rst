Packages the local artifacts (local paths) that your AWS CloudFormation
template references. The command uploads local artifacts, such as source code
for an AWS Lambda function or a Swagger file for an AWS API Gateway REST API,
to an S3 bucket. The command can also process local modules, which are
parameterized CloudFormation snippets that are merged into the parent template.
The command returns a copy of your template, replacing references to local
artifacts with the S3 location where the command uploaded the artifacts, or
replacing local and remote module references with the resources in the module.

Use this command to quickly process local artifacts that might be required by
your template. After you package your template's artifacts, run the ``deploy``
command to deploy the returned template.

This command can upload local artifacts referenced in the following places:


    - ``BodyS3Location`` property for the ``AWS::ApiGateway::RestApi`` resource
    - ``Code`` property for the ``AWS::Lambda::Function`` resource
    - ``Content`` property for the ``AWS::Lambda::LayerVersion`` resource
    - ``CodeUri`` property for the ``AWS::Serverless::Function`` resource
    - ``ContentUri`` property for the ``AWS::Serverless::LayerVersion`` resource
    - ``Location`` property for the ``AWS::Serverless::Application`` resource
    - ``DefinitionS3Location`` property for the ``AWS::AppSync::GraphQLSchema`` resource
    - ``RequestMappingTemplateS3Location`` property for the ``AWS::AppSync::Resolver`` resource
    - ``ResponseMappingTemplateS3Location`` property for the ``AWS::AppSync::Resolver`` resource
    - ``RequestMappingTemplateS3Location`` property for the ``AWS::AppSync::FunctionConfiguration`` resource
    - ``ResponseMappingTemplateS3Location`` property for the ``AWS::AppSync::FunctionConfiguration`` resource
    - ``DefinitionUri`` property for the ``AWS::Serverless::Api`` resource
    - ``Location`` parameter for the ``AWS::Include`` transform
    - ``SourceBundle`` property for the ``AWS::ElasticBeanstalk::ApplicationVersion`` resource
    - ``TemplateURL`` property for the ``AWS::CloudFormation::Stack`` resource
    - ``Command.ScriptLocation`` property for the ``AWS::Glue::Job`` resource
    - ``DefinitionS3Location`` property for the ``AWS::StepFunctions::StateMachine`` resource
    - ``DefinitionUri`` property for the ``AWS::Serverless::StateMachine`` resource
    - ``S3`` property for the ``AWS::CodeCommit::Repository`` resource


To specify a local artifact in your template, specify a path to a local file or
folder, as either an absolute or relative path. The relative path is a location
that is relative to your template's location. If the artifact is a module, the
path can be a local file or a remote URL starting with 'https'.

For example, if your AWS Lambda function source code is in the
``/home/user/code/lambdafunction/`` folder, specify
``CodeUri: /home/user/code/lambdafunction`` for the
``AWS::Serverless::Function`` resource. The command returns a template and replaces
the local path with the S3 location: ``CodeUri: s3://amzn-s3-demo-bucket/lambdafunction.zip``.

If you specify a file, the command directly uploads it to the S3 bucket. If you
specify a folder, the command zips the folder and then uploads the .zip file.
For most resources, if you don't specify a path, the command zips and uploads
the current working directory. The exception is ``AWS::ApiGateway::RestApi``;
if you don't specify a ``BodyS3Location``, this command will not upload an
artifact to S3.

Before the command uploads artifacts, it checks if the artifacts are already
present in the S3 bucket to prevent unnecessary uploads. The command uses MD5
checksums to compare files. If the values match, the command doesn't upload the
artifacts. Use the ``--force-upload flag`` to skip this check and always upload
the artifacts.

Modules can be included using the top level ``Modules`` section of the
template. Module confiruation has a ``Source`` attribute pointing to the module, 
either a local file or an ``https`` URL, a ``Properties`` attribute that 
corresponds to the module's parameters, and an ``Overrides`` attribute 
that can override module output.

This command also allows you to add a ``Constants`` section to the template
or to a local module. This section is a simple set of key-value pairs that 
can be used to reduce copy-paste within the template. Constants values are 
strings that can be referenced within ``Fn::Sub`` functions using the format 
``${Const::NAME}``, or objects that can be referenced with `Ref`.




