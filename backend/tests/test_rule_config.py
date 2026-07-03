from __future__ import annotations

from app.persistence import AlphaStateRepository
from app.services import AlphaStore
from app.simulation import DEFAULT_SIMULATION_RULES
from app.simulation.rule_config import validate_rules_update


def test_rules_update_validation_accepts_partial_safe_change() -> None:
    result = validate_rules_update(
        {"population": {"growthFactor": 0.12}},
        DEFAULT_SIMULATION_RULES,
    )

    assert result.valid is True
    assert result.rules.population.growth_factor == 0.12
    assert result.public_rules["population"]["growthFactor"] == 0.12
    assert len(result.rules_hash) == 64


def test_rules_update_validation_rejects_unknown_and_unsafe_change() -> None:
    result = validate_rules_update(
        {
            "population": {"growthFactor": 1.4},
            "unknown": {"value": 1},
        },
        DEFAULT_SIMULATION_RULES,
    )

    assert result.valid is False
    assert {error["path"] for error in result.errors} == {
        "population.growthFactor",
        "unknown",
    }


def test_store_applies_and_rolls_back_rules_in_memory() -> None:
    store = AlphaStore(seed=4211, boot_ticks=1)
    original = store.simulation_rules()

    applied = store.apply_simulation_rules(
        {"population": {"growthFactor": 0.12}},
        actor_id="test-admin",
        reason="Tune growth",
    )
    changed = store.simulation_rules()
    rolled_back = store.rollback_simulation_rules(
        actor_id="test-admin",
        reason="Restore previous growth",
    )
    restored = store.simulation_rules()

    assert applied["applied"] is True
    assert applied["revision"] == 2
    assert changed["rules"]["population"]["growthFactor"] == 0.12
    assert rolled_back["rolledBack"] is True
    assert rolled_back["restoredFromRevision"] == 1
    assert restored["rules"]["population"]["growthFactor"] == original["rules"]["population"]["growthFactor"]
    assert store.simulation_rules_audit()["pagination"]["total"] == 2


def test_repository_backed_store_loads_active_rules_config(tmp_path) -> None:
    repository = AlphaStateRepository(
        f"sqlite+pysqlite:///{tmp_path / 'alpha.db'}",
        create_schema=True,
    )
    store = AlphaStore(
        seed=4211,
        boot_ticks=1,
        repository=repository,
        refresh_on_read=True,
    )

    store.apply_simulation_rules(
        {"speciation": {"intervalTicks": 157}},
        actor_id="test-admin",
        reason="Tune speciation interval",
    )
    reloaded = AlphaStore(
        seed=4211,
        boot_ticks=1,
        repository=repository,
        refresh_on_read=True,
    )

    assert reloaded.simulation_rules()["rules"]["speciation"]["intervalTicks"] == 157
    assert reloaded.simulation_rules_revisions()["pagination"]["total"] == 2
