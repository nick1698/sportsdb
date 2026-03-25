import copy
from typing import Literal

import sqlparse
from sqlparse.sql import Function, Identifier, Parenthesis, Statement
from sqlparse.tokens import Keyword

from tables import (
    VertCheck,
    VertEnum,
    VertTable,
    VertConstraint,
    VertField,
    VertUnique,
)


def parse_enum(name: str, content: Parenthesis, enums: dict):
    print(f"\n{name.upper()}")
    content = content.normalized.split("\n")

    options = (line.split("--") for line in content if len(line.strip()) > 1)
    options: dict[str, str] = {o[0].strip(" ',").upper(): o[1].strip() for o in options}

    enums[name] = VertEnum(name, options)


def parse_constraint(name: str, ctype: Literal["unique", "check"], raw_content: str) -> VertConstraint:
    raw_content = raw_content.strip("(),\n ").split(",")
    match ctype:
        case "unique":
            c = VertUnique(name)
            for field in (f.strip().lower() for f in raw_content):
                c.add_field(field.strip("()"))
        case "check":
            c = VertCheck(name, raw_content[0])
    return c


def parse_table(title: str, content: Parenthesis, tables: dict, _enums_copy_: dict):
    table: VertTable = VertTable(title)
    table.add_enums(_enums_copy_)
    print(f"\n{title.upper()}")

    # dividing fields from constraints
    tmp = content.normalized.split("constraint")

    field_lines = tmp[0].split("\n")

    # read fields
    fields = (line for line in (line.split("--")[0].strip().removesuffix(",") for line in field_lines) if len(line) > 1)
    for line in fields:
        table.add_field(VertField(*line.split(" ", 2), enums=table.enums))

    # read comments
    comment_lines: list[str] = [c.split(":", 1) for c in (line.split("--")[1].strip() for line in field_lines if "--" in line and ":" in line)]
    comments: dict[str, str] = {c[0].strip().lower(): c[1].strip() for c in comment_lines}
    table.read_comments(**comments)

    # read constraints
    for c in tmp[1:]:
        constr = c.strip().split(" ", 2)
        table.add_constraint(parse_constraint(name=constr[0], ctype=constr[1], raw_content=constr[2]))

    tables[title] = copy.deepcopy(table)


def parse_schema(schema, tables: dict, enums: dict):
    schema: tuple[Statement] = sqlparse.parse(schema)

    for statement in schema:
        idx, _ = statement.token_next_by(t=Keyword.DDL)
        _, obj = statement.token_next_by(idx=idx, t=Keyword)
        _, name = statement.token_next_by(idx=idx, i=Identifier)
        name: str = name.value

        match obj.value.lower():
            case "type":
                name = name.replace(" as enum", "")
                enum_content: Parenthesis = statement.token_next_by(idx=idx, i=Parenthesis)[1]
                parse_enum(name, enum_content, enums)
            case "table":
                table_content: Parenthesis = statement.token_next_by(idx=idx, i=Parenthesis)[1]
                parse_table(name, table_content, tables, enums.copy())
            case "index":
                _, fn = statement.token_next_by(idx=idx, i=Function)
                table_name: str = fn.value.split(" ")[0]
                params: list[str] = [p.value for p in fn.get_parameters()]

                tables[table_name].add_index(name, params)
