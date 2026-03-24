from .parsers import parse_schema
from .tables import VertEnum, VertTable


def map_sql_type_to_django(sql_type):
    pass
    # sql_type = sql_type.upper()
    # if "VARCHAR" in sql_type or "CHAR" in sql_type:
    #     max_length = int(sql_type.split("(")[1].split(")")[0])
    #     return f"CharField(max_length={max_length})"
    # elif "INT" in sql_type:
    #     return "IntegerField()"
    # elif "TEXT" in sql_type:
    #     return "TextField()"
    # elif "BOOLEAN" in sql_type:
    #     return "BooleanField()"
    # elif "DATE" in sql_type:
    #     return "DateField()"
    # elif "DATETIME" in sql_type:
    #     return "DateTimeField()"
    # elif "DECIMAL" in sql_type:
    #     precision, scale = sql_type.split("(")[1].split(")")[0].split(",")
    #     return f"DecimalField(max_digits={precision}, decimal_places={scale})"
    # else:
    #     return "TextField()"


def generate_model_class(table_name, columns):
    pass
    # model_code = f"from django.db import models\n\n\nclass {table_name.capitalize()}(models.Model):\n"
    # for column in columns:
    #     field_name, sql_type = column.split(":")
    #     django_type = map_sql_type_to_django(sql_type)
    #     model_code += f"    {field_name} = {django_type}\n"
    # model_code += "\n    class Meta:\n        managed = False\n        db_table = '{table_name}'\n"
    # return model_code


def write(file_path: str, content: str):
    with open(file_path, "a") as f:
        f.write(content)


# Esecuzione
if __name__ == "__main__":
    # read the SQL DDL schema
    with open("schema.sql", "r") as f:
        sql_schema = f.read()

    # parse the schema to obtain tables
    tables: dict[str, VertTable] = {}
    enums: dict[str, VertEnum] = {}
    parse_schema(sql_schema, tables, enums)

    for table_name, table in tables.items():
        write(table.filename, str(table))
