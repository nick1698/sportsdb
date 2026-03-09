from shared.utils.routing import BaseRoute, TableUrlConfig

from platform_api.models.entities import Org, Person, Sport
from platform_api.models.geo import Country, GeoPlace, Venue


class PlatformRoute(BaseRoute):
    TABLES_URLS = {
        Country: TableUrlConfig("core", "countries", "iso2"),
        Sport: TableUrlConfig("core", "sports", "key"),
        GeoPlace: TableUrlConfig("geo", "locations"),
        Venue: TableUrlConfig("geo", "venues"),
        Org: TableUrlConfig("people", "orgs"),
        Person: TableUrlConfig("people", "persons"),
    }
