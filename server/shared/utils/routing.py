from urllib.parse import urlencode, urljoin


class TableUrlConfig:
    router: str
    table_ep: str
    pk: str

    def __init__(self, router, table_ep, pk="id"):
        self.router = router
        self.table_ep = table_ep
        self.pk = pk


class BaseRoute:
    t: type
    TABLES_URLS: dict[type, TableUrlConfig] = {}

    def __init__(self, t: type):
        self.t = t
        if self.t not in self.TABLES_URLS.keys():
            self.TABLES_URLS[self.t] = TableUrlConfig("/", "")

    @property
    def short(self):
        uc = self.TABLES_URLS[self.t]
        return f"/{uc.table_ep}"

    @property
    def short_id(self):
        uc = self.TABLES_URLS[self.t]
        return urljoin(f"/{uc.table_ep}/", f"{{{uc.pk}}}")

    @property
    def base(self):
        uc = self.TABLES_URLS[self.t]
        return urljoin("/api/", f"{uc.router}/{uc.table_ep}")

    @property
    def base_id(self):
        uc = self.TABLES_URLS[self.t]
        return urljoin("/api/", f"{uc.router}/{uc.table_ep}/{{{uc.pk}}}")

    def list(self, **params):
        uc = self.TABLES_URLS[self.t]
        return urljoin("/api/", f"{uc.router}/{uc.table_ep}?{urlencode(params)}")

    def retrieve(self, pk: str, **params):
        uc = self.TABLES_URLS[self.t]
        return urljoin("/api/", f"{uc.router}/{uc.table_ep}/{pk}?{urlencode(params)}")
