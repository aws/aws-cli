# AWS CLI code example contribution quick steps

```{danger}
The AWS CLI repository is a **public** GitHub repository and submitting examples before a feature launch produces issues. You must be able to run the command from the public installation source.
```

Thank you for your interest in contributing code examples to the AWS Command Line Interface (AWS CLI)! This page provides the basic steps for making a contribution to AWS CLI code examples.

## Quick steps

1. [Create or update your environment](setup.md).
1. Create a new feature branch in Git. For example Git commits and workflows, see [Git commits and workflows](git_workflows.md).
1. Add your code example updates.
    * All AWS CLI command examples must adhere to the [AWS CLI code examples style guide](docs_styleguide.md) and be real working/tested examples.
    * The command examples are located in the repository's [`/aws-cli/awscli/examples`](https://github.com/aws/aws-cli/tree/develop/awscli/examples) folder. For details, see [Example file location](docs_styleguide.md#example-file-location).
1. [Run the `test_examples.py` test](testing.md#to-run-a-specific-aws-cli-test) to confirm your contributions pass.
    * If the `test_examples.py` test does not pass, fix the errors in your examples until they all pass.
1. [Commit and push changes](git_workflows.md#create-a-feature-branch-for-contribution-and-submit-a-pull-request) to your GitHub fork.
1. [Create your pull request (PR)](contribution_process.md#submit-your-pull-request).
1. [Maintainers perform a preliminary review of your PR](contribution_process.md#github-pr-preliminary-review) to confirm the changes are as described.
1. Once confirmed, maintainers mark your issue and PR as `ready-for-review`.
1. [A full review of the contribution is performed](contribution_process.md#maintainer-review) by both the maintainers and the AWS CLI documentation writer, providing feedback to the contributor as needed.
1. After the PR is approved by the maintainers and AWS CLI doc writer, it is marked as `approved` and is then merged.