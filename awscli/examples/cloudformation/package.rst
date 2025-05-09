Following command exports a template named ``template.yaml`` by uploading local
artifacts to S3 bucket ``bucket-name`` and writes the exported template to
``packaged-template.yaml``::

    aws cloudformation package --template-file /path_to_template/template.yaml --s3-bucket bucket-name --output-template-file packaged-template.yaml


The following is an example of a template with a ``Modules`` section::

    Modules:
      Content:
        Source: ./module.yaml
        Properties:
          Name: foo
        Overrides:
          Bucket:
            Metadata:
              OverrideMe: def

An example module::
    
    Parameters:
      Name:
        Type: String
    Resources:
      Bucket:
        Type: AWS::S3::Bucket
        Metadata:
          OverrideMe: abc
        Properties:
          BucketName: !Ref Name
    Outputs:
      BucketArn: !GetAtt Bucket.Arn

Packaging the template with this module would result in the following output::

    Resources:
      ContentBucket:
        Type: AWS::S3::Bucket
        Metadata:
          OverrideMe: def
        Properties:
          BucketName: foo

The following is an example of adding constants to a template::

    Constants:
      foo: bar
      baz: ${Constant:foo}-xyz-${AWS::AccountId}

    Resources:
      Bucket:
        Type: AWS::S3::Bucket
        Properties:
          BucketName: !Sub ${Const::baz}

