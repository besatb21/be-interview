from pathlib import Path
from typing import Generator
from unittest.mock import patch
from uuid import uuid4
from fastapi import status
import alembic.command
import alembic.config
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlmodel import select

from app.db import get_database_session
from app.main import app
from app.models import Organisation, Location

_ALEMBIC_INI_PATH = Path(__file__).parent.parent / "alembic.ini"


@pytest.fixture()
def test_client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def apply_alembic_migrations() -> Generator[None, None, None]:
    # Creates test database per test function
    test_db_file_name = f"test_{uuid4()}.db"
    database_path = Path(test_db_file_name)
    try:
        test_db_url = f"sqlite:///{test_db_file_name}"
        alembic_cfg = alembic.config.Config(_ALEMBIC_INI_PATH)
        alembic_cfg.attributes["sqlalchemy_url"] = test_db_url
        alembic.command.upgrade(alembic_cfg, "head")
        test_engine = create_engine(test_db_url, echo=True)
        with patch("app.db.get_engine") as mock_engine:
            mock_engine.return_value = test_engine
            yield
    finally:
        database_path.unlink(missing_ok=True)


def test_organisation_endpoints(test_client: TestClient) -> None:
    list_of_organisation_names_to_create = ["organisation_a", "organisation_b", "organisation_c"]

    # Validate that organisations do not exist in database
    with get_database_session() as database_session:
        organisations_before = database_session.query(Organisation).all()
        database_session.expunge_all()
    assert len(organisations_before) == 0

    # Create organisations
    for organisation_name in list_of_organisation_names_to_create:
        response = test_client.post("/api/organisations/create", json={"name": organisation_name})
        assert response.status_code == status.HTTP_200_OK

    # Validate that organisations exist in database
    with get_database_session() as database_session:
        organisations_after = database_session.query(Organisation).all()
        database_session.expunge_all()
    created_organisation_names = set(organisation.name for organisation in organisations_after)
    assert created_organisation_names == set(list_of_organisation_names_to_create)

    # Validate that created organisations can be retried via API
    response = test_client.get("/api/organisations")
    organisations = set(organisation["name"] for organisation in response.json())
    assert set(organisations) == created_organisation_names


def test_organisation_locations_endpoints(test_client: TestClient) -> None:
    list_of_locations = [{"location_name": "location1",
                          "organisation_id": 1,
                          "longitude": 0,
                          "latitude": 0}, {"location_name": "location2",
                                           "organisation_id": 2,
                                           "longitude": 0,
                                           "latitude": 0}, {"location_name": "location3",
                                                            "organisation_id": 1,
                                                            "longitude": 0,
                                                            "latitude": 0}, ]

    with get_database_session() as database_session:
        locations_before = database_session.query(Location).all()
        database_session.expunge_all()
    assert len(locations_before) == 0

    list_of_organisation_names_to_create = ["organisation_a", "organisation_b"]

    for organisation_name in list_of_organisation_names_to_create:
        response = test_client.post("/api/organisations/create", json={"name": organisation_name})
        assert response.status_code == status.HTTP_200_OK

    for location in list_of_locations:
        response = test_client.post("/api/organisations/create/locations", json=location)
        assert response.status_code == status.HTTP_200_OK

    # Validate that organisations exist in database
    with get_database_session() as database_session:
        organisation_locations_after = database_session.exec(
            select(Location).where(Location.organisation_id == 1)).all()
        database_session.expunge_all()

    response = test_client.get(f"/api/organisations/1/locations")
    locations_name = set(x["location_name"] for x in response.json())

    for el in zip(organisation_locations_after, locations_name):
        assert el[0].location_name == el[1]
