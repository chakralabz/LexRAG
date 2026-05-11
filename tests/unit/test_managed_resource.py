from __future__ import annotations

from lexrag.runtime import ManagedResource


def test_managed_resource_loads_once_and_closes() -> None:
    calls: list[str] = []

    def loader() -> dict[str, str]:
        calls.append("load")
        return {"status": "ready"}

    def finalizer(resource: dict[str, str]) -> None:
        calls.append(resource["status"])

    resource = ManagedResource(loader=loader, finalizer=finalizer)

    first = resource.load()
    second = resource.get()
    resource.close()

    assert first == {"status": "ready"}
    assert second == {"status": "ready"}
    assert calls == ["load", "ready"]
    assert resource.loaded is False
