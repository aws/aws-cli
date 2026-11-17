**To create a new application version**

The following ``create-application-version`` example creates a new version, "v1" of an application named "MyApp". ::

    aws elasticbeanstalk create-application-version \
        --application-name MyApp \
        --version-label v1 \
        --description MyAppv1 \
        --source-bundle S3Bucket="amzn-s3-demo-bucket",S3Key="sample.war" \
        --auto-create-application

The application will be created automatically if it does not already exist, due to the auto-create-application option. The source bundle is a .war file stored in an s3 bucket named "amzn-s3-demo-bucket" that contains the Apache Tomcat sample application.

Output::

    {
        "ApplicationVersion": {
            "ApplicationName": "MyApp",
            "VersionLabel": "v1",
            "Description": "MyAppv1",
            "DateCreated": "2015-02-03T23:01:25.412Z",
            "DateUpdated": "2015-02-03T23:01:25.412Z",
            "SourceBundle": {
                "S3Bucket": "amzn-s3-demo-bucket",
                "S3Key": "sample.war"
            }
        }
    }

For more information, see `Managing application versions <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/applications-versions.html>`__ in the *AWS Elastic Beanstalk Developer Guide*.
