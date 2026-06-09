

## Project AI Instructions

Always read `MEMORY.md` before performing analysis, planning, refactoring, or implementation tasks or making changes.
Follow the architectural conventions, dependency boundaries, and implementation notes documented there.

Update `MEMORY.md` whenever major architectural or workflow changes are introduced.

Review and analyze the entire project comprehensively, including:

* Source code
* File and directory structure
* Build tooling and package management
* Environment variables and runtime configuration
* Dependencies and dependency relationships
* Database schema, migrations, and ORM models
* APIs, integrations, and external services
* Frontend architecture
* Backend architecture
* Infrastructure and deployment configuration
* Authentication and authorization flows
* State management patterns
* Background jobs, queues, schedulers, and workers
* Testing architecture and coverage
* CI/CD workflows
* Logging, monitoring, and observability
* Feature flags and configuration systems

Your objective is to build a complete operational understanding of the application so future development can continue efficiently from a completely fresh AI context window with minimal rediscovery work.

After completing the analysis, update `MEMORY.md` in the project root directory.

`MEMORY.md` is intended to function as the persistent high-signal engineering memory layer for future AI-assisted development sessions.

The document must be:

* Extremely concise
* Highly information-dense
* Optimized for token efficiency
* Structured for rapid context restoration
* Written for senior software engineers only
* Free of fluff, tutorials, or beginner explanations

The goal is to maximize useful engineering context per token.

Primary Objectives

1. Compress the entire project into an efficient operational reference
2. Preserve architectural and implementation knowledge
3. Reduce onboarding time for future sessions
4. Prevent repeated rediscovery of project structure and conventions
5. Enable safe continuation of development from scratch contexts

Required Sections
s
1. Project Overview

* Application purpose
* Core business logic
* Primary workflows
* Current project maturity/status

2. Tech Stack

* Languages
* Frameworks
* Runtime versions
* Major dependencies
* Critical third-party services

3. Architecture Overview

Separate sections for:

* Frontend
* Backend
* Infrastructure
* Shared libraries/modules

Include:

* High-level execution flow
* System boundaries
* Communication patterns
* Architectural decisions
* Data flow

4. Directory Map

Concise explanation of:

* Important directories
* Critical files
* Entry points
* Bootstrap/init flow

Ignore trivial/generated folders.

5. Dependency Graph

Generate concise dependency mapping including:

* Core internal module relationships
* Service dependencies
* Frontend/backend coupling
* Circular dependency warnings
* Critical dependency chains

Prefer compact text diagrams or bullet hierarchies over verbose explanations.

6. Data Model Overview

* Core entities/models
* Relationships
* Ownership boundaries
* Important schema assumptions
* Migration strategy
* Data lifecycle concerns

7. API and Integration Summary

* Important endpoints
* Service contracts
* Internal APIs
* External integrations
* Webhooks/events
* Auth requirements

8. State Management

* Frontend state architecture
* Cache layers
* Persistence strategy
* Synchronization patterns
* Reactive/event systems

9. Auth & Security

* Authentication flow
* Authorization model
* Session/token handling
* Security-sensitive areas
* Permission boundaries
* Secrets/config handling

10. Build / Run / Deploy

Minimal but complete commands for:

* Install
* Local development
* Testing
* Linting
* Building
* Deploying
* Environment setup

Include only commands actually used.

11. Development Conventions

Document:

* Naming conventions
* Architectural patterns
* Code organization standards
* Reusable abstractions
* Error handling strategy
* Logging conventions
* Testing expectations

12. Critical Engineering Knowledge

Capture:

* Hidden assumptions
* Non-obvious implementation details
* Important historical decisions
* Fragile areas
* Performance bottlenecks
* Race conditions
* Concurrency concerns
* Scaling constraints
* Known bugs
* Technical debt

Focus heavily on information future sessions are likely to miss.

13. Dead Code & Cleanup Candidates

Identify:

* Unused files
* Unused services
* Dead components
* Legacy code paths
* Orphaned dependencies
* Duplicate abstractions
* Stale configs
* Deprecated patterns

Mark confidence level where uncertain.

14. Safe Modification Guide

Explain:

* Files that should be modified carefully
* High-risk systems
* Common failure points
* Required update sequences
* Migration precautions
* Testing requirements before merge/deploy
* Areas where regressions are likely

Optimize this section for preventing accidental breakage.

15. Current Work / Open Problems

Summarize:

* Incomplete features
* TODOs
* Known blockers
* Pending refactors
* Areas requiring future attention

16. AI Session Continuation Notes

Create a compact section specifically optimized for future AI context restoration.

Include:

* Most important project facts
* Current architectural assumptions
* Active development areas
* Immediate priorities
* Critical files to read first

This section should be maximally token-efficient.

Maintenance Requirements

`MEMORY.md` must be treated as a living document.

Whenever significant code changes occur:

* Update affected sections
* Remove stale information
* Keep summaries synchronized with the current architecture
* Preserve token efficiency
* Avoid uncontrolled document growth

Prefer replacing outdated information over appending endlessly.

Analysis Requirements

While reviewing the project:

* Identify actual runtime flows
* Trace important execution paths
* Infer architectural intent where necessary
* Detect inconsistencies between architecture and implementation
* Flag suspicious or fragile patterns
* Detect overengineering and unnecessary abstractions
* Detect tight coupling and scalability risks
* Detect missing tests around critical logic

Do not produce generic documentation.

Do not summarize obvious framework behavior.

Do not explain standard programming concepts.

Only preserve information that materially improves future engineering effectiveness.

The final result should feel like compressed operational memory for a senior engineer continuing development on a large unfamiliar codebase.