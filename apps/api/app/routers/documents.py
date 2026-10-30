"""Document collection: presigned uploads, review loop, versioned history.

Upload flow (design.md): POST creates a draft row + presigned PUT ->
client PUTs bytes to Garage -> confirm verifies the object and flips the
row to pending_review. Drivers upload only to transports assigned to them;
dispatchers act within their groups. Cancelled transports accept nothing;
completed stays open for late paperwork.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app import storage
from app.config import settings
from app.deps import (
    CurrentUser,
    Session,
    effective_scope,
    get_scoped_group_ids,
    group_in_scope,
    is_dispatcher,
    require_roles,
)
from app.document_rules import missing_required_attributes
from app.event_log import append_event
from app.models import (
    ADMIN_ROLES,
    DOC_STATUS_ACCEPTED,
    DOC_STATUS_DRAFT,
    DOC_STATUS_PENDING_REVIEW,
    DOC_STATUS_REJECTED,
    Document,
    DocumentReview,
    DocumentType,
    Transport,
    TransportDriver,
    User,
    utcnow,
)
from app.schemas import (
    DocumentAttributesUpdate,
    DocumentCreate,
    DocumentOut,
    DocumentReviewCreate,
    DocumentReviewOut,
    DocumentUploadTicket,
)

router = APIRouter(tags=["documents"])

DispatcherCaller = Annotated[User, Depends(require_roles("dispatcher", *ADMIN_ROLES))]


async def _load_documents_with_reviews(
    session: Session, documents: list[Document]
) -> list[DocumentOut]:
    if not documents:
        return []
    reviews = list(
        (
            await session.execute(
                select(DocumentReview).where(
                    DocumentReview.document_id.in_([d.id for d in documents])
                )
            )
        )
        .scalars()
        .all()
    )
    by_doc: dict[uuid.UUID, list[DocumentReviewOut]] = {}
    for review in reviews:
        by_doc.setdefault(review.document_id, []).append(DocumentReviewOut.model_validate(review))
    out: list[DocumentOut] = []
    for doc in documents:
        item = DocumentOut.model_validate(doc)
        item.reviews = sorted(by_doc.get(doc.id, []), key=lambda r: r.created_at)
        out.append(item)
    return out


async def _transport_for_caller(
    session: Session, transport_id: uuid.UUID, caller: User
) -> Transport:
    """404 outside the caller's dispatch scope; drivers must be assigned."""
    scoped = effective_scope(caller, await get_scoped_group_ids(caller, session))
    transport = await session.get(Transport, transport_id)
    if transport is None or not group_in_scope(scoped, transport.group_id):
        raise HTTPException(status_code=404, detail="Transport not found")
    if not is_dispatcher(caller):
        assignment = await session.get(TransportDriver, (transport_id, caller.id))
        if assignment is None:
            raise HTTPException(status_code=403, detail="Driver is not assigned to this transport")
    return transport


async def _document_for_caller(session: Session, document_id: uuid.UUID, caller: User) -> Document:
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await _transport_for_caller(session, doc.transport_id, caller)
    return doc


@router.post(
    "/transports/{transport_id}/documents",
    response_model=DocumentUploadTicket,
    status_code=201,
)
async def create_document(
    transport_id: uuid.UUID,
    body: DocumentCreate,
    session: Session,
    caller: CurrentUser,
) -> DocumentUploadTicket:
    transport = await _transport_for_caller(session, transport_id, caller)
    if transport.state == "cancelled":
        raise HTTPException(status_code=409, detail="Transport is cancelled")
    doc_type = await session.get(DocumentType, body.document_type_id)
    if doc_type is None or not doc_type.is_active:
        raise HTTPException(status_code=404, detail="Document type not found or inactive")

    version = 1
    if body.resubmits_document_id is not None:
        previous = await session.get(Document, body.resubmits_document_id)
        if (
            previous is None
            or previous.transport_id != transport.id
            or previous.document_type_id != doc_type.id
        ):
            raise HTTPException(status_code=409, detail="Document to resubmit does not match")
        if previous.status != DOC_STATUS_REJECTED:
            raise HTTPException(status_code=409, detail="Only rejected documents are resubmitted")
        already = await session.execute(
            select(Document).where(Document.supersedes_id == previous.id)
        )
        if already.scalars().first() is not None:
            raise HTTPException(status_code=409, detail="Document was already resubmitted")
        version = previous.version + 1

    document_id = body.id or uuid.uuid4()
    if await session.get(Document, document_id) is not None:
        raise HTTPException(status_code=409, detail="Document id already exists")

    document = Document(
        id=document_id,
        group_id=transport.group_id,
        transport_id=transport.id,
        document_type_id=doc_type.id,
        variant=doc_type.variant,
        source=body.source,
        storage_key=f"documents/{transport.id}/{document_id}/{version}",
        mime=body.mime,
        status=DOC_STATUS_DRAFT,
        version=version,
        supersedes_id=body.resubmits_document_id,
        captured_at=body.captured_at,
        created_by=caller.id,
    )
    session.add(document)
    await session.commit()
    return DocumentUploadTicket(
        document=DocumentOut.model_validate(document),
        upload_url=storage.presign_put(document.storage_key, document.mime),
        expires_in_sec=settings.presign_ttl_sec,
    )


