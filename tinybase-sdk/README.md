# TinyBase SDK

SDK for writing TinyBase serverless functions with isolated dependencies.

## Installation

```bash
pip install tinybase-sdk
```

Or in your function's inline dependencies:

```python
# /// script
# dependencies = ["tinybase-sdk"]
# ///
```

## Usage

```python
# /// script
# dependencies = ["tinybase-sdk"]
# ///

from tinybase_sdk import function, run
from tinybase_sdk.client import Client

@function(name="hello", description="Say hello", auth="public")
def hello(client: Client, name: str) -> dict[str, str]:
    return {"message": f"Hello, {name}!"}

if __name__ == "__main__":
    run()
```

## Documentation

See the [TinyBase Functions Guide](https://maximiliancw.github.io/TinyBase/guide/functions/) for complete documentation.
