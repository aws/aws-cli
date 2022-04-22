# Improvements to the AWS CLI Contribution Process

Proposal         | Metadata
---------------- | -------------
**Author**       | Kenneth Daily
**Status**       | Proposed
**Created**      | 28-March-2022

## Abstract

Community contributions for the AWS CLI are not frequently reviewed, resulting
in stale and incomplete contributions. This document proposes changes to the
contribution process to ensure that community contributed feature requests are
successfully added to the AWS CLI. The new process aims to regain the trust of
contributors who have not had successful contributions and demonstrates our
customer obsession through a renewed focus on the community.

## Background and Motivation

### Terminology

The following terms are used throughout this document:

- The *community* comprises the individuals who use the AWS CLI.
- A *user* is a member of the community who uses the AWS CLI. They may also
  interact with the AWS CLI GitHub repository by opening or commenting on
  issues.
* A *contribution* is a proposed change to the AWS CLI code base. This can be
  adding new functionality, fixing a bug, or improving documentation.
- A *contributor* is a user who makes a contribution to the AWS CLI via a pull
  request. Contributors are not able to merge pull requests.
- A *maintainer* is a user who maintains the AWS CLI GitHub repository. They are
  also a contributor and write core functionality. They triage and moderate
  GitHub issues, review pull requests, and accept contributions by merging pull
  requests.

### Current contribution process

The AWS CLI GitHub repository is available for any individual to report bugs,
make feature requests, and ask guidance questions through GitHub issues, as well
as open pull requests to propose code changes. There are currently roughly three
stages to manage contributions that are common to open source projects: intake,
implementation, and review.

#### Intake stage

GitHub issues are triaged regularly to determine that they are correctly
categorized and express a real and relevant problem or request. An answer is
provided as soon as possible to acknowledge or resolve the issue. Feature
requests are reviewed for general suitability and uniqueness. Users can vote for
features via "reactions" on the issue. 

#### Implementation stage

Users can open pull requests to propose changes that address bugs or feature
requests. There is no requirement to work on an existing feature request or to
discuss a contribution prior to opening a pull request. Occassionally guidance
is provided to the contributor to improve the proposed change.

#### Review stage

Pull requests are selected for review opportunistically when the maintainers
have decided that a change or feature should be incorporated. When a feature is
selected for review it is added to an internal queue. This queue manages the
prioritization of these features but is not visible to the community. 

Pull requests are subjected to automated tests and checks which provide
preliminary feedback. Once a pull request passes all automated tests and checks,
it requires review from a maintainer to proceed toward being merged.

Maintainers may also push changes directly to a contributor's pull request in
order to expedite completion or if the contributor is no longer engaged. In some
cases, the maintainers will open their own pull request if the proposed change
is not acceptable as is or they fail to find an existing pull request.

When the pull request is completed to the maintainers satisfaction, it is merged
in for the next release.

#### Documentation and tracking

