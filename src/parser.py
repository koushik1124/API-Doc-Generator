import ast
import logging
from pathlib import Path
from typing import List, Dict, Optional
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CodeParser:
    """
    Production-safe Python code parser.

    Features:
    - Supports def + async def
    - Multiple encodings
    - AST + regex fallback
    - Safe docstring extraction
    - Cross-version compatible (3.8+)
    - Never returns empty source
    """

    MAX_SOURCE_LINES = 25

    # -------------------------------------------------

    def parse_file(self, file_path: str) -> List[Dict]:

        content = self._read_file_safe(file_path)

        if not content:
            logger.error(f"Could not read file: {file_path}")
            return []

        try:
            tree = ast.parse(content)
            functions = self._parse_ast(tree, content)

            if functions:
                logger.info(f"Parsed {len(functions)} functions via AST")
                return functions

        except SyntaxError as e:
            logger.warning(f"AST failed, falling back to regex: {e}")

        # Fallback
        fallback = self._parse_with_fallback(content)

        logger.info(f"Parsed {len(fallback)} functions via fallback")
        return fallback

    # -------------------------------------------------

    def _parse_ast(self, tree, source):

        results = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                info = self._extract_function(node, source)
                if info:
                    results.append(info)

        return results

    # -------------------------------------------------

    def _read_file_safe(self, path: str) -> Optional[str]:

        encodings = ("utf-8", "utf-8-sig", "latin-1", "cp1252")

        for enc in encodings:
            try:
                txt = Path(path).read_text(encoding=enc)
                return self._clean_content(txt)
            except Exception:
                continue

        return None

    # -------------------------------------------------

    def _clean_content(self, text: str) -> str:

        # remove citation artifacts
        text = re.sub(r"\[cite:.*?\]", "", text)
        text = re.sub(r"\[ref:.*?\]", "", text)
        text = re.sub(r"\[source:.*?\]", "", text)

        return text

    # -------------------------------------------------

    def _extract_function(self, node, source):

        try:
            args = []
            for arg in node.args.args:
                if arg.annotation:
                    try:
                        args.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
                    except Exception:
                        args.append(arg.arg)
                else:
                    args.append(arg.arg)

            returns = None
            if node.returns:
                try:
                    returns = ast.unparse(node.returns)
                except Exception:
                    pass

            doc = self._safe_docstring(node)
            code = self._extract_source(node, source)

            return {
                "name": node.name,
                "args": args,
                "returns": returns,
                "docstring": doc,
                "source": code,
                "lineno": getattr(node, "lineno", 0),
            }

        except Exception as e:
            logger.debug(f"Function extraction failed: {e}")
            return None

    # -------------------------------------------------

    def _safe_docstring(self, node) -> str:

        try:
            ds = ast.get_docstring(node)
            if ds:
                return self._normalize_doc(ds)
        except Exception:
            pass

        return ""

    # -------------------------------------------------

    def _normalize_doc(self, ds: str) -> str:

        lines = [l.strip() for l in ds.splitlines()]
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()

        return "\n".join(lines)

    # -------------------------------------------------

    def _extract_source(self, node, src):

        try:
            lines = src.splitlines()

            start = node.lineno - 1
            end = getattr(node, "end_lineno", start + 10)

            block = lines[start:end][: self.MAX_SOURCE_LINES]

            if len(block) == self.MAX_SOURCE_LINES:
                block.append("    # ... truncated")

            return "\n".join(block)

        except Exception:
            return f"def {node.name}(...):"

    # -------------------------------------------------
    # Regex fallback (last resort)
    # -------------------------------------------------

    def _parse_with_fallback(self, content: str) -> List[Dict]:

        pattern = re.compile(r"^\s*(async\s+)?def\s+(\w+)\s*\((.*?)\)\s*(?:->\s*(\S+))?\s*:", re.M)

        matches = pattern.finditer(content)
        lines = content.splitlines()

        results = []

        for m in matches:
            name = m.group(2)
            params = [p.strip() for p in m.group(3).split(",") if p.strip()]
            returns = m.group(4)

            line_no = content[: m.start()].count("\n")

            snippet = lines[line_no : line_no + 15]

            results.append({
                "name": name,
                "args": params,
                "returns": returns,
                "docstring": "",
                "source": "\n".join(snippet),
                "lineno": line_no + 1,
            })

        return results


# legacy compatibility
def parse_python_file(file_path: str) -> List[Dict]:
    return CodeParser().parse_file(file_path)
