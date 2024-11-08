from typing import Annotated

from fastapi import APIRouter, HTTPException, status, Depends, Path
from sqlmodel import select, Session, and_

from app.db import get_db
from app.models import Location, Organisation, CreateOrganisation, CreateLocation, BoundingBox

router = APIRouter()


@router.post("/create", response_model=Organisation)
def create_organisation(create_organisation: CreateOrganisation, session: Session = Depends(get_db)) -> Organisation:
    """Create an organisation."""
    organisation = Organisation(name=create_organisation.name)
    session.add(organisation)
    session.commit()
    session.refresh(organisation)
    return organisation


@router.get("/", response_model=list[Organisation])
def get_organisations(session: Session = Depends(get_db)) -> list[Organisation]:
    """
    Get all organisations.
    """
    organisations = session.exec(select(Organisation)).all()
    return organisations


@router.get("/{organisation_id}", response_model=Organisation)
def get_organisation(organisation_id: int, session: Session = Depends(get_db)) -> Organisation:
    """
    Get an organisation by id.
    """
    organisation = session.get(Organisation, organisation_id)
    if organisation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return organisation


@router.post("/create/locations")
def create_location(location: CreateLocation, session: Session = Depends(get_db)) -> Location:
    location = Location(location_name=location.location_name,
                        latitude=location.latitude,
                        longitude=location.longitude,
                        organisation_id=location.organisation_id,
                        )
    session.add(location)
    session.commit()
    session.refresh(location)
    return location


@router.get("/{organisation_id}/locations")
def get_organisation_locations(organisation_id: int, q: Annotated[BoundingBox | None,Path()] = None,
                               session: Session = Depends(get_db)):
    if q:
        organisation_locations = session.exec(select(Location).where(and_(Location.organisation_id == organisation_id,
                                                                          Location.latitude <= q.x_max,
                                                                          Location.latitude >= q.x_min,
                                                                          Location.longitude <= q.y_max,
                                                                          Location.longitude >= q.y_min)))
    else:
        organisation_locations = session.exec(select(Location).where(Location.organisation_id == organisation_id))

    result = []

    for location in organisation_locations:
        result.append({"location_name": location.location_name, "location_longitude": location.longitude,
                       "location_latitude": location.latitude})
    return result
