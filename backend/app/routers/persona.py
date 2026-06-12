from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.rbac import require_role
from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.models.persona import BrandPersona
from app.repositories.brands import get_brand
from app.schemas.persona import PersonaContent, PersonaOut

router = APIRouter(prefix="/brands/{brand_id}/persona", tags=["persona"])


def _require_brand(db: Session, brand_id: str, org_id: str):
    brand = get_brand(db, brand_id, org_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="brand not found")
    return brand


@router.get("", response_model=PersonaOut)
def get_persona(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PersonaOut:
    _require_brand(db, brand_id, current_user.org_id)
    persona = db.query(BrandPersona).filter(BrandPersona.brand_id == brand_id).first()
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="persona not found")
    return PersonaOut.model_validate(persona)


@router.put("", response_model=PersonaOut)
def upsert_persona(
    brand_id: str,
    payload: PersonaContent,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PersonaOut:
    require_role(current_user.role, {"admin", "team_member"})
    _require_brand(db, brand_id, current_user.org_id)

    persona = db.query(BrandPersona).filter(BrandPersona.brand_id == brand_id).first()
    data = payload.model_dump()
    if persona:
        for key, value in data.items():
            setattr(persona, key, value)
    else:
        persona = BrandPersona(brand_id=brand_id, **data)
        db.add(persona)
    db.commit()
    db.refresh(persona)
    return PersonaOut.model_validate(persona)