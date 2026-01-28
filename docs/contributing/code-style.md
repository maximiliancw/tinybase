# Code Style Guide

This guide covers coding conventions and style guidelines for TinyBase.

## Python Style

### Formatting

We use **Ruff** for formatting and linting:

```bash
# Format code
ruff format .

# Check and fix linting issues
ruff check --fix .
```

Configuration in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
ignore = ["E501"]
```

### Imports

Organize imports in this order:

1. Standard library
1. Third-party packages
1. Local imports

```python
# Standard library
import os
from datetime import datetime
from typing import Any

# Third-party
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

# Local
from tinybase.auth import get_token_user
from tinybase.db.models import User
```

### Type Hints

Use type hints for all function signatures:

```python
# Good
def process_data(items: list[dict[str, Any]], limit: int = 100) -> list[str]:
    ...

# Bad
def process_data(items, limit=100):
    ...
```

Use `|` for union types (Python 3.10+):

```python
# Good
def get_user(user_id: str | None = None) -> User | None:
    ...

# Avoid (older style)
def get_user(user_id: Optional[str] = None) -> Optional[User]:
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def create_record(
    collection: Collection,
    data: dict[str, Any],
    owner_id: UUID | None = None,
) -> Record:
    """
    Create a new record in a collection.

    Args:
        collection: The collection to add the record to.
        data: Record data (will be validated against schema).
        owner_id: Optional owner user ID.

    Returns:
        The created Record object.

    Raises:
        ValidationError: If data doesn't match the collection schema.
    """
    ...
```

### Naming Conventions

| Type      | Convention            | Example             |
| --------- | --------------------- | ------------------- |
| Functions | `snake_case`          | `get_user_by_id`    |
| Variables | `snake_case`          | `user_count`        |
| Classes   | `PascalCase`          | `CollectionService` |
| Constants | `UPPER_SNAKE_CASE`    | `DEFAULT_PAGE_SIZE` |
| Private   | `_leading_underscore` | `_internal_cache`   |

### Classes

Keep classes focused and use dataclasses/Pydantic where appropriate:

```python
# For data structures, use Pydantic
class UserInput(BaseModel):
    email: str
    password: str


# For services with methods
class CollectionService:
    """Service class for collection operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_collections(self) -> list[Collection]:
        ...
```

### Error Handling

Be specific with exceptions:

```python
# Good - specific exception with message
if not collection:
    raise ValueError(f"Collection '{name}' not found")

# Bad - generic exception
if not collection:
    raise Exception("Error")
```

Use early returns:

```python
# Good
def get_user(user_id: UUID) -> User:
    user = session.get(User, user_id)
    if not user:
        raise ValueError("User not found")
    return user

# Avoid deep nesting
def get_user(user_id: UUID) -> User:
    user = session.get(User, user_id)
    if user:
        return user
    else:
        raise ValueError("User not found")
```

## FastAPI Conventions

### Route Handlers

Use dependency injection:

```python
@router.get("/users/{user_id}")
async def get_user(
    user_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    ...
```

### Response Models

Define explicit response models:

```python
class UserResponse(BaseModel):
    id: UUID
    email: str
    is_admin: bool
    created_at: datetime

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(...) -> UserResponse:
    ...
```

### Error Responses

Use HTTPException:

```python
from fastapi import HTTPException, status

if not user:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )
```

## Vue/TypeScript Style

### Component Structure

```vue
<script setup lang="ts">
// Imports
import { ref, computed, onMounted } from 'vue'
import { useStore } from '@/stores/main'

// Props
const props = defineProps<{
  title: string
  count?: number
}>()

// Emits
const emit = defineEmits<{
  (e: 'update', value: string): void
}>()

// State
const isLoading = ref(false)

// Computed
const displayTitle = computed(() => props.title.toUpperCase())

// Methods
function handleClick() {
  emit('update', 'clicked')
}

// Lifecycle
onMounted(() => {
  // ...
})
</script>

<template>
  <div class="component">
    <h1>{{ displayTitle }}</h1>
    <button @click="handleClick">Click me</button>
  </div>
</template>

<style scoped>
.component {
  /* styles */
}
</style>
```

### Naming

| Type        | Convention   | Example         |
| ----------- | ------------ | --------------- |
| Components  | `PascalCase` | `UserList.vue`  |
| Composables | `camelCase`  | `useAuth.ts`    |
| Stores      | `camelCase`  | `userStore.ts`  |
| Views       | `PascalCase` | `Dashboard.vue` |

## Git Conventions

### Branch Names

```
feature/add-user-validation
fix/issue-123-token-expiry
docs/update-api-reference
refactor/simplify-auth-flow
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**

- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Formatting (no code change)
- `refactor` - Code refactoring
- `test` - Adding tests
- `chore` - Maintenance tasks

**Examples:**

```
feat(functions): add support for async functions

Adds ability to register async functions that are properly
awaited during execution.

Closes #45
```

```
fix(auth): handle expired tokens gracefully

Previously, expired tokens caused a 500 error. Now they
return a proper 401 with "Token expired" message.
```

```
docs: update installation guide for Python 3.12
```

## File Organization

### Python Modules

```python
"""
Module docstring explaining purpose.

This module provides...
"""

# Imports (organized)
import ...

# Constants
DEFAULT_PAGE_SIZE = 100

# Types/Protocols (if any)
class MyProtocol(Protocol):
    ...

# Classes
class MyService:
    ...

# Functions
def helper_function():
    ...

# Module-level code (minimal)
if __name__ == "__main__":
    ...
```

### Test Files

```python
"""Tests for collection service."""

import pytest
from tinybase.collections.service import CollectionService


class TestCollectionService:
    """Test suite for CollectionService."""

    def test_list_collections_empty(self, session):
        """Test listing when no collections exist."""
        service = CollectionService(session)
        assert service.list_collections() == []

    def test_create_collection_success(self, session):
        """Test successful collection creation."""
        ...

    def test_create_collection_duplicate_name(self, session):
        """Test that duplicate names raise error."""
        ...
```

## Best Practices

### 1. Keep Functions Small

- Each function should do one thing
- If it's hard to name, it's doing too much
- Aim for < 20 lines

### 2. Avoid Magic Numbers

```python
# Bad
if len(password) < 8:
    ...

# Good
MIN_PASSWORD_LENGTH = 8
if len(password) < MIN_PASSWORD_LENGTH:
    ...
```

### 3. Use Descriptive Names

```python
# Bad
def proc(d):
    ...

# Good
def process_user_data(user_data: dict) -> ProcessedData:
    ...
```

### 4. Write Self-Documenting Code

```python
# Code explains what, comments explain why

# Bad - comment states the obvious
# Check if user is admin
if user.is_admin:
    ...

# Good - comment explains business logic
# Admins can see all users, regular users only see themselves
if user.is_admin:
    users = get_all_users()
else:
    users = [user]
```

## See Also

- [Development Setup](development.md)
- [Testing Guide](testing.md)
- [Architecture](architecture.md)
