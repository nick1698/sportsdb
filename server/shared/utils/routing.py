from urllib.parse import urlencode

from shared.api_contract.schemas import ListEnvelope


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
    def _build_path(*parts: str | None) -> str:
        cleaned = [part.strip("/") for part in parts if part]
        return "/" + "/".join(cleaned)

    @staticmethod
    def _with_params(path: str, params: dict) -> str:
        if not params:
            return path
        return f"{path}?{urlencode(params)}"

    # endregion

    # region PROPERTIES

    @property
    def _router_prefix(self):
        """e.g. "/api/core" """
        return self._build_path("api", self.config.router)

    @property
    def list_short_url(self):
        """e.g. "/countries" """
        return self._build_path(self.config.table_ep)

    @property
    def retrieve_short_url(self):
        """e.g. "/countries/{iso2}" """
        return self._build_path(self.config.table_ep, f"{{{self.config.pk}}}")

    @property
    def search_short_url(self):
        """e.g. "/search/countries" """
        return self._build_path("search", self.config.table_ep)

    @property
    def list_url(self):
        """e.g. "/api/core/countries" """
        return self._build_path(self._router_prefix, self.config.table_ep)

    @property
    def retrieve_demo_url(self):
        """e.g. "/api/core/countries/{iso2}" """
        return self._build_path(
            self._router_prefix, self.config.table_ep, f"{{{self.config.pk}}}"
        )

    @property
    def search_url(self):
        """e.g. "/api/core/search/countries" """
        return self._build_path(self._router_prefix, "search", self.config.table_ep)

    # endregion

    # region GET METHODS

    def compose_list_url(self, **params):
        """e.g. "/api/core/countries?param1=...&param2=..." """
        return self._with_params(self.list_url, params)

    def compose_retrieve_url(self, pk: str, **params):
        """e.g. "/api/core/countries/[pk]?param1=...&param2=..." """
        path = self._build_path(self._router_prefix, self.config.table_ep, str(pk))
        return self._with_params(path, params)

    # endregion

    # region POST METHODS

    def compose_post_url(
        self, action: str = "create", pk: str | None = None, short=False
    ):
        match pk, short:
            case None, True:
                """e.g. "/countries/[action]/" """
                return self._build_path(self.config.table_ep, action)
            case None, False:
                """e.g. "/api/core/countries/[action]/" """
                return self._build_path(
                    self._router_prefix, self.config.table_ep, action
                )
            case _, True:
                """e.g. "/countries/[action]/{iso2}/" """
                return self._build_path(
                    self.config.table_ep, action, f"{{{self.config.pk}}}"
                )
            case pk, False:
                """e.g. "/api/core/countries/[action]/[pk]" """
                return self._build_path(
                    self._router_prefix, self.config.table_ep, action, pk
                )

    # endregion


def search_query_helper(params: str, query) -> ListEnvelope:
    # normalization
    ps: str | None = params.strip() if params else None
    if not ps:
        return ListEnvelope(
            items=[],
            total=0,
            limit=1,
            offset=0,
            sort=None,
        )

    """
    `icontains`, then annotate with a numeric rank:
        0 = exact
        1 = startswith
        2 = contains
    """
    items = list(query(ps))
    return ListEnvelope(
        items=items,
        total=len(items),
        limit=max(len(items), 1),
        offset=0,
        sort=None,
    )
