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
    def presence_retrieve_url(self):
        """e.g. "/countries/{iso2}/presences"""
        return self._build_path(
            self.config.table_ep, f"{{{self.config.pk}}}", "presences"
        )

    @property
    def presence_list_url(self):
        """e.g. "/api/core/countries/{iso2}/presences"""
        return self._build_path(self._router_prefix, self.presence_retrieve_url)

    def compose_presence_url(self, pk: str, **params):
        path = self._build_path(
            self._router_prefix, self.config.table_ep, str(pk), "presences"
        )
        return self._with_params(path, params)
