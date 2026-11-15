"""Minimal, safe Markdown -> HTML converter and a Naver-friendly variant."""

import html
import re

_SAFE_SCHEMES = ("http://", "https://", "mailto:")
_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])")
_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
# Private-use characters cannot appear in normal text, so they are safe placeholder delimiters.
_OPEN, _CLOSE = "\ue000", "\ue001"
_SLOT = re.compile(f"{_OPEN}(\\d+){_CLOSE}")


def _safe_url(url):
    url = url.strip()
    if "\\" in url or url.startswith("//") or any(ord(c) < 32 for c in url):
        return "#"
    if url.lower().startswith(_SAFE_SCHEMES) or url.startswith(("/", "#")):
        return url
    return "#"


def _attr(url):
    # Markdown sources may already contain entities such as &amp;; decode once so they are not double-escaped.
    return html.escape(_safe_url(html.unescape(url)), quote=True)


def _emphasis(text):
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    return _ITALIC.sub(r"<em>\1</em>", text)


def inline(text):
    text = text.replace(_OPEN, "").replace(_CLOSE, "")
    slots = []

    def stash(fragment):
        slots.append(fragment)
        return f"{_OPEN}{len(slots) - 1}{_CLOSE}"

    text = _INLINE_CODE.sub(lambda m: stash(f"<code>{html.escape(m.group(1))}</code>"), text)
    text = _IMAGE.sub(lambda m: stash(f'<img src="{_attr(m.group(2))}" alt="{html.escape(m.group(1), quote=True)}">'), text)
    text = _LINK.sub(lambda m: stash(
        f'<a href="{_attr(m.group(2))}" rel="noopener noreferrer">{_emphasis(html.escape(m.group(1), quote=False))}</a>'), text)
    text = _emphasis(html.escape(text, quote=False))

    def restore(m):
        i = int(m.group(1))
        return slots[i] if i < len(slots) else ""
    return _SLOT.sub(restore, text)


def _table(lines):
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines]
    head, body = rows[0], rows[2:]
    out = ["<table>", "<thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead>", "<tbody>"]
    out += ["<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body]
    return out + ["</tbody>", "</table>"]


def markdown_to_html(markdown):
    lines = markdown.replace("\r\n", "\n").split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
        elif stripped.startswith("```"):
            block, i = [], i + 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(block))}</code></pre>")
        elif re.match(r"^#{1,6}\s", stripped):
            level = len(stripped) - len(stripped.lstrip("#"))
            out.append(f"<h{level}>{inline(stripped[level:].strip())}</h{level}>")
            i += 1
        elif re.fullmatch(r"([-*_])\1{2,}", stripped):
            out.append("<hr>")
            i += 1
        elif stripped.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(f"<blockquote><p>{inline(' '.join(quote))}</p></blockquote>")
        elif "|" in stripped and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:-]+\|[\s|:-]*$", lines[i + 1]):
            block = []
            while i < len(lines) and "|" in lines[i]:
                block.append(lines[i])
                i += 1
            out += _table(block)
        elif re.match(r"^([-*+]|\d+\.)\s", stripped):
            ordered = bool(re.match(r"^\d+\.", stripped))
            tag = "ol" if ordered else "ul"
            items = []
            while i < len(lines) and re.match(r"^\s*([-*+]|\d+\.)\s", lines[i]):
                items.append(re.sub(r"^\s*([-*+]|\d+\.)\s+", "", lines[i]))
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(it)}</li>" for it in items) + f"</{tag}>")
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not _block_start(lines, i):
                para.append(lines[i].strip())
                i += 1
            if not para:  # defensive: never loop without consuming a line
                para.append(lines[i].strip())
                i += 1
            out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)


_TABLE_SEP = re.compile(r"^\s*\|?[\s:-]+\|[\s|:-]*$")


def _block_start(lines, i):
    s = lines[i].strip()
    if re.match(r"^(#{1,6}\s|```|>|([-*+]|\d+\.)\s)", s) or re.fullmatch(r"([-*_])\1{2,}", s):
        return True
    return "|" in s and i + 1 < len(lines) and bool(_TABLE_SEP.match(lines[i + 1]))


def markdown_to_naver(markdown):
    """Naver editors drop most structure on paste: flatten headings to bold markers."""
    converted = markdown_to_html(markdown)
    converted = re.sub(r"<h1>(.*?)</h1>", "", converted)
    converted = re.sub(r"<h[2-6]>(.*?)</h[2-6]>", r"<p><strong>■ \1</strong></p>", converted)
    return converted
