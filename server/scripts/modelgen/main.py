#! /usr/bin/env python3

from collections import defaultdict
import sys

from common import snake_to_camel
from parsers import parse_schema
from tables import VertEnum, VertTable


IMPORTS = {
    "uuid": "import uuid",
    "postgres_fields": "from django.contrib.postgres import fields",
    "minval": "from django.core.validators import MinValueValidator",
    "maxval": "from django.core.validators import MinValueValidator",
    "growing": "from shared.utils.models import GrowingTable",
    "fixed": "from shared.utils.models import FixedTable",
}


def write(file_path: str, content: str):
    with open(f"test/{file_path}.py", "a") as f:
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

    # write enums in their file
    write("enums", "from django.db import models\n")
    for enum_name, enum in enums.items():
        write("enums", str(enum))

    # write imports at the top of the files
    file_imports = defaultdict(set)
    for table in tables.values():
        if len(table.imports) > 0:
            file_imports[table.file].update(table.imports)
    IMPORTS.update({e: f"from enums import {snake_to_camel(e)}" for e in enums})
    for f, imps in file_imports.items():
        write(f, "from django.db import models\n")
        write(f, "\n".join((IMPORTS[i] for i in imps)))
        write(f, "\n")

    # write tables/models inside their respective files
    for table_name, table in tables.items():
        write(table.file, str(table))
