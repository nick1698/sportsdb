from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, Optional

from common import next_power_of_2, snake_to_camel


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

    def djangofield(self):
        match self.name:
            case "UUID":
                return "models.UUIDField"
            case "INT":
                return "models.IntegerField"
            case "VARCHAR":
                return "models.CharField"
            case "TEXT":
                return "models.TextField"
            case "ENUM":
                return "models.CharField"
            case "TS":
                return "models.DateTimeField"
            case "DATE":
                return "models.DateField"
            case "NUMERIC":
                return "models.DecimalField"
            case "DATERANGE":
                return "fields.DateRangeField"
            case "URL":
                return "models.URLField"
            case _:
                raise ValueError(f"Unsupported field type: {self.name}")


@dataclass
class SqlType:
    kind: FieldKind
    length: int | None  # e.g. varchar(255)
    enum_name: str | None  # e.g. postgres enum name
    max_digits: int | None  # e.g. numeric(10,2)
    decimals: int | None  # e.g. numeric(10,2)
    imports: str | None

    def __init__(self, kind: FieldKind, **params):
        self.kind = kind
        self.length = None
        self.enum_name = None
        self.max_digits = None
        self.decimals = None
        self.imports = None

        for k, v in params.items():
            if not hasattr(self, k):
                continue
            self.__setattr__(k, v)

    def check_default(self, def_val: Any, enums: dict[str, "VertEnum"] | None = None):
        match self.kind:
            case FieldKind.UUID:
                return "uuid.uuid4" if def_val.startswith("gen_random_uuid") else None
            case FieldKind.INT:
                return int(def_val) if def_val.isdigit() else None
            case FieldKind.VARCHAR | FieldKind.TEXT | FieldKind.URL:
                return def_val if isinstance(def_val, str) else None
            case FieldKind.ENUM:
                enum = enums[self.enum_name]
                return def_val if def_val.upper() in [o.upper() for o in enum.options.keys()] else None
            case _:
                return None

    @classmethod
    def resolve(cls, raw: str, param: str | None = None, enums: dict | None = None) -> "SqlType":
        if enums and raw in enums:
            return cls(FieldKind.ENUM, enum_name=raw, imports=raw)

        kind = FieldKind(raw)  # NOTE: raises ValueError if type is unknown
        params = {}
        match kind:
            case FieldKind.UUID:
                params["imports"] = "uuid"
            case FieldKind.VARCHAR:
                params["length"] = int(param)
            case FieldKind.NUMERIC:
                prec, scale = param.split(",", 1)
                if prec.isdigit() and scale.isdigit():
                    params["precision"] = int(prec)
                    params["scale"] = int(scale)
            case FieldKind.DATERANGE:
                params["imports"] = "postgres_fields"

        return cls(kind, **params)

    def format(self) -> dict[str, str]:
        base = {"field": self.kind.djangofield()}
        if self.length:
            base["max_length"] = self.length
        if self.enum_name:
            base["choices"] = f"{snake_to_camel(self.enum_name)}.choices"
        if self.max_digits:
            base["max_digits"] = self.max_digits
        if self.decimals:
            base["decimal_places"] = self.decimals
        return base


class VertField:
    name: str
    ftype: SqlType

    pk: bool
    nullable: bool
    default: Any
    fk: tuple[str, str] | None  # (table, field)
    unique: bool
    editable: bool

    comments: dict[str, str]
    imports: list[str]

    def __init__(
        self,
        name: str,
        raw_type: str,
        attrs: str | None = None,
        enums: dict | None = None,
    ):
        self.name = name
        self.imports = []

        self.ftype = self._resolve_type(raw_type.lower().strip(), enums)
        if self.ftype.imports:
            self.imports.append(self.ftype.imports)

        self.pk = False
        self.nullable = True
        self.default = None
        self.fk = None
        self.unique = False
        self.editable = True
        self.comments = {}

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
            def_val = attributes.split("default", 1)[1].strip().split(" ")[0].removesuffix(",")
            self.default = self.ftype.check_default(def_val, enums)
            self.nullable = False
            if self.default == "uuid.uuid4":
                self.editable = False
        if "references" in attributes:
            tmp = attributes.split("references")[1].strip().split()
            self.fk = (tmp[0], tmp[1].removeprefix("(").removesuffix(")"))
        if "unique" in attributes:
            self.unique = True

    def add_comment(self, comment: str):
        """
        Using comments as DjangoField parameters values - e.g.:

        '-- fieldname: This is a help text' => help_text='This is a help text'

        '-- fieldname: verbose_name: Field' => verbose_name='Field'
        """
        tmp: list[str] = comment.split(":")
        if len(tmp) > 1:
            k: str = tmp[0].strip().lower()
            self.comments[k] = tmp[1].strip()

            if "MinValueValidator" in tmp[1]:
                self.imports.append("minval")
            if "MaxValueValidator" in tmp[1]:
                self.imports.append("maxval")
        else:
            self.comments["help_text"] = comment[0].upper() + comment[1:]

    def __str__(self):
        ftype_params = self.ftype.format()
        ftype = ftype_params.pop("field", "models.TextField")

        base = f"{self.name} = {ftype}"

        params = {}
        for k, v in ftype_params.items():
            params[k] = v
        if self.pk:
            params["primary_key"] = True
        if self.fk:
            params[""] = self.fk[0]
            params["on_delete"] = "models.CASCADE"
            if self.fk[1] != "id":
                params["to_field"] = self.fk[1]
                params["db_column"] = f"{self.name}_{self.fk[1]}"
        if self.nullable:
            params["blank"] = True
            params["null"] = True
        if self.unique:
            params["unique"] = True
        if self.default:
            params["default"] = self.default
        if not self.editable:
            params["editable"] = False

        for k, v in self.comments.items():
            params[k] = v

        field_params = []
        for k, v in params.items():
            match k:
                case "default":
                    if self.ftype.kind == FieldKind.VARCHAR:
                        field_params.append(f"{k}='{v}'")
                    else:
                        field_params.append(f"{k}={v}")
                case "":
                    field_params.append(f"'{v}'")
                case "help_text" | "related_name":
                    field_params.append(f"{k}=\"{v}\"")
                case _:
                    field_params.append(f"{k}={v}")

        return f"{base}({', '.join(field_params)})\n"


