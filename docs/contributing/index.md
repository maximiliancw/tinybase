# Contributing to TinyBase

Thank you for your interest in contributing to TinyBase! This guide will help you get started.

## Ways to Contribute

<div class="grid cards" markdown>

- :material-bug: **Report Bugs**

  Found a bug? Open an issue with details on how to reproduce it.

- :material-lightbulb: **Suggest Features**

  Have an idea? Open an issue to discuss new features.

- :material-code-tags: **Submit Code**

  Fix bugs, add features, or improve documentation.

- :material-file-document: **Improve Docs**

  Help make our documentation clearer and more complete.

</div>

## Getting Started

1. **Fork the repository** on GitHub
1. **Clone your fork** locally
1. **Set up development environment** ([Development Guide](development.md))
1. **Create a branch** for your changes
1. **Make your changes** with tests
1. **Submit a pull request**

## Development Guides

- [Development Setup](development.md) - Set up your environment
- [Architecture](architecture.md) - Understand the codebase
- [Code Style](code-style.md) - Coding conventions
- [Testing](testing.md) - Writing and running tests

## Quick Start

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/tinybase.git
cd tinybase

# Set up environment
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
pytest

# Start development server
tinybase serve --reload
```

## Code of Conduct

We are committed to providing a welcoming and inclusive experience for everyone. Please:

- Be respectful and considerate
- Use inclusive language
- Accept constructive criticism gracefully
- Focus on what's best for the community

## Pull Request Process

### Before Submitting

1. **Check existing issues** - Your change might already be in progress
1. **Open an issue first** - For significant changes, discuss before coding
1. **Update documentation** - If your change affects user-facing behavior
1. **Add tests** - Ensure your changes are tested
1. **Run the test suite** - Make sure nothing is broken

### Submitting

1. **Create a descriptive title** - Summarize the change
1. **Fill out the PR template** - Provide context and details
1. **Link related issues** - Use "Fixes #123" or "Closes #123"
1. **Keep changes focused** - One feature/fix per PR

### After Submitting

1. **Respond to reviews** - Address feedback promptly
1. **Keep the PR updated** - Rebase if needed
1. **Be patient** - Maintainers review when available

## Issue Guidelines

### Bug Reports

Include:

- TinyBase version
- Python version
- Operating system
- Steps to reproduce
- Expected vs. actual behavior
- Error messages/logs

### Feature Requests

Include:

- Problem description
- Proposed solution
- Alternative approaches considered
- Use cases

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

- **GitHub Discussions** - For general questions
- **GitHub Issues** - For bugs and features

Thank you for contributing to TinyBase! 🎉
