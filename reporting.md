# Reporting bugs

This topic covers reporting bugs in the AWS Command Line Interface (AWS CLI). If you’d like to make a feature request, follow the **Intake** section in the [Contribution process](contribution_process.md#intake). 

To report a bug, perform the following steps:

1. Perform initial troubleshooting to confirm this is not a support issue. If this is an error, do not open a GitHub issue, instead [request support](support.md).
2. Before reporting a bug, check to see if there's an existing open [issue](https://github.com/aws/aws-cli/issues) or [pull request](https://github.com/aws/aws-cli/pulls) for the bug.
3. If there isn't an existing issue, [file a new GitHub issue](https://github.com/aws/aws-cli/issues/new/choose). When creating a new issue, use one of the suggested issue  templates as issues may require different information. In general, the ideal bug report includes:
    1. A description of the problem.
    2. Provide a [minimal reproducible example](https://stackoverflow.com/help/minimal-reproducible-example) of your issue. This includes the specific AWS CLI commands you are running and the debug logs for these commands when appending the `--debug` option to each command. 
    3. Be sure to remove any sensitive information from your command and the debug logs.
    4. The AWS CLI developer needs to be able to reproduce the issue you are seeing, so reduce your issue to the smallest possible set of steps that demonstrate the issue. This leads to a quicker resolution of your issue.
    5. The AWS CLI version you are using `aws --version`.