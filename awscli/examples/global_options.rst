``--debug`` (boolean)
  
  Turn on debug logging. The ``--debug`` option provides full Python logs. This includes additional ``stderr`` diagnostic information about the operation of the command that can be useful when troubleshooting why a command provides unexpected results.
  
``--endpoint-url`` (string)
  
  Specifies the URL to send the request to. For most commands, the AWS CLI automatically determines the URL based on the selected service and the specified AWS Region. However, some commands require that you specify an account-specific URL. You can also configure some AWS services to `host an endpoint directly within your private VPC <https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html#what-is-privatelink>`__, which might then need to be specified.
  
  For a list of the standard service endpoints available in each Region, see `AWS Regions and Endpoints <https://docs.aws.amazon.com/general/latest/gr/rande.html>`__ in the *Amazon Web Services General Reference*.
  
``--no-verify-ssl`` (boolean)
  
  By default, the AWS CLI uses SSL when communicating with AWS services. For each SSL connection, the AWS CLI will verify SSL certificates. This option overrides the default behavior of verifying SSL certificates.
  
  This option is not best practice. If you use ``--no-verify-ssl``, your traffic between your client and AWS services is no longer secured. This means your traffic is a security risk and vulnerable to man-in-the-middle exploits. If you're having issues with certificates, it's best to resolve those issues instead. For certificate troubleshooting steps, see `SSL certificate errors <https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-troubleshooting.html#tshoot-certificate-verify-failed>`__ in the *AWS CLI User Guide*.
  
``--no-paginate`` (boolean)
  
  Disable automatic pagination. For more information see `How to use the --no-paginate parameter <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-pagination.html#cli-usage-pagination-nopaginate>`__ in the *AWS CLI User Guide*.
  
``--output`` (string)
  
  Specifies the output format to use for this command. You can specify any of the following values:
  
  * **json:** The output is formatted as a `JSON <https://json.org/>`__ string.
  
  * **(AWS CLI V2 only) yaml:** The output is formatted as a `YAML <https://yaml.org/>`__ string.
  
  * **(AWS CLI V2 only) yaml-stream:** The output is streamed and formatted as a `YAML <https://yaml.org/>`__ string. Streaming allows for faster handling of large data types.
  
  * **text:** The output is formatted as multiple lines of tab-separated string values. This can be useful to pass the output to a text processor, like grep, sed, or awk.
  
  * **table:** The output is formatted as a table using the characters +|- to form the cell borders. It typically presents the information in a "human-friendly" format that is much easier to read than the others, but not as programmatically useful.  
  
  For more information see `Setting the AWS CLI output format <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-output-format.html>`__ in the *AWS CLI User Guide*.
  
``--query`` (string)
  
  The AWS CLI provides built-in JSON-based client-side filtering capabilities with the ``--query`` parameter. The ``--query`` parameter is a powerful tool you can use to customize the content and style of your output. The ``--query`` parameter takes the HTTP response that comes back from the server and filters the results before displaying them. Since the entire HTTP response is sent to the client before filtering, client-side filtering can be slower than server-side filtering for large data-sets. For more information on the ``--query`` parameter, see `Client-side filtering <https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-filter.html#cli-usage-filter-client-side>`__ in the *AWS CLI User Guide*.
  
``--profile`` (string)
  
  Use the specified profile from your ``config`` and ``credentials`` file. To set up additional named profiles, you can use the ``aws configure`` command with the ``--profile`` option. For more information see `Named profiles for the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html>`__ in the *AWS CLI User Guide*.
  
``--region`` (string)
  
  Overrides configuration and environment variable settings to the specified AWS Region to send this command's AWS request to. For a list of all of the Regions that you can specify, see `AWS Regions and Endpoints <https://docs.aws.amazon.com/general/latest/gr/rande.html>`__ in the *Amazon Web Services General Reference*.
  
``--version`` (string)
  
  Display the AWS CLI version number of your installed AWS CLI.
  
``--color`` (string)
  
  Specifies support for color output. Valid values are ``on``, ``off``, and ``auto``. The default value is auto.
  
``--no-sign-request`` (boolean)
  
  Do not sign requests. Credentials are not loaded if this argument is provided.
  
``--ca-bundle`` (string)
  
  Overrides the configuration and environment variable settings fo which certificate authority (CA) bundle to use when verifying SSL certificates.
  
``--cli-read-timeout`` (int)
  
  The maximum socket read time in seconds. If the value is set to 0, the socket read will be blocking and not timeout. The default value is 60 seconds.
  
``--cli-connect-timeout`` (int)
  
  The maximum socket connect time in seconds. If the value is set to 0, the socket connect will be blocking and not timeout. The default value is 60 seconds.
  