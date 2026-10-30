"""Document-type taxonomy endpoints.

Reading types serves the upload forms in both frontends ("selectable for
new transports immediately"); only admins may register new types.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import CurrentUser, Session, admin_only, is_admin
from app.models import DocumentType, User
from app.schemas import DocumentTypeCreate, DocumentTypeOut

router = APIRouter(prefix="/document-types", tags=["document-types"])

AdminCaller = Annotated[User, Depends(admin_only)]


@router.get("", response_model=list[DocumentTypeOut])
async def list_document_types(
    session: Session, caller: CurrentUser, include_inactive: bool = False
) -> list[DocumentType]:
    stmt = select(DocumentType).order_by(DocumentType.key)
    if not (include_inactive and is_admin(caller)):
        stmt = stmt.where(DocumentType.is_active.is_(True))
    return list((await session.execute(stmt)).scalars().all())


@router.post("", response_model=DocumentTypeOut, status_code=201)
async def create_document_type(
    body: DocumentTypeCreate, session: Session, caller: AdminCaller
) -> DocumentType:
    doc_type = DocumentType(**body.model_dump())
    session.add(doc_type)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Document type key already exists") from None
    await session.refresh(doc_type)
    return doc_type
