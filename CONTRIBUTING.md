# Contributing to AEGIS

First off, thank you for considering contributing to AEGIS! 🎉

This project is open source under the MIT License, and we welcome contributions of all kinds — bug fixes, new features, documentation improvements, and knowledge base additions.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
  - [Report a Bug](#report-a-bug)
  - [Suggest a Feature](#suggest-a-feature)
  - [Submit Code Changes](#submit-code-changes)
- [Development Setup](#development-setup)
- [Coding Guidelines](#coding-guidelines)
- [Adding Incident Patterns](#adding-incident-patterns)
- [Adding Training Tickets](#adding-training-tickets)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/aegis-itsm-agent.git
   cd aegis-itsm-agent
   ```
3. Set up the development environment (see [Development Setup](#development-setup))
4. Create a branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## How to Contribute

### Report a Bug

Open an issue on GitHub with:

- A clear, descriptive title
- Steps to reproduce the bug
- Expected vs. actual behavior
- Environment details (OS, Python version, dependencies)
- Logs or error messages, if applicable

### Suggest a Feature

Open an issue with:

- A clear description of the problem you're trying to solve
- How you envision the feature working
- Any alternatives you've considered
- Why this would benefit the project

### Submit Code Changes

1. Ensure your code follows the [coding guidelines](#coding-guidelines)
2. Write or update tests as needed
3. Run existing tests to make sure nothing breaks
4. Update documentation if your changes affect the API or behavior
5. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git

### Local Setup

```bash
# Clone and enter the repo
git clone https://github.com/laral5173/aegis-itsm-agent.git
cd aegis-itsm-agent

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env with your API keys
```

### Running Tests

```bash
# Run classifier accuracy tests
python test_classifier.py

# Run cross-validation
python cross_validation.py

# Run integration module import verification
python test_integration.py
```

### Running the Server

```bash
# Start the FastAPI server
uvicorn app.main:app --reload
```

The server will start at http://localhost:8000. Open http://localhost:8000/docs for the interactive API documentation.

## Coding Guidelines

### Python Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for code style
- Use type hints for all function signatures
- Write docstrings for all public functions, classes, and modules
- Keep functions focused and single-purpose
- Maximum line length: 100 characters

### Naming Conventions

- `snake_case` for functions, methods, and variables
- `PascalCase` for classes
- `UPPER_CASE` for constants
- Descriptive names over abbreviations

### Project Structure

- New features should follow the existing modular structure
- Business logic goes in `app/services/`
- API endpoints go in `app/routers/`
- LLM providers go in `app/llm/`
- Standalone scripts stay in the root directory

### Error Handling

- Use specific exception types
- Log errors with appropriate context
- Return meaningful error messages in API responses
- Don't swallow exceptions without logging

## Adding Incident Patterns

The knowledge base lives in [`AEGIS_PATTERNS.md`](AEGIS_PATTERNS.md). To add a new pattern:

1. Research a real incident from a public postmortem
2. Follow the existing format:
   - **Pattern ID**: `AEGIS-NNN` (next sequential number)
   - **Title**: Clear, descriptive name
   - **Source**: Company and year
   - **Priority**: HIGH, MEDIUM, or LOW
   - **Symptoms**: Observable signs of the incident
   - **Root Cause**: Technical explanation of what happened
   - **Diagnosis**: How to identify this pattern
   - **Remediation**: Step-by-step resolution script
3. Submit a pull request with the addition

## Adding Training Tickets

The training dataset is in [`tickets_dataset.csv`](tickets_dataset.csv). To add tickets:

1. Each row represents one ticket with columns: `ticket`, `category`, `resolution`
2. Categories must be one of: ACCESS, API, DATABASE, HOWTO, LICENSE, NETWORK, PERFORMANCE, SECURITY
3. Tickets should be realistic IT support scenarios
4. Resolutions should be actionable and specific
5. After adding tickets, re-run cross-validation to verify classifier performance

## Pull Request Process

1. **Create a branch** from `main` for your changes
2. **Make your changes** following the coding guidelines
3. **Test your changes** — run existing tests and add new ones if needed
4. **Update documentation** if your changes affect the API, configuration, or usage
5. **Submit a pull request** with:
   - A clear title and description
   - Reference to any related issues
   - Screenshots or logs for UI/behavior changes
6. **Respond to feedback** — maintainers may request changes
7. **Merge** — once approved, a maintainer will merge your PR

### PR Checklist

Before submitting, ensure:

- [ ] Code follows coding guidelines
- [ ] Tests pass (`python test_classifier.py`)
- [ ] New tests added for new functionality
- [ ] Documentation updated (README, docstrings, etc.)
- [ ] No sensitive data (API keys, passwords) in code
- [ ] Branch is up to date with `main`

## Questions?

Open an issue or reach out to the maintainer:

- **Leopoldo Lara** — [GitHub](https://github.com/laral5173)

---

Thank you for helping make AEGIS better! 🚀
