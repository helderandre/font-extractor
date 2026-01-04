# Contributing to Font Extractor

First off, thank you for considering contributing to Font Extractor! It's people like you that make this tool better for everyone.

## Code of Conduct

This project and everyone participating in it is governed by respect and professionalism. Please be kind and constructive.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples** (URLs, font names, etc.)
- **Describe the behavior you observed** and what you expected
- **Include screenshots** if relevant
- **Include your environment** (OS, Python version, browser)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Use a clear and descriptive title**
- **Provide a detailed description** of the suggested enhancement
- **Explain why this enhancement would be useful**
- **List examples** of how it would work

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code, ensure it follows the existing style
3. Make sure your code lints and passes tests
4. Update documentation as needed
5. Write a clear commit message describing your changes

## Development Setup

```bash
# Clone your fork
git clone https://github.com/helderandre/font-extractor.git
cd font-extractor

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Style Guidelines

### Python Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Add comments for complex logic

### JavaScript Code Style

- Use modern ES6+ syntax
- Use `const` and `let`, not `var`
- Use meaningful variable names
- Add comments for complex logic
- Keep functions pure when possible

### CSS Style

- Use CSS custom properties for theming
- Follow BEM naming convention when applicable
- Keep selectors specific but not overly complex
- Add comments for complex styling

## Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally

Examples:
```
Add font subsetting feature
Fix WOFF2 conversion error
Update README with new examples
```

## Testing

If adding new features, please include tests:

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=main
```

## Questions?

Feel free to open an issue with your question or reach out to the maintainers.

Thank you for contributing! 🎉
