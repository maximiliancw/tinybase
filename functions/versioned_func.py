# /// script
# dependencies = ["tinybase-sdk"]
# ///

from tinybase_sdk import register


@register(name="versioned_func")
def versioned_func(client, payload):
    return {"result": "v1"}
