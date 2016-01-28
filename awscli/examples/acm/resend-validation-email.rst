**To resend validation email for your ACM certificate request**

The following ``resend-validation-email`` command tells the Amazon certificate authority to send validation email to the appropriate addresses::

  aws acm resend-validation-email --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012 --domain www.example.com --validation-domain example.com
