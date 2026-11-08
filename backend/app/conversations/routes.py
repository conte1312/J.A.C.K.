from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.ai.schemas import ChatInput
from app.ai.service import AiServiceError
from app.conversations.repository import ConversationNotFoundError
from app.conversations.schemas import (
    ConversationContextRead,
    ConversationMessage,
    ConversationMessageWrite,
    ConversationRead,
    ConversationRename,
    ConversationWrite,
)
from app.conversations.service import ConversationService
from app.memory.repository import MemoryRepository

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conversation_repository(request: Request) -> ConversationService:
    return request.app.state.conversation_service


Service = Annotated[ConversationService, Depends(get_conversation_repository)]


def get_memory_repository(request: Request) -> MemoryRepository:
    return request.app.state.memory_repository


MemoryRepo = Annotated[MemoryRepository, Depends(get_memory_repository)]


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Conversation not found",
    )


@router.get("", response_model=list[ConversationRead])
def list_conversations(service: Service) -> list[dict[str, object]]:
    return service.list_conversations()


@router.post(
    "",
    response_model=ConversationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    payload: ConversationWrite, service: Service
) -> dict[str, object]:
    try:
        return service.create_conversation(
            title=payload.title,
            provider_id=payload.provider_id,
            model_id=payload.model_id,
            metadata=payload.metadata,
        )
    except AiServiceError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail={"code": error.code, "message": error.message},
        ) from error


@router.get("/{conversation_id}", response_model=ConversationContextRead)
def get_conversation(
    conversation_id: str, service: Service
) -> dict[str, object]:
    conversation = service.get_conversation(conversation_id)
    if conversation is None:
        raise _not_found()
    return {
        "conversation": {
            "id": conversation["id"],
            "title": conversation["title"],
            "created_at": conversation["created_at"],
            "updated_at": conversation["updated_at"],
            "provider_id": conversation["provider_id"],
            "model_id": conversation["model_id"],
            "metadata": conversation["metadata"],
            "message_count": conversation["message_count"],
        },
        "messages": conversation.get("messages", []),
    }


@router.put("/{conversation_id}/title", response_model=ConversationRead)
def rename_conversation(
    conversation_id: str,
    payload: ConversationRename,
    service: Service,
) -> dict[str, object]:
    try:
        updated = service.rename_conversation(conversation_id, payload.title)
    except ConversationNotFoundError:
        raise _not_found()
    if updated is None:
        raise _not_found()
    return updated


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str, service: Service
) -> Response:
    if not service.delete_conversation(conversation_id):
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{conversation_id}/messages",
    response_model=ConversationMessage,
    status_code=status.HTTP_201_CREATED,
)
def add_conversation_message(
    conversation_id: str,
    payload: ConversationMessageWrite,
    service: Service,
) -> dict[str, object]:
    try:
        message = service.add_message(
            conversation_id=conversation_id,
            role=payload.role.value,
            content=payload.content,
            is_demo=payload.is_demo,
            provider_label=payload.provider_label,
        )
    except ConversationNotFoundError:
        raise _not_found()
    if message is None:
        raise _not_found()
    return message


@router.get("/{conversation_id}/context", response_model=ConversationContextRead)
def get_conversation_context(
    conversation_id: str,
    service: Service,
    q: str = "",
) -> dict[str, object]:
    conversation = service.get_conversation(conversation_id)
    if conversation is None:
        raise _not_found()
    context = service.build_ai_context(
        conversation_id=conversation_id,
        user_message=q,
        model_id=conversation.get("model_id"),
    )
    return {
        "conversation": {
            "id": conversation["id"],
            "title": conversation["title"],
            "created_at": conversation["created_at"],
            "updated_at": conversation["updated_at"],
            "provider_id": conversation["provider_id"],
            "model_id": conversation["model_id"],
            "metadata": conversation["metadata"],
            "message_count": conversation["message_count"],
        },
        "messages": conversation.get("messages", []),
        "context_memories": context.get("context_memories", []),
        "context_blocks": context.get("context_blocks", []),
        "model_id": context.get("model_id"),
    }


@router.post("/{conversation_id}/chat")
async def chat_in_conversation(
    conversation_id: str,
    payload: ChatInput,
    service: Service,
    memory_repository: MemoryRepo,
) -> dict[str, str]:
    try:
        return await service.chat_with_context(
            conversation_id=conversation_id,
            model_id=payload.model_id,
            messages=[turn.model_dump() for turn in payload.messages],
            memory_repository=memory_repository,
        )
    except AiServiceError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