class ConstrKind(Enum):
    UNQ = "unique"
    CHK = "check"


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
    fields: list[str]

    def __init__(self, name):
        super().__init__(name)
        self.fields = []

    def add_field(self, field: str):
        self.fields.append(field)

    def __str__(self):
        return f"models.UniqueConstraint(name='{self.name}', fields={self.fields})"


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

    def __str__(self):
        name = snake_to_camel(self.name)
        options = "    ".join(f"{k} = '{v}'\n" for k, v in self.options.items())

        return f"""
class {name}(models.TextChoices):
    {options}
"""


class VertTable:
    title: str
    djtitle: str
    file: str
    inherits: Literal["fixed", "growing"]
    verbose_name: Optional[str]
    verbose_name_plural: Optional[str]

    fields: dict[str, VertField]
    enums: dict[str, VertEnum]
    constraints: dict[str, VertConstraint]
    indexes: dict[str, VertIndex]
    imports: set[str]

    def __init__(self, name: str):
        self.title: str = name.lower()
        self.dj_title: str = snake_to_camel(name.lower())
        self.file = "__init__"
        self.inherits = "growing"
        self.verbose_name = name.capitalize().replace("_", " ")
        self.verbose_name_plural = f"{self.verbose_name}s"

        self.fields = {}
        self.enums = {}
        self.constraints = {}
        self.indexes = {}
        self.imports = set()

    def read_comments(self, **comments):
        """Saving comments written in '[key]:[value]' style"""
        for k, v in comments.items():
            if hasattr(self, k):
                # set header attribute
                self.__setattr__(k, v)
            elif k in self.fields:
                # add comment to field
                self.fields[k].add_comment(v)
                self.imports.update(self.fields[k].imports)
        self.imports.add(self.inherits)

    def add_field(self, field: VertField):
        self.fields[field.name] = field
        self.imports.update(field.imports)

    def add_enums(self, enums: dict):
        self.enums = enums

    def add_constraint(self, constraint: VertConstraint):
        self.constraints[constraint.name] = constraint

    def add_index(self, name: str, fields: list[str]):
        self.indexes[name] = VertIndex(name, fields)

    def __str__(self):
        table_kind = f"{self.inherits.capitalize()}Table"

        pk = None
        for field in self.fields.values():
            if field.pk:
                pk = field
                break
        if pk is None:
            raise ValueError(f"No primary key defined for table '{self.title}'")

        non_pk_fields = "    ".join(str(f) for n, f in self.fields.items() if n != pk.name)

        constraints = None
        # constraints = (
        #     "        ".join(str(c) for c in self.constraints.values())
        #     if self.constraints
        #     else ""
        # )
        indexes = None
        # indexes = (
        #     "        ".join(str(c) for c in self.indexes.values())
        #     if self.indexes
        #     else ""
        # )

        return f"""
class {self.dj_title}({table_kind}):
    {pk}
    {non_pk_fields}

    class Meta:
        db_table = "{self.title}"
        verbose_name = "{self.verbose_name.capitalize()}"
        verbose_name_plural = "{self.verbose_name_plural.capitalize()}"
        {f"constraints = [{constraints}]" if self.constraints else ""}
        {f"indexes = [{indexes}]" if self.indexes else ""}

"""
