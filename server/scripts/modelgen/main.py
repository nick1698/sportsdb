import sqlparse
from sqlparse.sql import Function, Identifier, Parenthesis, Statement
from sqlparse.tokens import Keyword

from .parsers import parse_enum, parse_table


def parse_statements(schema):
    schema: tuple[Statement] = sqlparse.parse(schema)
    tables: dict = {}
    enums: dict = {}

    for statement in schema:
        idx, _ = statement.token_next_by(t=Keyword.DDL)
        _, obj = statement.token_next_by(idx=idx, t=Keyword)
        _, name = statement.token_next_by(idx=idx, i=Identifier)
        name: str = name.value

        match obj.value:
            case "type":
                name = name.replace(" as enum", "")
                enum_content: Parenthesis = statement.token_next_by(
                    idx=idx, i=Parenthesis
                )
                enums[name] = parse_enum(name, enum_content)
            case "table":
                table_content: Parenthesis = statement.token_next_by(
                    idx=idx, i=Parenthesis
                )
                tables[name] = parse_table(name, table_content, enums.copy())
            case "index":
                _, fn = statement.token_next_by(idx=idx, i=Function)
                table_name: str = fn.value.split(" ")[0]
                params: list[str] = [p.value for p in fn.get_parameters()]

                tables[table_name].add_index(name, params)

    return tables


def map_sql_type_to_django(sql_type):
    sql_type = sql_type.upper()
    if "VARCHAR" in sql_type or "CHAR" in sql_type:
        max_length = int(sql_type.split("(")[1].split(")")[0])
        return f"CharField(max_length={max_length})"
    elif "INT" in sql_type:
        return "IntegerField()"
    elif "TEXT" in sql_type:
        return "TextField()"
    elif "BOOLEAN" in sql_type:
        return "BooleanField()"
    elif "DATE" in sql_type:
        return "DateField()"
    elif "DATETIME" in sql_type:
        return "DateTimeField()"
    elif "DECIMAL" in sql_type:
        precision, scale = sql_type.split("(")[1].split(")")[0].split(",")
        return f"DecimalField(max_digits={precision}, decimal_places={scale})"
    else:
        return "TextField()"


def generate_model_class(table_name, columns):
    model_code = f"from django.db import models\n\n\nclass {table_name.capitalize()}(models.Model):\n"
    for column in columns:
        field_name, sql_type = column.split(":")
        django_type = map_sql_type_to_django(sql_type)
        model_code += f"    {field_name} = {django_type}\n"
    model_code += "\n    class Meta:\n        managed = False\n        db_table = '{table_name}'\n"
    return model_code


def save_model_to_file(model_code, file_path):
    with open(file_path, "w") as f:
        f.write(model_code)


# Esecuzione
with open("schema.sql", "r") as f:
    sql_schema = f.read()
tables = parse_statements(sql_schema)

for table_name, columns in tables.items():
    model_code = generate_model_class(table_name, columns)
    save_model_to_file(model_code, f"{table_name}_models.py")
