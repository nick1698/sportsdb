from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal

from scripts.modelgen import next_power_of_2, snake_to_camel


class FieldKind(Enum):
    UUID = "uuid"
    INT = "integer"
    VARCHAR = "varchar"
    TEXT = "text"
    ENUM = "enum"
    TS = "timestamptz"
    DATE = "date"
    NUMERIC = "numeric"
    DATERANGE = "daterange"
    URL = "url"


@dataclass
class SqlType:
    kind: FieldKind
    length: int | None = None  # e.g. varchar(255)
    enum_name: str | None = None  # e.g. postgres enum name
    precision: int | None = None  # e.g. numeric(10,2)
    scale: int | None = None  # e.g. numeric(10,2)

    def __init__(self, kind: FieldKind, **params):
        self.kind = kind
        for k, v in params.items():
            if not hasattr(self, k):
                continue
            self.__setattr__(k, v)

    def check_default(self, def_val: Any, enums: dict[str, "VertEnum"] | None = None):
        match self.kind:
            case FieldKind.UUID:
                return "random" if def_val.startswith("gen_random_uuid") else None
            case FieldKind.INT:
                return int(def_val) if def_val.isdigit() else None
            case FieldKind.VARCHAR | FieldKind.TEXT | FieldKind.URL:
                return def_val if isinstance(def_val, str) else None
            case FieldKind.ENUM:
                enum = enums[self.enum_name]
                try:
                    enum(def_val)
                    return def_val
                except ValueError:
                    return None
            case _:
                return None

    @classmethod
    def resolve(
        cls, raw: str, param: str | None = None, enums: dict | None = None
    ) -> "SqlType":
        if enums and raw in enums:
            return cls(FieldKind.ENUM, enum_name=raw)

        kind = FieldKind(raw)  # NOTE: raises ValueError if type is unknown
        params = {}
        match kind:
            case FieldKind.VARCHAR:
                params["length"] = int(param)
            case FieldKind.NUMERIC:
                prec, scale = param.split(",", 1)
                if prec.isdigit() and scale.isdigit():
                    params["precision"] = int(prec)
                    params["scale"] = int(scale)

        return cls(kind, **params)


class VertField:
    name: str
    ftype: SqlType

    pk: bool = False
    nullable: bool = True
    default: Any = None
    fk: tuple[str, str] | None = None

    comments: dict[str, str] = {}

    def __init__(
        self,
        name: str,
        raw_type: str,
        attrs: str | None = None,
        enums: dict | None = None,
    ):
        self.name = name
        self.ftype = self._resolve_type(raw_type.lower().strip(), enums)
        self._resolve_attrs(attrs, enums)

    @staticmethod
    def _resolve_type(raw: str, enums: dict | None = None) -> SqlType:
        raw = raw.split("(", 1)
        param = raw[1].removesuffix(")") if len(raw) > 1 else None
        return SqlType.resolve(raw[0], param, enums=enums)

    def _resolve_attrs(self, attributes: str | None = None, enums: dict | None = None):
        attributes = (attributes or "").lower()
        if "primary key" in attributes:
            self.pk = True
        if "not null" in attributes:
            self.nullable = False
        if "default" in attributes:
            def_val = (
                attributes.split("default", 1)[1]
                .strip()
                .split(" ")[0]
                .removesuffix(",")
            )
            self.default = self.ftype.check_default(def_val, enums)
        if "references" in attributes:
            tmp = attributes.split("references")[1].strip().split()
            self.fk = (tmp[0], tmp[1].removeprefix("(").removesuffix(")"))

    def add_comment(self, comment: str):
        """
        Using comments as DjangoField parameters values - e.g.:

        '-- fieldname: This is a help text' => help_text='This is a help text'

        '-- fieldname: verbose_name: Field' => verbose_name='Field'
        """
        tmp: list[str] = comment.split(":")
        k: str = tmp[0].strip().lower() if len(tmp) > 1 else "help_text"
        self.comments[k] = tmp[1].strip() if len(tmp) > 1 else comment


class ConstrKind(Enum):
    UNQ = "unique"
    CHK = "check"


# @dataclass
# class ConstraintType:
#     kind: ConstrKind
#     fields: list[str] = []

#     def __init__(self, raw_type: str, fields: list[str]):
#         self.kind = ConstrKind(raw_type)
#         self.fields = fields


"""
campo IS NULL                   ->  Q(campo__isnull=True)
campo IS NOT NULL               ->  Q(campo__isnull=False)
campo = valore                  ->  Q(campo=valore)
campo <> valore                 ->  ~Q(campo=valore) o Q(~campo=valore)
campo > valore                  ->  Q(campo__gt=valore)
campo >= valore                 ->  Q(campo__gte=valore)
campo1 = campo2                 ->  Q(campo1=F('campo2'))
campo1 <> campo2                ->  ~Q(campo1=F('campo2'))
condizione1 OR condizione2      ->  `Q(condizione1)
condizione1 AND condizione2     ->  Q(condizione1) & Q(condizione2)
"""


class VertConstraint:
    name: str

    def __init__(self, name: str):
        self.name = name


class VertUnique(VertConstraint):
    fields: list[str] = []

    def add_field(self, field: str):
        self.fields.append(field)


class VertCheck(VertConstraint):
    raw_condition: str = ""

    def __init__(self, name: str, raw_condition: str):
        super().__init__(name)
        self.raw_condition = raw_condition


class VertIndex:
    def __init__(self, name: str, fields: list[str]):
        self.name = name
        self.fields = fields

    def __str__(self):
        return f"models.Index(name='{self.name}', fields={self.fields})"


class VertEnum:
    name: str
    options: dict[str, str]
    char_len: int = 64

    def __init__(self, name: str, options: dict[str, str]):
        self.name = name
        self.options = options
        self.char_len = next_power_of_2(max(len(s) for s in self.options.keys()))


class VertTable:
    title: str
    djtitle: str
    filename: str = "__init__"
    inherits: Literal["fixed", "growing"] = "growing"

    fields: dict[str, VertField] = {}
    enums: dict[str, VertEnum] = {}
    constraints: dict[str, VertConstraint] = {}
    indexes: dict[str, VertIndex] = {}

    def __init__(self, name: str):
        self.title: str = name.lower()
        self.dj_title: str = snake_to_camel(name)

    def read_comments(self, **comments):
        """Saving comments written in '[key]:[value]' style"""
        for k, v in comments.items():
            if hasattr(self, k):
                # set header attribute
                self.__setattr__(k, v)
            elif k in self.fields:
                # add comment to field
                self.fields[k].add_comment(v)

    def add_field(self, field: VertField):
        self.fields[field.name] = field

    def add_enums(self, enums: dict):
        self.enums = enums

    def add_constraint(self, constraint: VertConstraint):
        self.constraints[constraint.name] = constraint

    def add_index(self, name: str, fields: list[str]):
        self.indexes[name] = VertIndex(name, fields)
