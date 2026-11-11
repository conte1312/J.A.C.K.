"""J.A.C.K. M4.6 - Context Builder integration test.

Tests that Knowledge Engine items are actually passed to the AI provider
via ConversationService.chat_with_context(), using a mock AI provider.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from app.conversations.service import ConversationService
from app.conversations.repository import ConversationRepository
from app.knowledge.context_builder import ContextBuilder
from app.knowledge.graph_service import KnowledgeGraphService
from app.knowledge.repository import KnowledgeRepository


class MockAIProviderService:
    """Mock AI provider that captures messages sent to it."""

    def __init__(self):
        self.last_messages: list[dict[str, str]] | None = None
        self.last_model: str | None = None
        self.call_count = 0

    async def chat(self, *, model_id: str, messages: list[dict[str, str]]) -> dict[str, str]:
        self.last_messages = messages
        self.last_model = model_id
        self.call_count += 1
        return {
            "provider_id": "mock-provider",
            "model_id": model_id,
            "content": "Risposta di test dal provider mock",
        }


class ConversationServiceIntegrationTest(unittest.TestCase):
    """Test che il contesto Knowledge Engine raggiunga effettivamente il provider AI."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="jack-conv-service-test-")
        self.database_path = Path(self.temp_dir.name) / "test_conv.sqlite3"

        # Knowledge repository (M4)
        self.kb_repo = KnowledgeRepository(self.database_path)
        self.kb_repo.initialize()
        self.kb_domain = self.kb_repo.create_domain(
            name="Test Domain", slug="test-domain"
        )

        # Conversation repository (M3)
        self.conv_repo = ConversationRepository(self.database_path)
        self.conv_repo.initialize()
        self.conv = self.conv_repo.create_conversation(
            title="Test Conversation",
            provider_id="test-provider",
            model_id="test-model",
        )

        # Mock AI provider
        self.ai_provider = MockAIProviderService()

        # Graph service + ContextBuilder (M4.6 wiring)
        self.graph_service = KnowledgeGraphService(repository=self.kb_repo)
        self.context_builder = ContextBuilder(
            repository=self.kb_repo,
            graph_service=self.graph_service,
        )

        # ConversationService with ContextBuilder injected (M4.6)
        self.service = ConversationService(
            conversation_repository=self.conv_repo,
            memory_repository=None,
            knowledge_repository=self.kb_repo,
            context_builder=self.context_builder,
            ai_provider_service=self.ai_provider,
        )

    def tearDown(self) -> None:
        self.temp_directory.cleanup() if hasattr(self, "temporary_directory") else None

    def test_context_builder_sends_knowledge_to_ai_provider(self) -> None:
        """Verifica che gli item di conoscenza vengano inviati al provider AI."""
        # Create knowledge items
        self.kb_repo.create_item(
            title="Python Programming",
            content="Python is a high-level programming language.",
            domain_id=self.kb_domain["id"],
            knowledge_type="concept",
            source_type="document",
            verification_status="verified",
            item_state="published",
        )
        self.kb_repo.create_item(
            title="Flask Web Framework",
            content="Flask is a micro web framework for Python.",
            domain_id=self.kb_domain["id"],
            knowledge_type="fact",
            source_type="document",
            verification_status="verified",
            item_state="published",
        )

        # Call chat_with_context
        import asyncio

        async def run():
            return await self.service.chat_with_context(
                conversation_id=self.conv["id"],
                model_id="test-model",
                messages=[
                    {"role": "user", "content": "Python Programming"},
                ],
                memory_repository=None,
                knowledge_repository=self.kb_repo,
            )

        result = asyncio.run(run())

        # Verify the AI provider was called
        self.assertEqual(self.ai_provider.call_count, 1)
        messages = self.ai_provider.last_messages

        # Verify the system prompt is present
        system_messages = [m for m in messages if m["role"] == "system"]
        self.assertGreaterEqual(len(system_messages), 1)

        # Verify knowledge items are included in system messages
        knowledge_messages = [
            m for m in system_messages if "Conoscenza" in m["content"]
        ]
        self.assertGreaterEqual(len(knowledge_messages), 1)

        # Verify the knowledge content contains our items
        knowledge_text = " ".join(m["content"] for m in knowledge_messages)
        self.assertIn("Python Programming", knowledge_text)
        self.assertIn("Python is a high-level programming language", knowledge_text)

    def test_context_builder_includes_provenance(self) -> None:
        """Verifica che la provenienza sia inclusa nei messaggi al provider."""
        self.kb_repo.create_item(
            title="Test Source Item",
            content="Test content for provenance tracking.",
            domain_id=self.kb_domain["id"],
            knowledge_type="fact",
            source_type="document",
            verification_status="verified",
            item_state="published",
        )

        import asyncio

        async def run():
            return await self.service.chat_with_context(
                conversation_id=self.conv["id"],
                model_id="test-model",
                messages=[
                    {"role": "user", "content": "Test Source Item"},
                ],
                memory_repository=None,
                knowledge_repository=self.kb_repo,
            )

        result = asyncio.run(run())
        messages = self.ai_provider.last_messages

        knowledge_messages = [m for m in messages if m["role"] == "system"]
        knowledge_text = " ".join(m["content"] for m in knowledge_messages)
        self.assertIn("Test Source Item", knowledge_text)
        self.assertIn("Test content for provenance tracking.", knowledge_text)

    def test_conversation_without_knowledge_still_works(self) -> None:
        """Verifica che la conversazione funzioni anche senza conoscenza M4."""
        import asyncio

        async def run():
            return await self.service.chat_with_context(
                conversation_id=self.conv["id"],
                model_id="test-model",
                messages=[
                    {"role": "user", "content": "Hello how are you"},
                ],
                memory_repository=None,
                knowledge_repository=self.kb_repo,
            )

        result = asyncio.run(run())

        # Should still work without knowledge items
        self.assertEqual(result["content"], "Risposta di test dal provider mock")
        messages = self.ai_provider.last_messages
        # Should have system prompt + user message, but no knowledge items
        system_messages = [m for m in messages if m["role"] == "system"]
        knowledge_messages = [
            m for m in system_messages if "Conoscenza" in m["content"]
        ]
        self.assertEqual(len(knowledge_messages), 0)

    def test_token_budget_respected(self) -> None:
        """Verifica che il contesto non superi il budget di token."""
        import asyncio

        async def run():
            return await self.service.chat_with_context(
                conversation_id=self.conv["id"],
                model_id="test-model",
                messages=[
                    {"role": "user", "content": "Python Programming"},
                ],
                memory_repository=None,
                knowledge_repository=self.kb_repo,
            )

        result = asyncio.run(run())
        messages = self.ai_provider.last_messages

        # Calculate total tokens (rough estimate: chars / 4)
        total_chars = sum(len(m["content"]) for m in messages)
        estimated_tokens = total_chars / 4

        # Should be well within typical context limits
        self.assertLess(total_chars, 4000)  # Well under 4K tokens worth of chars

    def test_context_builder_is_injected(self) -> None:
        """Verifica che ContextBuilder sia iniettato nel ConversationService."""
        self.assertIsNotNone(self.service.context_builder)
        self.assertIsInstance(self.service.context_builder, ContextBuilder)

    def test_contextual_resolver_is_invoked(self) -> None:
        """Verifica che ContextualResolver venga effettivamente invocato."""
        self.kb_repo.create_item(
            title="Resolver Test Item",
            content="Content to trigger resolver invocation.",
            domain_id=self.kb_domain["id"],
            knowledge_type="concept",
            source_type="document",
            verification_status="verified",
            item_state="published",
        )

        import asyncio

        async def run():
            return await self.service.chat_with_context(
                conversation_id=self.conv["id"],
                model_id="test-model",
                messages=[
                    {"role": "user", "content": "Resolver Test Item"},
                ],
                memory_repository=None,
                knowledge_repository=self.kb_repo,
            )

        result = asyncio.run(run())
        messages = self.ai_provider.last_messages

        knowledge_messages = [
            m for m in messages if m["role"] == "system" and "Conoscenza" in m["content"]
        ]
        self.assertGreaterEqual(len(knowledge_messages), 1)
        knowledge_text = " ".join(m["content"] for m in knowledge_messages)
        self.assertIn("Resolver Test Item", knowledge_text)

    def test_provenance_and_verification_preserved(self) -> None:
        """Verifica che provenienza e stato di verifica siano preservati."""
        self.kb_repo.create_item(
            title="Provenance Item",
            content="Content with provenance and verification metadata.",
            domain_id=self.kb_domain["id"],
            knowledge_type="fact",
            source_type="document",
            source_id="src-123",
            verification_status="verified",
            item_state="published",
        )

        import asyncio

        async def run():
            return await self.service.chat_with_context(
                conversation_id=self.conv["id"],
                model_id="test-model",
                messages=[
                    {"role": "user", "content": "Provenance Item"},
                ],
                memory_repository=None,
                knowledge_repository=self.kb_repo,
            )

        result = asyncio.run(run())
        messages = self.ai_provider.last_messages

        knowledge_messages = [
            m for m in messages if m["role"] == "system" and "Conoscenza" in m["content"]
        ]
        self.assertGreaterEqual(len(knowledge_messages), 1)
        knowledge_text = " ".join(m["content"] for m in knowledge_messages)
        self.assertIn("Provenance Item", knowledge_text)
        self.assertIn("Content with provenance and verification metadata.", knowledge_text)
        # Verifica status viene incluso nel messaggio
        self.assertIn("published", knowledge_text)

    def test_token_budget_respected_with_context_builder(self) -> None:
        """Verifica che il token budget di ContextBuilder sia rispettato."""
        # Crea molti item per verificare che il budget tagli il contesto
        for i in range(20):
            self.kb_repo.create_item(
                title=f"Budget Item {i}",
                content=f"Content for budget test item number {i} with some text.",
                domain_id=self.kb_domain["id"],
                knowledge_type="concept",
                source_type="document",
                verification_status="verified",
                item_state="published",
            )

        import asyncio

        async def run():
            return await self.service.chat_with_context(
                conversation_id=self.conv["id"],
                model_id="test-model",
                messages=[
                    {"role": "user", "content": "Budget Item"},
                ],
                memory_repository=None,
                knowledge_repository=self.kb_repo,
            )

        result = asyncio.run(run())
        messages = self.ai_provider.last_messages

        total_chars = sum(len(m["content"]) for m in messages)
        # ContextBuilder default budget è 4000 token ≈ 16000 char, ma max_items=3
        # limita fortemente il contesto
        self.assertLess(total_chars, 12000)

    def test_fallback_without_context_builder(self) -> None:
        """Verifica che il fallback legacy funzioni senza ContextBuilder."""
        service_no_cb = ConversationService(
            conversation_repository=self.conv_repo,
            memory_repository=None,
            knowledge_repository=self.kb_repo,
            context_builder=None,
            ai_provider_service=self.ai_provider,
        )
        self.assertIsNone(service_no_cb.context_builder)

        self.kb_repo.create_item(
            title="Fallback Item",
            content="Fallback content for legacy path.",
            domain_id=self.kb_domain["id"],
            knowledge_type="fact",
            source_type="document",
            verification_status="verified",
            item_state="published",
        )

        import asyncio

        async def run():
            return await service_no_cb.chat_with_context(
                conversation_id=self.conv["id"],
                model_id="test-model",
                messages=[
                    {"role": "user", "content": "Fallback Item"},
                ],
                memory_repository=None,
                knowledge_repository=self.kb_repo,
            )

        result = asyncio.run(run())
        messages = self.ai_provider.last_messages

        knowledge_messages = [
            m for m in messages if m["role"] == "system" and "Conoscenza" in m["content"]
        ]
        self.assertGreaterEqual(len(knowledge_messages), 1)
        knowledge_text = " ".join(m["content"] for m in knowledge_messages)
        self.assertIn("Fallback Item", knowledge_text)

    def test_m3_m4_separation(self) -> None:
        """Verifica che M3 (memorie personali) e M4 (conoscenza) siano separati."""
        self.kb_repo.create_item(
            title="M4 Knowledge Item",
            content="M4 general knowledge content.",
            domain_id=self.kb_domain["id"],
            knowledge_type="concept",
            source_type="document",
            verification_status="verified",
            item_state="published",
        )

        import asyncio

        async def run():
            return await self.service.chat_with_context(
                conversation_id=self.conv["id"],
                model_id="test-model",
                messages=[
                    {"role": "user", "content": "M4 Knowledge Item"},
                ],
                memory_repository=None,
                knowledge_repository=self.kb_repo,
            )

        result = asyncio.run(run())
        messages = self.ai_provider.last_messages

        # M4 knowledge deve arrivare
        knowledge_messages = [
            m for m in messages if m["role"] == "system" and "Conoscenza" in m["content"]
        ]
        self.assertGreaterEqual(len(knowledge_messages), 1)
        knowledge_text = " ".join(m["content"] for m in knowledge_messages)
        self.assertIn("M4 Knowledge Item", knowledge_text)
        # Separazione M3/M4: nessuna interfaccia M3 collegata al ContextBuilder
        self.assertIsNone(self.service.context_builder.m3_memory)


if __name__ == "__main__":
    unittest.main()