The GitHub repository has a [contribution
guide](https://github.com/aws/aws-cli/blob/develop/CONTRIBUTING.md), standard to
many open source projects, to provide guidance on contributing code to the
project. The guide describes how to report an issue or feature request and
states the minimum requirements and suggestions for a code contribution. It
describes how to perform the basic tasks using Git, including retrieving and
building the development version.

### Problems with the current contribution process

The current contribution process is applied unevenly and inconsistently. The
lack of commitment to the process has led to an accumulation of community
feature requests and bug fixes. In turn, the AWS CLI community is dissatisfied
and frustrated because their voices, votes, and efforts do not have an impact.
Here, we describe some examples of deficiencies in the current process.

#### Community contributions are not frequently reviewed.

[86 community pull requests][open-prs-2021] were opened in 2021. Of these, 43
(50%) have been closed: [24 by merging][prs-closed-by-merging-2021] and 19 by
closing without merging. The pull requests that were reviewed and merged were
chosen opportunistically - they corresponded to work the team needed to
complete, like bumping versions, or were low risk, like documentation changes.
There is a willingness from the community to make improvements to the AWS CLI
through contributions, but their contributions are not reviewed. This
inconsistent approach frustrates contributors and results in missed
opportunities to support community efforts to improve AWS CLI.

#### Contributors do not have enough information on how their contributions can be accepted.

[34 pull requests][prs-no-maintainer-response] opened in 2021 do not have any
response from a maintainer. Of these, [27 pull
requests][prs-no-maintainer-response-open] (79%) are still open. The project
lacks documentation on the guidelines and requirements for making a contribution
as well as what types of contributions would be accepted. Furthermore, the
maintainers do not consistently provide acknowledgement, feedback, next steps,
or indications of when a review would occur. The result is contributors are
unaware if they are making a contribution correctly, what the next steps are,
and when it will be reviewed. Contributors are frustrated that their efforts are
not being acknowledged and do not know what to do to move forward.

#### Community contributions stall and are left incomplete.

There are [14 pull requests][open-pr-with-comment-from-maintainer] opened in
2021 that had a comment from a maintainer but remain open. These comments
include feedback that the contributor responded to and was not followed up on by
a maintainer. In some cases, approval was given for a contribution but never
merged. The maintainers do not consistently check on the status of existing pull
requests and the contribution process stalls. The loss of momentum of the
contribution process erodes trust with individual contributors, who feel
ignored, and the community at large, who see stale contributions.

### Goals

Based on the problems identified in the current process, the proposed
improvements for customer contributions should satisfy the following goals:

1. Maintainers should review community contributions regularly.
1. Contributors and maintainers should always be able to determine the current
   state of a contribution and what steps remain to drive the contribution to a
   resolution.
1. Maintainers should resolve in-flight contribution reviews before committing
   to any new reviews.

## Specification

<a name="figure-1"></a>

 ![Figure 1: Flowchart of contribution guide review
process.](assets/contribution-guide/contribution-guide-flowchart.png "Figure 1:
Flowchart of contribution guide review process.")

**Figure 1: Flowchart of contribution guide review process.**

We propose to formalize the existing intake, implementation, and review stages
to assure they are applied systematically and transparently. In addition, we
will augment the current process with new stages to clarify what issues are
available for contribution and what stage they are in. [Figure 1](#figure-1)
demonstrates how a request and contribution will proceed through the improved
process.

We will also publish an improved contributing guide to document the review
process, acceptance criteria, and expectations for communication. We will use
existing issue labeling in conjunction with a GitHub Project Board to provide
transparent status to the community to indicate what is available for
contribution and to track the progress of a contribution.

The following sections detail the proposed improvements to the existing process.

### Intake stage

A contribution is initiated by opening a GitHub issue. The GitHub issue captures
information necessary to make the contribution, such as:

1. A description of the requested change.
1. The number of users in the community that request the change, measured
   through GitHub :+1: reactions.
1. Design discussions, including use cases, edge cases, and alternative
   solutions.

Maintainers will regularly review open GitHub issues and label the ones that are
ready for community contribution. The decision to label an issue as ready for
community contribution is ultimately up to the discretion of the maintainers.
Depending on the issue type (bug or feature request) and area (code or
documentation), the maintainers will use a set of criteria to decide if the
issue is ready for contribution. This may include:

1. The change is feasible for a community member to contribute. See [the
   appendix](#changes-not-available-for-contribution) for details.
1. Feature requests should have at least 10 :+1: reactions. See the
   [rationale](#rationale-upvotes) for further discussion.
1. The maintainers agree with the implementation plan, including any design
   discussions (e.g., public interface design, edge cases, backwards
   compatibility concerns).

If the criteria are not satisfied, the maintainers should explicitly comment
what criteria are not satsified and how the community can satisfy them. All
discussions must be resolved prior to making a contribution so that feedback
during the review process focuses on the implementation of the agreed upon
design.

Issues that do not receive enough :+1: reactions and do not have any activty for
a year are considered stale. Without further interaction, they will be closed.

### Contribution-ready stage

A GitHub issue enters the contribution ready stage when a maintainer publicly
labels the issue ready for contribution. This stage indicates any user is
welcome to initiate a contribution via a GitHub pull request. All contribution
ready issues are listed publicly for the community to discover.

### Implementation stage

A GitHub issue enters the implementation stage once a user submits a GitHub pull
request implementing the change. This stage indicates that a contribution has
been submitted for the issue, but the maintainers have not committed to a full
review of the contribution. The maintainers will respond to let the contributor
know to expect a preliminary review to confirm:

1. It is implemented in the manner described in the issue.
1. It meets the criteria specified in the contribution guide. See the
   [appendix](#preliminary-review-criteria) for details.

If the criteria are not satisfied, the maintainers will comment on the issue
specifically indicating what work is still required. If the contributor has
questions, they should refer to the contributing guide documentation or ask the
maintainers to clarify. Once the contributor makes the required changes, the
maintainers will follow up.

If the contributor is no longer actively engaged by responding to comments from
maintainers or making code changes for more than 30 business days, the
contribution is stale. If not, the pull request will be closed and the
corresponding issue will be marked as ready for contribution.

Contributions made without a GitHub issue will not be prioritized to move to the
next stage. Pull requests that are not linked to an issue and are more than six
months old will be considered stale and closed. See the
[rationale](#rationale-require-issues) for further discussion.

### Ready for review stage

Once the preliminary review criteria from the implementation stage have been
met, the tracking GitHub issue is labeled as ready for review and added to a
queue for maintainer review. The maintainers will select issues for full review
from this queue. The issues will be prioritized for review publicly based on the
following criteria in descending order of importance:

1. Bugs, documentation changes, and feature requests will be prioritized in that
   order. See the [rationale](#rationale-priority-order) for further discussion.
1. Older contributions will be selected before more recent ones.

A maintainer must select the issue from the queue with the current highest
priority. The prioritization of issues in the queue is reviewed on a regular
cadence and is ultimately decided based on the maintainers' discretion. See the
[rationale](#rationale-reprioritize) for further discussion. 

### Review stage

Selecting a pull request for review will move the tracking GitHub issue to the
under review stage. In this stage, the maintainers will work with the
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
business days. If the contributor does not respond within 15 days, the pull
request will be marked as stale and the contributor will have 5 days to respond.
If there is no response, the maintainers will complete the pull request.

Once a pull request is completed to the satisfaction of the maintainers, it will
be approved and merged. The corresponding tracking issue will be closed closed
and labeled to acknowledge it as a community contribution.

## Contribution Kanban board

<a name="figure-2"></a>

 ![Figure 2: Example GitHub project for tracking contribution status.
process.](assets/contribution-guide/github-project-kanban-board.png "Figure 2:
Example GitHub project for tracking contribution status.")

**Figure 2: Example GitHub project for tracking contribution status.**

The contribution process will be implemented with a publicly visible [GitHub
project Kanban
board](https://docs.github.com/en/issues/trying-out-the-new-projects-experience/about-projects).
This project board will track GitHub issues from the contribution-ready stage
through completion by merging a pull request. Each lane of the project board
maps to a stage of the contribution process. New and existing GitHub labels and
GitHub issue events will be used to drive the movement of the issue between the
lanes of the GitHub project, which map to the stages of the contribution
process. GitHub issue labels will be used to move an issue to the next lane.

The contribution-ready lane is the entry point for users interested in making a
contribution. The ready for review lane is the prioritization queue, and issues
will be ordered in decreasing priority from top to bottom.

[Figure 2](#figure-2) demonstrates an example project with contributions in
various stages of completion. 


## Managing the existing backlog

As of 2021-12-15, there are 188 pull requests and 436 issues in the AWS CLI
GitHub repository. 43 pull requests and 87 issues have not been updated in more
than a year. 95 issues have ten or more upvotes. Many of these issues are
candidates for the ready to contribute or ready for review stages. We can use
them to backfill the proposed contribution process, providing the team with pull
requests to review and issues for the community to contribute.

We propose to manage existing pull requests in two phases. First, we will
determine if there is a corresponding tracking issue for each pull request and
[link them
together](https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue).
If no tracking issue exists, we will create one and link it to the pull request.
Then, we will apply the new specification to all open issues and identify the
current stage. We will prioritize the review of issues with a linked pull
request. After review, all pull requests will follow the process and timelines
defined in the specification.

## Rationale/FAQ

### Q. Why do we limit the number of issues in the review stage?

We do not want to discourage users from contributing or proposing changes, but
we need to acknowledge that the maintainers have limited bandwidth to give
feedback on implementation or design and review pull requests. The maintainers
have work that comes from outside of the GitHub repository that needs to be
prioritized along with user contributions. Controlling the volume of pull
request reviews and prioritizing completing the in flight reviews over new
reviews will result in a shorter time to merge and release a contributor's
change for a feature requested by the community. It will also reduce the amount
of context switching for the maintainers, allowing them to focus on giving high
quality feedback to users. As we use this framework to process existing feature
requests, we can revisit what the in flight limit should be.

<a name="rationale-require-issues"></a>

### Q. Why do we require issues to be opened instead of just pull requests?

Having a defined process for intake removes any ambiguity on how to initiate a
contribution by ensuring that all potential contributions start out as a GitHub
issue. We feel that having a more general discussion about the problem and
solutions will help reduce the overall effort into code review and provide
contributors with enough detail to make a sucessful contribution.

This requirement also solidifies the position that all pull requests that are
currently open are something we'd like to pull in. It removes any ambiguity for
a contributor about the status of the request.

Pull requests are often made for problems that only affect the contributor or a
small portion of the user base. An issue provides a mechanism to gather
quantitative feedback in the form of "upvotes" through GitHub reactions to
estimate the impact of the issue on the community.
 
We intend for issues to be a way to improve contributor confidence in both their
contributions and the overall process. Draft pull requests can be used to
demonstrate a potential implementation and get community feedback or interest
and may be converted to pull requests for review at a later time. If a user does
open a pull request without an issue, we will use the opportunity to educate
them about our process, and when necessary assist them in opening an issue.

<a name="rationale-reprioritize"></a>

### Q. Why would we re-prioritize contributions for review instead of taking them first in, first out?

We add issues to the queue in a way so that those with higher priority can be
resolved quickly and not blocked by larger proposed changes. However, there are
scenarios where a new issue may be added to the queue ahead of issues already
there. One example considers if the issues currently prioritized for review are
all large and complex. In this case, they risk blocking smaller and easier
changes. We may pull up the smaller issues to keep the queue moving. In another
case, a new feature may increase in urgency due to other API changes. Since the
main responsibility of the AWS CLI is to facilitate access to the AWS API, we
would re-prioritize a feature request to address that change.

<a name="rationale-upvotes"></a>

### Q. Why should there be a minimum number of upvotes or reactions for a feature request?

Feature requests carry a risk of adding new technical debt and increased
maintenance cost and should have a higher bar to be included.

The request should have user impact beyond the individual who proposed it. This
is difficult to measure objectively, but one proxy for impact can be the number
of upvote reactions on the issue. This is intended to prevent narrowly scoped
changes that only affect a single user. It also helps to limit the number of in
flight reviews that the maintainers need to be engaged on, as there is not an
unlimited amount of bandwidth to devote to this task.

At present, there are more than 95 open issues with at least 10 upvotes. We will
use the current upvote counts to review the backlog and identify issues that we
feel would be suited for community contributions. This process can then inform
us how to handle new issues that might be candidates for community contribution.

As part of the contribution guide, we will provide specific guidance on how to
upvote a feature so we can more accurately estimate user impact.

### Q. Do users need to request or acknowledge to work on an issue that is ready for contribution?

No. We do not want to require that users who want to contribute pre-register
their interest. Multiple contributions can result in a better implementation.
However, we should encourage users to comment on the issue that they are working
on it. This can be an opportunity for community collaboration instead of
duplicated effort.

<a name="rationale-priority-order"></a>

### Q. Why are issue types prioritized in the order of bug fixes, documentation, and feature requests?

The AWS CLI is a tool that is widely used in critical, production environments.
Reliability is essential and as such the priority is to address known bugs.
Feature requests need to be carefully assessed before taking on new potential
technical debt. Adding new features before known bugs are addressed would reduce
the reliability of the AWS CLI. Once a bug has been triaged and confirmed, it
should be made available for community contribution immediately without any
upvote requirements. High priority or high impact bugs will be handled by the
maintainers immediately without waiting for community contributions.

Most documentation changes are low risk and should move quickly through the
review process. Documentation changes also have a high reward potential,
measured by the number of users who would read the documentation to solve their
problem. In addition, there are also more maintainers available for validation
and review of documentation changes.


### Q. Why do maintainers complete the pull request in the review phase once it becomes stale?

The contribution process requires significant effort from both contributors and
maintainers. The process encourages high quality, desirable changes make it to
the review phase, and much of the work to vet the idea and an accompanying pull
request has already been completed. At this point, there is enough evidence and
effort that a proposed change should be accepted. In addition, the changes are
fresh in the maintainer's minds and will be easier to push to completion than
waiting for another review cycle. If the original contributor is unable to
finish the work, the maintainers should finish it so that the whole community
benefits.

### Q. Why do we need a GitHub project Kanban board?

Currently, all open issues in the AWS CLI GitHub repository are visible to the
community on the issues tab. We use GitHub issue labels to group related issues
together, The labels can be used to search and filter issues. However, there is
no way to for users to see the all of the stages of the contribution process or
how issues transition through it. A user would need to use predefined searches
to see which issues are in each stage and could only look at one stage at a
time. A Kanban board is a natural tool to display this information, and a GitHub
project board implements this using GitHub issues. Lanes in the Kanban board map
naturally to the stages of the contribution process.

## Appendix
### Changes not available for contribution

There are parts of the codebase that are not suitable for community
contributions. They may pose a security risk, be part of the code that is
dynamically generated, may require interaction with internal teams to implement,
or may require knowledge of the codebase that is not well documented. These
include (but are not limited to):

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

### Preliminary review criteria 

The maintainers will use a set of criteria to move a pull request from the
implementation to the ready for review stage, which may include (but are not
limited to):

1. The pull request must include passing tests.
1. The pull request must pass all existing tests.
1. The code must work on all supported operating systems.
1. The code must pass all linting and style checks.
1. The code must be documented, which may include inline documentation and user
   documentation.

### Future work

#### Proposals and request for comments

There are times when a change warrants an even more intentional and structured
process before introducing a change. For example, we [publicly posted a
proposal](https://github.com/aws/aws-cli/pull/6352) for a source distribution
for the AWS CLI v2. The proposal was open for comments and feedback that the
approach would solve the problems that exist. The proposed change was a major
deviation from how users currently install the AWS CLI, and we felt that
including users in the conversation for this change would result in better
decisions.

In this situation, we would use the same format as this document for a proposal
that would be opened for public comment and review. The document would be
incorporated into the codebase as an accepted proposal as a matter of record.

[contribution guide]:
    https://github.com/aws/aws-cli/blob/2069bf6735560da48440b743eb323488df5fa6c8/CONTRIBUTING.md
[open-pr-with-comment-from-maintainer]:
    https://github.com/search?q=is%3Apr+is%3Aopen+commenter%3Ajustindho+commenter%3Aelysahall+commenter%3AjoguSD+commenter%3Anateprewitt+commenter%3Azdutta+commenter%3Astobrien89+commenter%3Atim-finnigan+commenter%3Ajamesls+commenter%3Astealthycoin+commenter%3Avz10+commenter%3Akyleknap+commenter%3Akdaily+-author%3Ajustindho+-author%3Aelysahall+-author%3AjoguSD+-author%3Anateprewitt+-author%3Azdutta+-author%3Astobrien89+-author%3Atim-finnigan+-author%3Ajamesls+-author%3Astealthycoin+-author%3Avz10+-author%3Akyleknap+-author%3Akdaily+repo%3Aaws%2Faws-cli+created%3A2021-01-01..2021-12-31&type=Issues
[open-prs-2021]:
   https://github.com/search?q=is%3Apr+-author%3AConnorKirk+-author%3Asankalpbhandari+-author%3Amicahhausler+-author%3Ajustindho+-author%3Aelysahall+-author%3AjoguSD+-author%3Anateprewitt+-author%3Azdutta+-author%3Astobrien89+-author%3Atim-finnigan+-author%3Ajamesls+-author%3Astealthycoin+-author%3Avz10+-author%3Akyleknap+-author%3Akdaily+repo%3Aaws%2Faws-cli+created%3A2021-01-01..2021-12-31&type=Issues
[prs-closed-by-merging-2021]:
   https://github.com/search?q=is%3Apr+is%3Amerged+-author%3AConnorKirk+-author%3Asankalpbhandari+-author%3Amicahhausler+-author%3Ajustindho+-author%3Aelysahall+-author%3AjoguSD+-author%3Anateprewitt+-author%3Azdutta+-author%3Astobrien89+-author%3Atim-finnigan+-author%3Ajamesls+-author%3Astealthycoin+-author%3Avz10+-author%3Akyleknap+-author%3Akdaily+repo%3Aaws%2Faws-cli+created%3A2021-01-01..2021-12-31&type=Issues
[prs-no-maintainer-response]:
    https://github.com/search?q=is%3Apr+-commenter%3AJordonPhillips+-commenter%3Ajustindho+-commenter%3Aelysahall+-commenter%3AjoguSD+-commenter%3Anateprewitt+-commenter%3Azdutta+-commenter%3Astobrien89+-commenter%3Atim-finnigan+-commenter%3Ajamesls+-commenter%3Astealthycoin+-commenter%3Avz10+-commenter%3Akyleknap+-commenter%3Akdaily+-author%3AConnorKirk+-author%3Asankalpbhandari+-author%3Amicahhausler+-author%3Ajustindho+-author%3Aelysahall+-author%3AjoguSD+-author%3Anateprewitt+-author%3Azdutta+-author%3Astobrien89+-author%3Atim-finnigan+-author%3Ajamesls+-author%3Astealthycoin+-author%3Avz10+-author%3Akyleknap+-author%3Akdaily+repo%3Aaws%2Faws-cli+created%3A2021-01-01..2021-12-31&type=Issues
[prs-no-maintainer-response-open]:
    https://github.com/search?q=is%3Apr+is%3Aopen+-commenter%3AJordonPhillips+-commenter%3Ajustindho+-commenter%3Aelysahall+-commenter%3AjoguSD+-commenter%3Anateprewitt+-commenter%3Azdutta+-commenter%3Astobrien89+-commenter%3Atim-finnigan+-commenter%3Ajamesls+-commenter%3Astealthycoin+-commenter%3Avz10+-commenter%3Akyleknap+-commenter%3Akdaily+-author%3AConnorKirk+-author%3Asankalpbhandari+-author%3Amicahhausler+-author%3Ajustindho+-author%3Aelysahall+-author%3AjoguSD+-author%3Anateprewitt+-author%3Azdutta+-author%3Astobrien89+-author%3Atim-finnigan+-author%3Ajamesls+-author%3Astealthycoin+-author%3Avz10+-author%3Akyleknap+-author%3Akdaily+repo%3Aaws%2Faws-cli+created%3A2021-01-01..2021-12-31&type=Issues
