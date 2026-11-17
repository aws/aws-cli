**To package local artifacts and export a template**

The following ``package`` example exports a template named ``template.json`` by uploading local
artifacts to the S3 bucket ``bucket-name`` and writes the exported template to
``packaged-template.json``. ::

    aws cloudformation package \
        --template-file /path_to_template/template.json \
        --s3-bucket bucket-name \
        --output-template-file packaged-template.json \
        --use-json

Output::

    Successfully packaged artifacts and wrote output template to file packaged-template.json.
    Execute the following command to deploy the packaged template
    aws cloudformation deploy --template-file /path_to_current_directory/packaged-template.json --stack-name <YOUR STACK NAME>

For more information, see `Upload local artifacts to an S3 bucket with the AWS CLI <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-cli-package.html>`__ in the *AWS CloudFormation User Guide*.
