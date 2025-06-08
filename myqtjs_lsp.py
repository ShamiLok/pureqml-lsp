import os
import json
from lsprotocol.types import (
    CompletionParams,
    CompletionItem,
    CompletionItemKind,
    InsertTextFormat,
    HoverParams,
    Hover,
    MarkupContent,
    MarkupKind,
    DidOpenTextDocumentParams,
    DidChangeTextDocumentParams,
    TextDocumentSyncKind,
    InitializeParams,
)
from pygls.server import LanguageServer

# Define server
class MyQLServer(LanguageServer):
    def __init__(self):
        super().__init__(name="myqtjs-lsp", version="0.1")
        # Load completion items from JSON
        path = os.path.join(os.path.dirname(__file__), "completions.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.completion_items = []
        for item in data:
            self.completion_items.append(
                CompletionItem(
                    label=item["label"],
                    kind=CompletionItemKind(item.get("kind", CompletionItemKind.Text)),
                    insert_text_format=InsertTextFormat(item.get("insertTextFormat", InsertTextFormat.PlainText)),
                    insert_text=item.get("insertText", item["label"]),
                    documentation=item.get("documentation", "")
                )
            )

server = MyQLServer()

# Ensure client sends full document on open and change
@server.feature("initialize")
def on_init(ls: LanguageServer, params: InitializeParams):
    ls.server_capabilities.text_document_sync = TextDocumentSyncKind.Full
    return ls.server_capabilities

@server.feature("textDocument/didOpen")
def did_open(ls: LanguageServer, params: DidOpenTextDocumentParams):
    # No-op: ensures document is stored in workspace
    pass

@server.feature("textDocument/didChange")
def did_change(ls: LanguageServer, params: DidChangeTextDocumentParams):
    # No-op: ensure workspace document is updated
    pass

@server.feature("textDocument/completion")
def completions(ls: MyQLServer, params: CompletionParams):
    ls.show_message_log(f"[myql] completion at {params.position.line}:{params.position.character}")
    # Get document text
    uri = params.text_document.uri
    doc = ls.workspace.get_document(uri)
    lines = doc.source.splitlines()
    line = params.position.line
    ch = params.position.character

    # Determine prefix (last token before cursor)
    prefix = ""
    if line < len(lines):
        fragment = lines[line][:ch]
        if fragment.strip():
            prefix = fragment.split()[-1]

    low = prefix.lower()
    # Filter completion items
    matches = [item for item in ls.completion_items if item.label.lower().startswith(low)]
    ls.show_message_log(f"Prefix='{prefix}', found {len(matches)} matches")
    return matches

@server.feature("textDocument/hover")
def hover(ls: MyQLServer, params: HoverParams):
    uri = params.text_document.uri
    doc = ls.workspace.get_document(uri)
    line_text = doc.source.splitlines()[params.position.line]

    # Find word under cursor
    import re
    pattern = r"\b\w+\b"
    word = ""
    for m in re.finditer(pattern, line_text):
        start, end = m.span()
        if start <= params.position.character <= end:
            word = m.group(0)
            break

    # Lookup documentation
    for item in ls.completion_items:
        if item.label == word:
            return Hover(contents=MarkupContent(kind=MarkupKind.Markdown,
                                               value=item.documentation))
    return None

if __name__ == '__main__':
    server.start_io()
