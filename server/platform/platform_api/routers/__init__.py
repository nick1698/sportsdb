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

    @property
    def presence_short(self):
        return self._build_path(
            self.config.table_ep, f"{{{self.config.pk}}}", "presences"
        )

    @property
    def presence_base(self):
        return self._build_path(
            "api", self.config.router, self.config.table_ep, f"{{{self.config.pk}}}", "presences"
        )

    def presence(self, pk: str, **params):
        path = self._build_path(
            "api", self.config.router, self.config.table_ep, str(pk), "presences"
        )
        return self._with_query(path, params)
