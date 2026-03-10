from urllib.parse import urlencode

from shared.api_contract.ninja import ListEnvelope


class TableUrlConfig:
    router: str
    table_ep: str
    pk: str

    def __init__(self, router, table_ep, pk="id"):
        self.router = router
        self.table_ep = table_ep
        self.pk = pk


class BaseRoute:
    # region BASE

    t: type
    TABLES_URLS: dict[type, TableUrlConfig] = {}

    def __init__(self, t: type):
        self.t = t

    @property
    def config(self) -> TableUrlConfig:
        return self.TABLES_URLS.get(self.t, TableUrlConfig("/", ""))

    # endregion

    # region CLASS HELPERS

    @staticmethod
    def _build_path(*parts: str) -> str:
        cleaned = [part.strip("/") for part in parts if part]
        return "/" + "/".join(cleaned)

    @staticmethod
    def _with_query(path: str, params: dict) -> str:
        if not params:
            return path
        return f"{path}?{urlencode(params)}"

    # endregion

    # region PROPERTIES

    @property
    def short(self):
        return self._build_path(self.config.table_ep)

    @property
    def short_id(self):
        return self._build_path(self.config.table_ep, f"{{{self.config.pk}}}")

    @property
    def search_short(self):
        return self._build_path("search", self.config.table_ep)

    @property
    def base(self):
        return self._build_path("api", self.config.router, self.config.table_ep)

    @property
    def base_id(self):
        return self._build_path(
            "api", self.config.router, self.config.table_ep, f"{{{self.config.pk}}}"
        )

    @property
    def search(self):
        return self._build_path(
            "api", self.config.router, "search", self.config.table_ep
        )

    # endregion

    # region QUERY METHODS

    def list(self, **params):
        return self._with_query(self.base, params)

    def retrieve(self, pk: str, **params):
        path = self._build_path(
            "api", self.config.router, self.config.table_ep, str(pk)
        )
        return self._with_query(path, params)

    # endregion


def search_query_helper(params: str, query) -> ListEnvelope:
    # normalization
    params = params.strip() if params else None
    if not params:
        return {
            "items": [],
            "total": 0,
            "limit": 1,
            "offset": 0,
            "sort": None,
        }

    """
    `icontains`, then annotate with a numeric rank:
        0 = exact
        1 = startswith
        2 = contains
    """
    items = list(query(params))
    return {
        "items": items,
        "total": len(items),
        "limit": max(len(items), 1),
        "offset": 0,
        "sort": None,
    }
