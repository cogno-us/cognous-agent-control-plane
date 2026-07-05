# Contributing

Thank you for your interest in contributing to Agent Control Plane.

## How to contribute

1. **Open an issue** before starting significant work so we can discuss the
   approach and avoid duplicated effort.
2. **Fork the repository** and create a feature branch from `main`.
3. **Write tests** for any new behaviour.  All tests must pass before
   a pull request is merged.
4. **Follow the code style**: the project uses standard Python typing,
   Pydantic models, and docstrings on all public classes and methods.
5. **Submit a pull request** with a clear description of the change and
   why it is needed.

## Development setup

```bash
pip install -e ".[dev]"
pytest
```

## Code style

- Python 3.11+
- Type annotations on all function signatures.
- Pydantic v2 models for data objects.
- Docstrings on all public classes and methods.
- No unnecessary abstractions or heavy dependencies.

## Commit messages

Use short, descriptive imperative-mood commit messages, e.g.:

```
Add write-authority policy rule
Fix fingerprint ordering for authority scopes
Update README quickstart example
```

## Licence

By contributing you agree that your contributions will be licensed under
the Apache-2.0 licence.
