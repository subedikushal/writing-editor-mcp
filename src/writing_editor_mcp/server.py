"""Writing Editor MCP server. The client's model writes the prose; this server supplies guidance and review."""

from __future__ import annotations

import json
from typing import Annotated

from mcp import McpError, types
from mcp.server.fastmcp import Context, FastMCP
from pydantic import AfterValidator, Field, StringConstraints

from writing_editor_mcp import __version__
from writing_editor_mcp.guidance import (
    EDITOR,
    LATEX_GUIDANCE,
    PROFILES,
    SECTION_GUIDANCE,
    Genre,
    PaperSection,
    SourceFormat,
    length_guidance,
)
from writing_editor_mcp.review import audit, looks_like_latex


def nonblank(text: str) -> str:
    if not text.strip():
        raise ValueError("Provide a passage containing text.")
    return text


Draft = Annotated[
    str, StringConstraints(min_length=1, max_length=32_000), AfterValidator(nonblank)
]
Reader = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]
Sample = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=6_000)
]
Samples = Annotated[list[Sample], Field(max_length=5)]
Term = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Terms = Annotated[list[Term], Field(max_length=100)]
TargetWords = Annotated[int, Field(ge=20, le=8_000)]


def is_latex(source_format: SourceFormat | None, draft: str) -> bool:
    return (
        looks_like_latex(draft) if source_format is None else source_format == "latex"
    )


mcp = FastMCP(
    "Writing Editor",
    instructions="Call revise_writing to edit a passage. If it returns host_revision_needed, write the revision using its instructions and call review_revision before presenting it.",
)
# FastMCP has no version argument; report this package's version instead of the SDK's during initialization.
mcp._mcp_server.version = __version__


@mcp.tool()
def review_revision(
    draft: Draft,
    revision: Draft,
    samples: Samples | None = None,
    keep_terms: Terms | None = None,
    target_words: TargetWords | None = None,
    source_format: SourceFormat | None = None,
) -> dict:
    """Compare original and revised prose for changed markers, missing exact terms and eight-word overlap with optional style samples. Reports word counts, and flags a revision more than 10% from target_words when one is given. For LaTeX source (source_format="latex", or detected from LaTeX commands in the draft), flags percent signs that LaTeX would read as comments. Also lists changes to words that set a claim's strength (qualifier_changes) and style notes on the revision; neither affects the status. Returns review flags, not a factual certification."""
    return audit(
        draft,
        revision,
        samples or [],
        keep_terms or [],
        target_words,
        is_latex(source_format, draft),
    )


@mcp.tool()
async def revise_writing(
    draft: Draft,
    ctx: Context,
    genre: Genre = "explainer",
    audience: Reader = "an interested general reader",
    samples: Samples | None = None,
    keep_terms: Terms | None = None,
    paper_section: PaperSection | None = None,
    target_words: TargetWords | None = None,
    source_format: SourceFormat | None = None,
) -> dict:
    """Edit through the client's model or return a host editing brief. Use paper_section for a specific part of a research paper; it selects research guidance. Samples are optional style references. Pass target_words to request a length, and source_format="latex" for LaTeX source (detected automatically when the draft contains LaTeX commands)."""
    samples, keep = samples or [], keep_terms or []
    latex = is_latex(source_format, draft)
    if paper_section is not None:
        genre = "research"
        profile = {
            **PROFILES[genre],
            "paper_section": paper_section,
            "section_guidance": SECTION_GUIDANCE[paper_section],
        }
    else:
        profile = PROFILES[genre]
    brief = {
        "genre": genre,
        "reader": audience,
        "profile": profile,
        "draft": draft,
        "style_samples": samples,
        "required_exact_terms": keep,
        "source_format": "latex" if latex else (source_format or "unspecified"),
        "target_words": target_words,
    }
    requirements = (
        [length_guidance(target_words, len(draft.split()))] if target_words else []
    ) + ([LATEX_GUIDANCE] if latex else [])
    if requirements:
        brief["format_and_length"] = requirements
    fallback = {
        "status": "host_revision_needed",
        "editor_instructions": EDITOR,
        "brief": brief,
        "next_step": "The host assistant should write the revision now, then call review_revision with the same draft, samples, keep_terms, target_words and source_format. Fix any marker change, missing term or LaTeX issue it reports, and restore the draft's wording wherever an entry in qualifier_changes makes a claim stronger or weaker.",
    }
    if not ctx.session.check_client_capability(
        types.ClientCapabilities(sampling=types.SamplingCapability())
    ):
        return fallback
    message = types.SamplingMessage(
        role="user",
        content=types.TextContent(
            type="text", text=json.dumps(brief, ensure_ascii=False)
        ),
    )
    try:
        reply = await ctx.session.create_message(
            messages=[message],
            system_prompt=EDITOR,
            max_tokens=min(16000, max(1024, len(draft) + 256)),
            related_request_id=ctx.request_id,
        )
    except McpError as error:
        # A client declining a model call is a user decision. Never retry through another provider.
        return {"status": "sampling_unavailable", "detail": str(error.error.message)}
    if reply.stopReason == "maxTokens":
        return {
            "status": "incomplete",
            "detail": "The client stopped at its output limit. Request a shorter section.",
        }
    content = reply.content
    if not isinstance(content, types.TextContent) or not content.text.strip():
        return {
            "status": "incomplete",
            "detail": "The client did not return a text revision.",
        }
    revision = content.text
    if len(revision) > 32_000:
        return {
            "status": "incomplete",
            "detail": "The result exceeds the passage length limit. Request a shorter section.",
        }
    return {
        "status": "revised",
        "revision": revision,
        "review": audit(draft, revision, samples, keep, target_words, latex),
        "guidance_used": profile,
    }


def main() -> None:
    """Run the server over standard input/output."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
