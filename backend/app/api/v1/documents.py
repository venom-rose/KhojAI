import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_optional_current_user
from backend.app.database.session import get_db, async_session_factory
from backend.app.models.user import User
from backend.app.schemas.document import (
    DocumentAskIn,
    DocumentAskOut,
    DocumentDetailOut,
    DocumentListOut,
    DocumentOut,
    DocumentSearchIn,
    DocumentSearchOut,
)
from backend.app.services.document_service import document_service

router = APIRouter(prefix="/documents", tags=["Document Library & RAG"])


async def _run_background_processing(document_id: uuid.UUID, destination_id: Optional[uuid.UUID]):
    """Background worker task to process large documents asynchronously."""
    async with async_session_factory() as session:
        await document_service.process_document(
            db=session,
            document_id=document_id,
            destination_id=destination_id,
        )


@router.post(
    "",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest document",
    description="Securely upload a travel document (PDF, TXT, MD, CSV, JSON) to validate, store, chunk, and embed.",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Physical document file"),
    title: Optional[str] = Form(None, description="Optional custom document title"),
    document_type: str = Form("guide", description="Document category (guide, advisory, field_note, itinerary, report)"),
    destination_id: Optional[uuid.UUID] = Form(None, description="Associated destination ID"),
    process_async: bool = Query(False, description="Process extraction and embedding in background"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None

    # 1. Validate & Store
    doc = await document_service.create_document(
        db=db,
        upload_file=file,
        title=title,
        document_type=document_type,
        destination_id=destination_id,
        user_id=user_id,
    )

    # 2. Extract, clean, chunk, embed
    if process_async:
        background_tasks.add_task(_run_background_processing, doc.id, destination_id)
        doc.status = "processing"
        await db.commit()
        await db.refresh(doc)
    else:
        doc = await document_service.process_document(
            db=db,
            document_id=doc.id,
            destination_id=destination_id,
        )

    return DocumentOut.model_validate(doc)


@router.get(
    "",
    response_model=DocumentListOut,
    summary="Retrieve document library",
    description="List active documents with optional status filtering and title search.",
)
async def list_documents(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None, description="Filter by status: uploaded, processing, ready, failed"),
    search: Optional[str] = Query(default=None, description="Search document title"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    return await document_service.list_documents(
        db=db,
        user_id=user_id,
        limit=limit,
        offset=offset,
        status_filter=status,
        search=search,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailOut,
    summary="Retrieve document details",
    description="Fetch document details including full extracted text and indexed chunks.",
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    return await document_service.get_document_detail(
        db=db, document_id=document_id, user_id=user_id
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document",
    description="Permanently delete a document, its vector chunks, and the physical file on disk.",
)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    await document_service.delete_document(
        db=db, document_id=document_id, user_id=user_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{document_id}/reprocess",
    response_model=DocumentOut,
    summary="Reprocess document",
    description="Re-extract, clean, chunk, and re-embed an existing document.",
)
async def reprocess_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    process_async: bool = Query(False, description="Reprocess in background"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    doc = await document_service.get_document_or_404(db, document_id, user_id=user_id)

    if process_async:
        background_tasks.add_task(_run_background_processing, doc.id, None)
        doc.status = "processing"
        await db.commit()
        await db.refresh(doc)
    else:
        doc = await document_service.process_document(db=db, document_id=doc.id)

    return DocumentOut.model_validate(doc)


@router.post(
    "/search",
    response_model=DocumentSearchOut,
    summary="Semantic vector search",
    description="Perform semantic cosine similarity retrieval over ingested knowledge chunks.",
)
async def search_documents(
    payload: DocumentSearchIn,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    results = await document_service.semantic_search(
        db=db,
        query=payload.query,
        top_k=payload.top_k,
        document_id=payload.document_id,
        user_id=user_id,
        min_similarity=payload.min_similarity,
    )
    return DocumentSearchOut(
        query=payload.query,
        results=results,
        count=len(results),
    )


@router.post(
    "/query",
    response_model=DocumentAskOut,
    summary="Ask-from-document (RAG)",
    description="Answer questions grounded in retrieved document evidence.",
)
async def ask_documents(
    payload: DocumentAskIn,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    return await document_service.ask_document(
        db=db,
        query=payload.query,
        top_k=payload.top_k,
        document_id=payload.document_id,
        user_id=user_id,
        model=payload.model,
    )


@router.post(
    "/{document_id}/query",
    response_model=DocumentAskOut,
    summary="Ask a specific document (RAG)",
    description="Answer questions grounded specifically within a designated document.",
)
async def ask_single_document(
    document_id: uuid.UUID,
    payload: DocumentAskIn,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    return await document_service.ask_document(
        db=db,
        query=payload.query,
        top_k=payload.top_k,
        document_id=document_id,
        user_id=user_id,
        model=payload.model,
    )
