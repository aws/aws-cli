# Contribution process

This is the complete definition of the AWS CLI contribution process. It
formalizes the steps that a contribution passes through from opening an issue
through merging a change with a pull request. It also defines the expectations
of the maintainers and contributors throughout the process.

The contribution process is composed of the following five stages:

1. **Intake** - A contribution is initiated by
   [opening a GitHub issue](https://github.com/aws/aws-cli/issues/new/choose) in
   the AWS CLI GitHub repository. The issue contains the information necessary
   to make the contribution. Maintainers will regularly review open GitHub
   issues and request details to assure it is an acceptable request.
2. **Ready for Contribution** - Issues that garner enough community interest and
   have sufficient detail are moved to the ready to contribute stage for any
   user to implement via a GitHub pull request.
3. **Implementation** - When a user submits a pull request for an issue that is
   ready for contribution, it moves to the implementation stage. The maintainers
   will perform a preliminary review to assert that it is implemented as
   described. Once the review criteria have been met, the issue is added to a
   queue for maintainer review.
4. **Ready for Review** - The maintainers will select a maximum of four issues at
   a time for full review from the queue of ready to review issues. The issues
   will be publicly prioritized for review based on their type (bug,
   documentation, and feature request, in that order) and age. New issues may be
   prioritized higher based on their potential impact. 
5. **Review** - The maintainers will perform a full review of the contribution
   with the goal of merging the pull request. They will work with the
   contributor to address any necessary changes. Once a pull request is
   completed to the satisfaction of the maintainers, it will be approved and
   merged.

The contribution process is tracked on a publicly visible
[GitHub project board](https://github.com/orgs/aws/projects/21). Each lane of
the board maps to a stage of the contribution process.

## Intake stage

A contribution is initiated by [opening a GitHub
issue](https://github.com/aws/aws-cli/issues/new/choose). An issue must be
opened prior to any pull request that implements a change to resolve the
request. The GitHub issue captures information necessary to make the
contribution, such as:

1. A description of the requested change.
1. The number of users in the community that request the change, measured
   through GitHub :+1: reactions.
1. Design discussions, including use cases, edge cases, and alternative
   solutions.

Maintainers regularly review open GitHub issues and label the ones that are
ready for community contribution with the `community` label and add them to the
"Ready to contribute" lane of the project board.

The decision to label an issue as ready for community contribution is ultimately
up to the discretion of the maintainers. Depending on the issue type (bug or
feature request) and area (code or documentation), the maintainers use a set of
criteria to decide if the issue is ready for contribution. This may include:

1. The change is feasible for a community member to contribute. See below for
   more details.
1. Feature requests should have at least 10 :+1: reactions to demonstrate impact
   beyond the requester.
1. The maintainers agree with the implementation plan, including any design
   discussions (e.g., public interface design, edge cases, backwards
   compatibility concerns).

If the criteria are not satisfied, the maintainers should explicitly comment
what criteria are not satsified and how the community can satisfy them. All
criteria must be met prior to making a contribution so that feedback
during the review process focuses on the implementation of the agreed upon
design.

Issues that do not receive enough :+1: reactions and do not have any activty for
a year are considered stale. Without further interaction, they will be closed.

Some changes are not open for community contribution. They may pose a security
risk, be part of the code that is dynamically generated, may require interaction
with internal teams to implement, or may require knowledge of the codebase that
is not well documented. These include (but are not limited to):

1. Changes to build processes. Some of our build processes are available through
   GitHub, but some are not. We need to carefully test any potential changes to
   be sure that they are compatible with all of our systems.
1. GitHub Actions. Changes to our actions need to be made and reviewed with
   extra scrutiny for security purposes.
1. Changes to models, including waiters, paginators, and resources. These
   requests are cross-SDK and managed by service teams so that all SDKs can use
   them with uniform behavior.
1. Changes to configuration or credential files or processes. These changes can
   also affect the behavior in other SDKs and must thus be made in coordination
   with internal teams.

## Contribution-ready stage

A GitHub issue enters the contribution ready stage when a maintainer adds the
issue to the "Ready to contribute" lane of the public [GitHub project
board](https://github.com/orgs/aws/projects/21) and labels the issue with the
`community` label. This stage indicates any user is welcome to initiate a
contribution via a GitHub pull request.

## Implementation stage

A GitHub issue enters the implementation stage once a user submits a GitHub pull
request implementing the change. This stage indicates that a contribution has
been submitted for the issue, but the maintainers have not committed to a full
review of the contribution. The issue will be moved to the "Implementation" lane
of the [GitHub project board](https://github.com/orgs/aws/projects/21). The
maintainers will respond to let the contributor know to expect a preliminary
review to confirm:

1. It is implemented in the manner described in the issue.
2. It meets the following criteria:
   - The pull request must include passing tests and must pass all existing tests.
   - The code must work on all supported operating systems.
   - The code must be documented, which may include inline documentation and
     user documentation.
   - A CHANGELOG entry must be provided.

If the criteria are not satisfied, the maintainers will comment on the issue
specifically indicating what work is still required. If the contributor has
questions, they should refer to this guide or ask the maintainers to clarify.
Once the contributor makes the required changes, the maintainers will follow up.

If the pull request is still a work in progress, contributors should open it as
a
[draft pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/changing-the-stage-of-a-pull-request).
A preliminary review will not be made on pull requests with a draft status. When
the contributor is ready for review, they should mark it as ready (remove draft
status). The contributor should feel free to ask questions or request help if
their pull request is in the draft status.

If the contributor is no longer actively engaged by responding to comments from
maintainers or making code changes for more than 30 days, the contribution is
stale. If not, the pull request will be closed and the corresponding issue will
be marked as ready for contribution.

Contributions made without a GitHub issue are not prioritized to move to the
next stage. Pull requests that are not linked to an issue and are more than six
months old are considered stale and will be closed.

## Ready for review stage

Once the preliminary review criteria from the implementation stage have been
met, the tracking GitHub issue is labeled as ready for review and added to a
queue for maintainer review. The maintainers select issues for full review from
this queue. The issues are prioritized for review publicly on the
[GitHub project board](https://github.com/orgs/aws/projects/21) based on the
following criteria in descending order of importance:

1. Bugs, documentation changes, and feature requests are prioritized in that
   order.
1. Older contributions are selected before more recent ones.

A maintainer must select the issue from the queue with the current highest
priority. The prioritization of issues in the queue is reviewed on a regular
cadence and is ultimately decided based on the maintainers' discretion.

## Review stage

Selecting a pull request for review moves the tracking GitHub issue to the
Review lane on the project board. In this stage, the maintainers work with the
contributor to perform a full review of the contribution with the goal of
merging the pull request. Having a pull request selected for review does not
guarantee how long it will be until it is merged. The maintainers will review no
more than four pull requests at a time. The criteria for merging a pull request
may include:

1. The change is made in the right place and fits in the existing architecture.
1. The change does not increase the maintainability in an unreasonable fashion.
1. There is sufficient documentation, both in the code and for end users.
1. The code is readable and follows best practices and conventions.

If a pull request is not ready to merge, the maintainers will comment on the
pull request with their feedback and questions for the contributor to address.
If changes are requested, the contributor should make the changes within 15
days. If the contributor does not respond within 15 days, the pull request will
be marked as stale and the contributor has 5 days to respond. If there is no
response, the maintainers will complete the pull request.

Once a pull request is completed to the satisfaction of the maintainers, it will
be approved and merged. The corresponding tracking issue will be closed and
labeled to acknowledge it as a community contribution.
