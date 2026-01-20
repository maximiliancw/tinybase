# /// script
# dependencies = ["tinybase-sdk"]
# ///

from tinybase_sdk import register

@register(name="idempotent_test")
def idempotent_test(client, payload):
    return {"result": "ok"}
