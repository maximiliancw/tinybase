# /// script
# dependencies = ["tinybase-sdk"]
# ///

from pydantic import BaseModel
from tinybase_sdk import register


class TestInput(BaseModel):
    value: str


class TestOutput(BaseModel):
    result: str


@register(name="api_test", description="API test function", auth="auth")
def api_test(client, payload: TestInput) -> TestOutput:
    return TestOutput(result=f"Got: {payload.value}")
