import json
import typing
from starlette.responses import Response


class PrettyJsonResponse(Response):
    media_type = "application/json"

    def render(self, content: typing.Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=4,
            separators=(", ", ": "),
            sort_keys=True,
            default=str,
        ).encode("utf-8")
