from typing import Generator, Literal

from sqlparse.sql import Identifier, Parenthesis
from sqlparse.tokens import Keyword

from .tables import VertCheck, VertEnum, VertTable, VertConstraint, VertField, VertUnique


def parse_enum(name: str, content: Parenthesis) -> VertEnum:
    content = content.normalized.split("\n")

    options = (line.split("--") for line in content if len(line.strip()) > 1)
    options: dict[str, str] = {
        o[0].strip(" ',").upper(): o[1].strip() for o in options
    }
    return VertEnum(name, options.copy())


def parse_constraint(name: str, ctype: Literal["unique", "check"], raw_content: str) -> VertConstraint:
    raw_content = raw_content.strip("()").split(",")
    match ctype:
        case "unique":
            c = VertUnique(name)
            for field in (f.strip().lower() for f in raw_content):
                c.add_field(field)
        case "check":
            c = VertCheck(name, raw_content)
    return c


def parse_table(title: str, content: Parenthesis, enums: dict) -> VertTable:
    table = VertTable(title)
    table.add_enums(enums)

    content = content.normalized.split("constraint")[0].split("\n")

    # read fields
    fields = (
        line.split("--")[0].strip().removesuffix(",")
        for line in content
        if len(line.strip()) > 1
    )
    for line in fields:
        table.add_field(VertField(*line.split(" ", 2), enums=table.enums))

    # read comments
    comment_lines: Generator[str] = (
        line.split("--")[1].strip() for line in content if "--" in line and ":" in line
    )
    comments: dict[str, str] = {
        c[0].strip().lower(): c[1].strip() for c in comment_lines
    }
    table.read_comments(**comments)

    # read constraints
    for c in (t for t in content.tokens if t.match(Keyword, "constraint")):
        idx = content.token_index(c)
        _, name = content.token_next_by(idx=idx, i=Identifier)
        _, ctype = content.token_next_by(idx=idx, t=Keyword)
        _, constraint = content.token_next_by(idx=idx, i=Parenthesis)
        table.add_constraint(
            parse_constraint(name.value, ctype.value, constraint.value)
        )

    return table
