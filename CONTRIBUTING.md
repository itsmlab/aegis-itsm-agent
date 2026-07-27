# Contributing to ITSMLab

First off, thank you for considering contributing to ITSMLab! 🎉

## How to Contribute

### 1. Reporting Issues

- Check if the issue already exists in the GitHub Issues
- Use a clear, descriptive title
- Include steps to reproduce, expected behavior, and actual behavior
- Include system information (OS, Python version, Docker version)

### 2. Adding Patterns to the Knowledge Base

The knowledge base lives in [`ITSMLab_PATTERNS.md`](ITSMLab_PATTERNS.md). To add a new pattern:

1. Research a real incident from a public postmortem
2. Follow the existing format:
   - **Pattern ID**: `ITSMLab-NNN` (next sequential number)
   - **Title**: Clear, descriptive name
   - **Source**: Link to the original postmortem
   - **Symptoms**: Observable indicators
   - **Root Cause**: What actually happened
   - **Remediation**: Step-by-step fix script
3. Submit a Pull Request

### 3. Improving the Classifier

- Add more labeled tickets to `tickets_dataset.csv`
- Improve the hybrid classification algorithm
- Add new categories if needed

### 4. Code Contributions

- Fork the repository
- Create a feature branch
- Write tests for new functionality
- Ensure all existing tests pass
- Submit a Pull Request

## Development Setup

```bash
git clone https://github.com/laral5173/aegis-itsm-agent.git
cd aegis-itsm-agent
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

## Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public functions
- Keep functions focused and small

## Testing

```bash
# Run classifier tests
python test_classifier.py

# Run cross-validation
python cross_validation.py

# Run integration tests
python -m pytest tests/
```

## Pull Request Process

1. Update the README.md if needed
2. Update the ARCHITECTURE.md if architecture changes
3. Ensure all tests pass
4. Get at least one review
5. Squash commits before merging

Thank you for helping make ITSMLab better! 🚀
