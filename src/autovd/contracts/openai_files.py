"""ChatGPT file objects passed through the OpenAI MCP file-parameter extension."""

from pydantic import BaseModel, ConfigDict, Field


class OpenAIFile(BaseModel):
    """Runtime file value ChatGPT passes to a declared MCP file parameter."""

    model_config = ConfigDict(extra="forbid")

    download_url: str = Field(min_length=1)
    file_id: str = Field(min_length=1)
    mime_type: str | None = None
    file_name: str | None = None
