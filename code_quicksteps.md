# Code contribution quick steps

Thank you for your interest in contributing to the AWS Command Line Interface (AWS CLI)! This page provides the basic steps for making a contribution to the AWS CLI and linking to detailed information. 

The contribution process is tracked on a publicly visible [GitHub project board](https://github.com/orgs/aws/projects/21). Each lane of the board maps to a stage of the contribution process.

```{seealso} 
For more information on the full contribution process, see the [Detailed contribution process](contribution_process.md).
```

## Quick steps

1. [Create a GitHub issue](contribution_process.md#creating-a-github-issue) with the information necessary to make your contribution. Use the appropriate [GitHub issue template](https://github.com/aws/aws-cli/issues/new/choose).
2. [Maintainers review your issue and request details if needed.](contribution_process.md#github-issue-review-process) Once your issue fulfills all criteria, it is approved for contribution.
3. [Create or update your environment](setup.md).
4. Create a new feature branch in Git. For example Git commits and workflows, see [Git commits and workflows](git_workflows.md).
5. Implement your changes. Ensure you're following the [AWS CLI code guidelines](code_styleguide.md)
6. [Run tests to confirm your contributions pass](testing.md).
7. [Commit and push changes](git_workflows.md#create-a-feature-branch-for-contribution-and-submit-a-pull-request) to your GitHub fork.
8. [Create your pull request (PR)](contribution_process.md#submit-your-pull-request).
9. [Maintainers perform a preliminary review of your PR](contribution_process.md#github-pr-preliminary-review) to confirm the changes are as described in your opened GitHub issue.
10. Once confirmed, maintainers mark your issue and PR as `ready-for-review`.
11. [Maintainers perform a full review of the contribution](contribution_process.md#maintainer-review), providing feedback to the contributor as needed.
12. After the PR is approved by the maintainers, it is marked as `approved` and is then merged.