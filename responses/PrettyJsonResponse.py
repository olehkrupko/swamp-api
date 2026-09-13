"""Custom JSON response formatter for FastAPI.

Provides formatted JSON output with proper indentation and key sorting.
"""

import json
import typing
from starlette.responses import Response


class PrettyJsonResponse(Response):
    """Formatted JSON response with consistent indentation and sorting.

    Renders responses as pretty-printed JSON with 4-space indentation,
    sorted keys, and no NaN values. Ensures consistent output formatting.
    """

    media_type = "application/json"

    def render(self, content: typing.Any) -> bytes:
        """Render content as formatted JSON bytes.

        Args:
            content: Any JSON-serializable content.

        Returns:
            bytes: UTF-8 encoded JSON string.
        """
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=4,
            separators=(", ", ": "),
            sort_keys=True,
            default=str,
        ).encode("utf-8")
