# Repository Guidelines

## Project Structure & Module Organization
This repository is currently an empty workspace. Keep the top level minimal and introduce code in predictable folders as the project grows:

- `src/` for application or library code
- `tests/` for automated tests that mirror `src/`
- `assets/` for static files such as images, sample media, or fixtures
- `scripts/` for repeatable development or release automation
- `docs/` for design notes or architecture decisions when needed

Mirror source and test paths where practical. Example: `src/player/queue.js` should have a corresponding test such as `tests/player/queue.test.js`.

## Build, Test, and Development Commands
No build, test, or lint tooling is configured yet. When adding a stack, expose a small set of standard commands and update this guide in the same change.

Examples:

- `npm run dev` or `make dev` to start local development
- `npm test` or `make test` to run the full test suite
- `npm run lint` or `make lint` to run static checks and formatting validation

Prefer checked-in scripts over one-off shell commands so other contributors can reproduce the workflow.

## Coding Style & Naming Conventions
Use clear, single-purpose modules and descriptive names. Keep filenames lowercase unless the language ecosystem expects otherwise; examples include `snake_case.py`, `kebab-case.ts`, and `PascalCase.jsx` for component files only.

Adopt the formatter and linter native to the chosen stack and commit their config with the code. Default text conventions for this repository are UTF-8, LF line endings, and no trailing whitespace.

## Testing Guidelines
Add automated tests with every non-trivial change. Keep tests deterministic, fast, and focused on behavior rather than implementation details. Use names such as `test_parser.py` or `parser.test.ts` based on the selected framework.

Prioritize coverage for business logic, parsing, and edge cases. If a change cannot be tested automatically, explain the manual verification steps in the pull request.

## Commit & Pull Request Guidelines
There is no Git history yet, so use short, imperative commit messages such as `Add initial movie parser` or `Create playback fixture data`.

Pull requests should include a brief summary, the reason for the change, test evidence, and screenshots or sample output when UI or media behavior changes. Link related issues and note any follow-up work explicitly.
