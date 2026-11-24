# Writing Editor MCP

<!-- mcp-name: io.github.subedikushal/writing-editor-mcp -->

An MCP server that helps your AI assistant edit research papers, explanations and technical documentation.

You give the assistant a draft. The server tells the assistant how to edit it, and then checks the edited version against your original. The check catches numbers, citations, links and required terms that went missing or changed.

- No API key. Your assistant's own model does the writing.
- Nothing leaves your machine through this server, and it stores nothing.

## Install

You need [uv](https://docs.astral.sh/uv/getting-started/installation/). The command `uvx writing-editor-mcp` downloads and starts the server.

**Codex**

```sh
codex mcp add writing-editor -- uvx writing-editor-mcp
```

**Claude Code**

```sh
claude mcp add writing-editor -- uvx writing-editor-mcp
```

**Claude Desktop, Cursor, VS Code and other apps with a JSON config**

```json
{
  "mcpServers": {
    "writing-editor": {
      "command": "uvx",
      "args": ["writing-editor-mcp"]
    }
  }
}
```

VS Code uses `servers` instead of `mcpServers`. If the app can't find `uvx`, replace `"uvx"` with the full path that `which uvx` prints.

Restart the app or start a new chat after adding the server.

## Use it

Ask your assistant in plain words. For example:

> Use writing-editor to revise this results paragraph for software engineering researchers. Keep "median" and "95%" exactly as written.
>
> [paste your paragraph]

The assistant edits the paragraph and runs the check. It keeps how strongly each claim is stated, and when your draft announces parts (for example "three ways"), it keeps naming each part where its results appear. Read the result yourself before using it. The check finds mechanical problems, not changes in meaning.

When the draft is missing something, the edited text contains a note for you instead of a made-up fact:

- `[TODO: …]` a missing fact or definition
- `[CITE: …]` a claim that needs a citation
- `[CHECK: …]` a number or claim that looks inconsistent

## Tools

### `revise_writing`

Edits a draft.

| Option | What it does |
| --- | --- |
| `draft` | The text to edit. Required. Up to 32,000 characters. |
| `genre` | `research`, `explainer` (default) or `documentation`. |
| `audience` | Who will read it, for example "first-year PhD students". |
| `paper_section` | For one part of a paper: `title`, `abstract`, `introduction`, `related_work`, `method`, `evaluation`, `results`, `discussion`, `limitations`, `conclusion` or `caption`. Each has its own rules. For example, `results` leads with the finding, and `abstract` becomes one paragraph with no citations. |
| `keep_terms` | Words or phrases that must stay exactly as written. |
| `samples` | Up to 5 examples of writing you like, up to 6,000 characters each. The edit borrows their structure, not their sentences. |
| `target_words` | A length to aim for, within 10%. |
| `source_format` | `plain`, `markdown` or `latex`. LaTeX is detected automatically. |

Most assistants, including Codex and Claude, get back editing instructions (`host_revision_needed`) and write the new version themselves. Apps that let a server ask their model to write (called MCP sampling) get back the finished text and its check in one step.

### `review_revision`

Compares an original and an edited version. It takes `draft`, `revision` (the edited text), and the same `samples`, `keep_terms`, `target_words` and `source_format` you gave `revise_writing`.

It reports:

- numbers, units, links, citations, quotations, code and LaTeX references that changed or disappeared
- any `keep_terms` that are missing
- eight or more words copied in a row from your `samples`
- word counts, and whether the text is within 10% of `target_words`
- in LaTeX, a `%` after a number that LaTeX would treat as a comment
- `qualifier_changes`: words that set how strong a claim is, such as "often", "most", "could", "only", "not" or "full", that were dropped or added. "Often" becoming "could" makes a claim weaker; adding "full" makes it stronger. Swapping "every" for "each" is not listed.
- style notes: wording that readers of scientific text stumble over, such as "respectively", "in order to", "utilize", a non-statistical "significant", or a sentence that starts with a numeral

The status is `no_mechanical_flags` or `review_flags`. Qualifier changes and style notes never change the status, because many are fine edits, so read each one. A flagged item can be a correct edit, and a clean result doesn't prove the meaning is unchanged.

## Run from a copy of the code

```sh
git clone https://github.com/subedikushal/writing-editor-mcp
codex mcp add writing-editor -- uv --directory /full/path/to/writing-editor-mcp run writing-editor-mcp
```

## License

MIT