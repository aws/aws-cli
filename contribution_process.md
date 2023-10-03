# Detailed contribution process

Thank you for your interest in contributing to the AWS Command Line Interface (AWS CLI)! This document delves into the details of the contribution process for maintainers and contributors. The contribution process is tracked on a publicly visible [GitHub project board](https://github.com/orgs/aws/projects/21). Each lane of the board maps to a stage of the contribution process.

The goal with this guide is to give contributors confidence when making a contribution. We want to set expectations of maintainers and contributors to respect everyone’s time and effort. We do not expect that you need to read this document from beginning to end to make a contribution. Instead, it serves as an authoritative reference when you need it.

```{seealso} 
For quick steps, see [Code contribution quick steps](code_quicksteps.md).
```

The contribution process is composed of the following five stages:

1. **[Intake](#intake):** A contributor [creates a GitHub issue](https://github.com/aws/aws-cli/issues/new/choose) with the contribution information. Maintainers regularly review open GitHub issues and request details to assure it is an acceptable request.
2. **[Ready for Contribution](#ready-for-contribution):** Issues that garner enough community interest and have sufficient detail are moved to the ready to contribute stage for any user to implement via a GitHub pull request.
3. **[Implementation](#implementation):** When a user submits a pull request for an issue that is ready for contribution, it moves to the implementation stage. Maintainers then perform a preliminary review to confirm that a PR is implemented as described, and the issue is added to a queue for maintainer full review.
4. **[Ready for Review](#ready-for-review):** Maintainers select a maximum of four issues at a time for full review from the queue of ready to review issues. Issues are publicly prioritized for review based on their type (bug, documentation, and feature request, in that order) and age. New issues may be prioritized higher based on their potential impact.
5. **[Review](#maintainer-review):** Maintainers perform a full review of the contribution with the goal of merging the pull request. We work with the contributor to address any necessary changes. Once a pull request is completed to the satisfaction of the maintainers, it is approved and merged.

## Intake

The contribution process is initiated during intake by submitting a GitHub issue. The issue is then reviewed by the maintainers to assess a variety of factors.

### Creating a GitHub issue

 The intake process starts by [opening a GitHub issue](https://github.com/aws/aws-cli/issues/new/choose) on the AWS CLI repository using the appropriate template. 

```{important}
Before creating a GitHub issue, confirm there is no existing [issue](https://github.com/aws/aws-cli/issues) or [pull request](https://github.com/aws/aws-cli/pulls) for the contribution.
```

An issue must be opened prior to any pull request. The GitHub issue must capture the following information:

1. A description of the requested change.
2. Design discussions, including use cases, edge cases, and alternative solutions.
3. The number of users in the community that request the change. This is measured through GitHub `+1` reactions.

### GitHub issue review process

Maintainers regularly review open GitHub issues. Issues that are ready for community contribution are labeled with the `community` label and added to the **Ready to contribute** lane of the [project board](https://github.com/orgs/aws/projects/21).

The decision to label an issue as `contribution-ready` is up to the discretion of the maintainers. Depending on the issue type (bug or feature request) and area (code or documentation), the maintainers use a set of criteria to decide if the issue is ready for contribution. This includes the following:

1. The change is feasible for a community member to contribute. See below for more details.
2. The maintainers agree with the implementation plan, including any design discussions (e.g. public interface design, edge cases, and backwards compatibility concerns).
3. If this is a **feature request**, the issue should have at least 10 `+1` reactions to demonstrate impact beyond the requester. **Feature requests** that do not receive enough `+1` reactions with no activity for a year are considered stale and are closed.

If the criteria are not satisfied, the maintainers comment on what is missing and how the community can rectify them. All criteria must be met prior to making a contribution (PR) so that feedback during the PR review process focuses on the implementation of the agreed upon design.

After the review process is complete, a maintainer adds the GitHub issue to the **Contribution Ready** lane of the public [GitHub project board](https://github.com/orgs/aws/projects/21) and labels the issue with the `community` label. This stage indicates any user is welcome to initiate a contribution via a GitHub pull request.

```{attention}
Some changes are not open for community contribution. They may pose a security risk, be part of dynamically generated code, requires interaction with internal teams to implement, or requires knowledge of the codebase that is not well documented. These include, but are not limited to, the following:

1. Changes to build processes. Some of our build processes are available through GitHub and some are internal. We need to carefully test any potential changes to ensure they are compatible with our systems.
2. GitHub Actions. Changes to our actions need to be carefully reviewed for security purposes.
3. Changes to models. This includes waiters, paginators, and resources. These requests are cross-SDK and managed by service teams so that all SDKs can use them with uniform behavior.
4. Changes to configuration or credential files or processes. These changes can also affect the behavior in other SDKs and need coordination with internal teams.
```

## Ready for contribution

When an issue is ready for contribution you must make your changes using Git and submit a PR.

```{important}
Before making your contribution, complete [first time setup for your contribution environment](setup.md).
```

### Creating your contribution

1. Pull all updates from the original AWS CLI GitHub repository and create a new Git branch in your fork. For example Git commits and workflows, including first time setup, see [Git commits and workflows](git_workflows.md).
2. When implementing your changes, be sure to follow formatting guidelines as appropriate to your type of change:
    1. [AWS CLI code guidelines](code_styleguide.md)
    2. [AWS CLI code examples style guide](docs_styleguide.md)
3. Once all changes are complete, [run the AWS CLI tests](testing.md). Resolve any errors until all tests pass.
4. Once tests pass, [commit and push changes](git_workflows.md) to your GitHub fork. Be sure to follow [our Git commit message guidelines](git_workflows.md#commit-message-formatting).

### Submit your pull request

1. After [comitting and pushing your branch to your repository fork](git_workflows), a link to submit a pull request (PR) is provided in the Git output.
2. When you submit your PR, include the related GitHub issue in the description.
3. Automated tests run after you submit a PR. If any of the tests fail, you must resolve them until your updates pass all the tests. If you are having issues resolving the failed tests, engage a maintainer for help.
4. Once all tests are resolved, [rebase your commits](git_workflows#rebase-your-commits).

```{note}
If your PR is still a work in progress, you should open it as a [draft pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/changing-the-stage-of-a-pull-request). PRs with a **draft** status do not move to the next step in the process. When you’re ready for review, remove the **draft** status from your PR. If you need help, reach out to the community and maintainers while your pull request is in the **draft** status.
```    

## Implementation

A GitHub issue enters the implementation stage once a user submits a GitHub pull request. This stage indicates that a contribution has been submitted for the issue, but the maintainers have not committed to a full review of the contribution. The issue is moved to the “Implementation” lane of the [GitHub project board](https://github.com/orgs/aws/projects/21).

### GitHub PR preliminary review

After a PR is submitted, the maintainers inform you to expect a preliminary review to confirm the following:

1. Your changes are implemented in the manner described in the linked issue.
2. The pull request includes new passing tests and passes all existing tests.
3. The code works on all supported operating systems.
4. The code is documented, which may include inline documentation and user documentation.
5. A **CHANGELOG** entry is provided.

If the criteria are not satisfied, the maintainers comment on the issue what work is still required. If you have questions, refer to this guide or ask the maintainers to clarify. Once your changes are added, the maintainers follow up.

Once the preliminary review criteria is met, the tracking GitHub issue is labeled `ready-for-review` and added to a queue for maintainer review. 

### Stale requests and preliminary review prioritization

If you aren’t actively engaged in responding to comments from maintainers or making code changes for more than 30 days, the contribution is considered stale. A stale pull request is closed and the linked issue is marked as `contribution-ready`.

PRs submitted without a GitHub issue are not prioritized to move to the next stage. If these PRs are more than six months old, they are considered stale and are closed.


## Ready for review 

The AWS CLI maintainers select issues for full review from the `ready-for-review` queue on the [GitHub project board](https://github.com/orgs/aws/projects/21). Issues are prioritized based on the following in descending order of importance:

1. Bugs
2. Documentation changes
3. Feature requests
4. Older contributions are selected before more recent ones.

A maintainer selects the issue from the queue with the current highest priority. The prioritization of issues in the queue is reviewed on a regular cadence and is decided based on maintainer discretion.

## Maintainer review

Selecting a pull request for review moves the tracking GitHub issue to the `Review` lane on the [GitHub project board](https://github.com/orgs/aws/projects/21). Maintainers work with you to perform a full review of the contribution with the goal of merging your pull request. Having a PR selected for review does not guarantee a merge timeline. The maintainers review no more than four pull requests at a time. 

The criteria for merging a pull request may include the following:

1. The change is made in the correct place and fits in the existing architecture.
2. The change does not increase the maintainability in an unreasonable fashion.
3. There is sufficient documentation, both in the code and for end users.
4. The code is readable and follows best practices and conventions.
5. For documentation, the contribution has AWS CLI writer approval.

If a pull request is not ready to merge, the maintainers comment on the pull request with their feedback and questions for you to address. If changes are requested, You should make the changes within 15 days. If you do not respond within 15 days, the pull request is marked as stale and the contributor has 5 days to respond. If there is no response, the maintainers  close the pull request.

Once a pull request is completed to the satisfaction of the maintainers, it is approved and merged. The corresponding tracking issue is closed and labeled to acknowledge it as a community contribution.
