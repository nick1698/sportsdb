#! /usr/bin/env python3

import sys
from parsers import parse_schema
from tables import VertEnum, VertTable


def write(file_path: str, content: str):
    with open(file_path, "a") as f:
        f.write(content)


# Esecuzione
if __name__ == "__main__":
    sql_filepath = sys.argv[1] if len(sys.argv) > 1 else "schema.sql"

    # read the SQL DDL schema
    with open(sql_filepath, "r") as f:
        sql_schema = f.read()

    # parse the schema to obtain tables
    tables: dict[str, VertTable] = {}
    enums: dict[str, VertEnum] = {}
    parse_schema(sql_schema, tables, enums)

    for table_name, table in tables.items():
        write(table.filename, str(table))