@router.get("/transports/{transport_id}/documents", response_model=list[DocumentOut])
async def list_transport_documents(
    transport_id: uuid.UUID, session: Session, caller: CurrentUser
) -> list[DocumentOut]:
    transport = await _transport_for_caller(session, transport_id, caller)
    documents = list(
        (
            await session.execute(
                select(Document)
                .where(Document.transport_id == transport.id)
                .order_by(Document.created_at, Document.version)
            )
        )
        .scalars()
        .all()
    )
    return await _load_documents_with_reviews(session, documents)


@router.get("/documents/{document_id}/upload-url", response_model=DocumentUploadTicket)
async def refresh_upload_url(
    document_id: uuid.UUID, session: Session, caller: CurrentUser
) -> DocumentUploadTicket:
    """Fresh presigned PUT for the caller's own expired draft."""
    document = await _document_for_caller(session, document_id, caller)
    if document.created_by != caller.id:
        raise HTTPException(status_code=403, detail="Only the uploader can re-presign a draft")
    if document.status != DOC_STATUS_DRAFT:
        raise HTTPException(status_code=409, detail="Only drafts can be re-presigned")
    return DocumentUploadTicket(
        document=DocumentOut.model_validate(document),
        upload_url=storage.presign_put(document.storage_key, document.mime),
        expires_in_sec=settings.presign_ttl_sec,
    )


@router.post("/documents/{document_id}/confirm", response_model=DocumentOut)
async def confirm_document(
    document_id: uuid.UUID, session: Session, caller: CurrentUser
) -> DocumentOut:
    document = await _document_for_caller(session, document_id, caller)
    if document.created_by != caller.id:
        raise HTTPException(status_code=403, detail="Only the uploader can confirm an upload")
    if document.status != DOC_STATUS_DRAFT:
        raise HTTPException(status_code=409, detail="Only drafts can be confirmed")
    if not storage.object_exists(document.storage_key):
        raise HTTPException(status_code=409, detail="Object not uploaded yet")
    document.status = DOC_STATUS_PENDING_REVIEW
    document.confirmed_at = utcnow()
    append_event(
        session,
        event_type="document_submitted",
        transport_id=document.transport_id,
        actor_id=caller.id,
        payload={"document_id": str(document.id), "version": document.version},
    )
    await session.commit()
    await session.refresh(document)
    return DocumentOut.model_validate(document)


@router.post("/documents/{document_id}/review", response_model=DocumentOut)
async def review_document(
    document_id: uuid.UUID,
    body: DocumentReviewCreate,
    session: Session,
    caller: DispatcherCaller,
) -> DocumentOut:
    document = await _document_for_caller(session, document_id, caller)
    if document.status != DOC_STATUS_PENDING_REVIEW:
        raise HTTPException(status_code=409, detail="Only pending documents can be reviewed")
    if body.decision == "approve":
        doc_type = await session.get(DocumentType, document.document_type_id)
        if doc_type is not None:
            missing = missing_required_attributes(doc_type, document.attributes)
            if missing:
                raise HTTPException(
                    status_code=422,
                    detail=f"Required attributes missing: {', '.join(missing)}",
                )
        document.status = DOC_STATUS_ACCEPTED
    else:
        document.status = DOC_STATUS_REJECTED
    session.add(
        DocumentReview(
            document_id=document.id,
            reviewer_id=caller.id,
            decision=body.decision,
            reason=body.reason,
        )
    )
    append_event(
        session,
        event_type="document_review",
        transport_id=document.transport_id,
        actor_id=caller.id,
        payload={"document_id": str(document.id), "decision": body.decision},
    )
    await session.commit()
    await session.refresh(document)
    docs = await _load_documents_with_reviews(session, [document])
    return docs[0]


@router.patch("/documents/{document_id}/attributes", response_model=DocumentOut)
async def update_document_attributes(
    document_id: uuid.UUID,
    body: DocumentAttributesUpdate,
    session: Session,
    caller: CurrentUser,
) -> DocumentOut:
    """Manual attribute entry (OCR is MVP3); accepted versions stay immutable."""
    document = await _document_for_caller(session, document_id, caller)
    if document.status == DOC_STATUS_ACCEPTED:
        raise HTTPException(status_code=409, detail="Accepted documents are immutable")
    if document.created_by != caller.id and not is_dispatcher(caller):
        raise HTTPException(status_code=403, detail="Not the uploader or a group dispatcher")
    merged: dict[str, Any] = dict(document.attributes or {})
    merged.update(body.attributes)
    document.attributes = merged
    await session.commit()
    await session.refresh(document)
    return DocumentOut.model_validate(document)


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: uuid.UUID, session: Session, caller: CurrentUser
) -> dict[str, Any]:
    document = await _document_for_caller(session, document_id, caller)
    return {
        "url": storage.presign_get(document.storage_key),
        "expires_in_sec": settings.presign_ttl_sec,
    }
