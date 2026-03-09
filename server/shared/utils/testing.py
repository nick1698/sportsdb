def assert_list_envelope(
    data: dict, *, limit: int | None = None, offset: int | None = None
):
    assert "items" in data and isinstance(data["items"], list)
    assert "limit" in data and isinstance(data["limit"], int)
    assert "offset" in data and isinstance(data["offset"], int)
    assert "total" in data and isinstance(data["total"], int)

    if limit is not None:
        assert data["limit"] == limit
    if offset is not None:
        assert data["offset"] == offset
