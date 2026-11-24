import ast
import io
import sys
import tokenize
from pathlib import Path

FIX = (
    "Delete it. An agent reads a comment as a hard rule, long after the reason for it has gone. "
    "Say it with a name or a test, or in the docs when a person needs to know."
)
SCRIPT = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}
HASH = {".yml", ".yaml", ".sh", ".toml"}
HASH_NAMES = {".gitignore", ".gitattributes"}
SKIPPED = {".git", "node_modules", "__pycache__"}
REGEX_AFTER = set("(,=:[!&|?{};+-*%<>~^")
REGEX_AFTER_WORD = {"return", "typeof", "case", "in", "of", "delete", "void", "throw", "new", "else", "do", "yield", "await"}


def offsets(text):
    starts = [0]
    for line in text.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    return starts


def python_comments(text):
    starts = offsets(text)
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT and not (token.start == (1, 0) and token.string.startswith("#!")):
            begin = starts[token.start[0] - 1] + token.start[1]
            yield begin, begin + len(token.string)
    lines = text.splitlines(keepends=True)
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        first = node.body[0] if node.body else None
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            begin = starts[first.lineno - 1] + len(lines[first.lineno - 1].encode()[: first.col_offset].decode())
            end = starts[first.end_lineno - 1] + len(lines[first.end_lineno - 1].encode()[: first.end_col_offset].decode())
            yield begin, end


def script_comments(text):
    found = []
    size = len(text)

    def quoted(i, quote):
        while i < size and text[i] != quote and text[i] != "\n":
            i += 2 if text[i] == "\\" else 1
        return i + 1

    def template(i):
        while i < size and text[i] != "`":
            if text[i] == "\\":
                i += 2
            elif text.startswith("${", i):
                i = code(i + 2, True)
            else:
                i += 1
        return i + 1

    def regex(i):
        in_class = False
        while i < size and text[i] != "\n" and (in_class or text[i] != "/"):
            if text[i] == "\\":
                i += 1
            elif text[i] == "[":
                in_class = True
            elif text[i] == "]":
                in_class = False
            i += 1
        return i + 1

    def code(i, in_template):
        depth = 0
        before = "("
        while i < size:
            char = text[i]
            if char in "\"'":
                i = quoted(i + 1, char)
                before = "x"
            elif char == "`":
                i = template(i + 1)
                before = "x"
            elif text.startswith("//", i):
                end = text.find("\n", i)
                end = size if end < 0 else end
                found.append((i, end))
                i = end
            elif text.startswith("/*", i):
                end = text.find("*/", i + 2)
                end = size if end < 0 else end + 2
                found.append((i, end))
                i = end
            elif char == "/" and before in REGEX_AFTER:
                i = regex(i + 1)
                before = "x"
            elif char.isalnum() or char in "_$":
                end = i
                while end < size and (text[end].isalnum() or text[end] in "_$"):
                    end += 1
                before = "(" if text[i:end] in REGEX_AFTER_WORD else "x"
                i = end
            else:
                if char == "{":
                    depth += 1
                elif char == "}":
                    if in_template and depth == 0:
                        return i + 1
                    depth -= 1
                if not char.isspace():
                    before = char
                i += 1
        return i

    code(0, False)
    return found


def hash_comments(text):
    position = 0
    for number, line in enumerate(text.splitlines(keepends=True), start=1):
        quote = None
        for column, char in enumerate(line):
            if quote:
                if char == quote:
                    quote = None
            elif char in "\"'":
                quote = char
            elif char == "#" and (column == 0 or line[column - 1].isspace()):
                if not (number == 1 and column == 0 and line.startswith("#!")):
                    yield position + column, position + len(line.rstrip("\r\n"))
                break
        position += len(line)


def comments(path, text):
    if path.suffix == ".py":
        return sorted(python_comments(text))
    if path.suffix in SCRIPT:
        return script_comments(text)
    if path.suffix in HASH or path.name in HASH_NAMES:
        return list(hash_comments(text))
    return []


def files(root):
    for path in sorted(root.rglob("*")):
        if path.is_file() and not SKIPPED.intersection(path.relative_to(root).parts):
            yield path


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    found = 0
    for path in files(root):
        if not (path.suffix == ".py" or path.suffix in SCRIPT or path.suffix in HASH or path.name in HASH_NAMES):
            continue
        text = path.read_text(encoding="utf-8")
        starts = offsets(text)
        for begin, _ in comments(path, text):
            line = max(n for n, start in enumerate(starts, start=1) if start <= begin)
            found += 1
            shown = text[begin:].splitlines()[0].strip()[:60]
            print(f"{path.relative_to(root).as_posix()}:{line}: found a comment: {shown}")
    if found:
        print(f"\n{found} comment(s) or docstring(s) in code and config. {FIX}")
        return 1
    print("No comments in code or config.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
