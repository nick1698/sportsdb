from server.shared.utils.routing import BaseRoute, TableUrlConfig

from platform_api.models.entities import Sport
from platform_api.models.geo import Country, GeoPlace


class PlatformRoute(BaseRoute):
    TABLES_URLS = {
        Country: TableUrlConfig("core", "countries", "iso2"),
        Sport: TableUrlConfig("core", "sports", "key"),
        GeoPlace: TableUrlConfig("geo", "locations"),
    }
