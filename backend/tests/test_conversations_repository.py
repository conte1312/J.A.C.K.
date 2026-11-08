from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from app.conversations.repository import ConversationNotFoundError, ConversationRepository


class ConversationRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(
            prefix="jack-conversations-test-"
        )
        self.database_path = Path(self.temporary_directory.name) / "test.sqlite3"
        self.repository = ConversationRepository(self.database_path)
        self.repository.initialize()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_create_and_list_conversations(self) -> None:
        first = self.repository.create_conversation(
            title="Prima conversazione",
            provider_id="nvidia",
            model_id="nvidia/nemotron-3.5-lightning-30b-a3b",
        )
        time.sleep(0.01)
        second = self.repository.create_conversation(
            title="Seconda conversazione",
            provider_id="nvidia",
            model_id="nvidia/nemotron-3.5-bolt-e4b",
        )

        conversations = self.repository.list_conversations()
        self.assertEqual(len(conversations), 2)
        self.assertEqual(conversations[0]["title"], "Seconda conversazione")
        self.assertEqual(conversations[1]["title"], "Prima conversazione")
        self.assertEqual(conversations[0]["message_count"], 0)
        self.assertEqual(conversations[1]["message_count"], 0)
        self.assertEqual(first["provider_id"], "nvidia")
        self.assertEqual(first["model_id"], "nvidia/nemotron-3.5-lightning-30b-a3b")

    def test_get_conversation_with_messages(self) -> None:
        conversation = self.repository.create_conversation(title="Chat")
        message = self.repository.add_message(
            conversation_id=conversation["id"],
            role="user",
            content="Ciao J.A.C.K.",
        )
        self.assertEqual(message["role"], "user")
        self.assertEqual(message["content"], "Ciao J.A.C.K.")
        self.assertFalse(message["is_demo"])

        fetched = self.repository.get_conversation_with_messages(conversation["id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["title"], "Chat")
        self.assertEqual(len(fetched["messages"]), 1)
        self.assertEqual(fetched["messages"][0]["content"], "Ciao J.A.C.K.")
        self.assertEqual(fetched["message_count"], 1)

    def test_update_and_delete_conversation(self) -> None:
        conversation = self.repository.create_conversation(title="Da rinominare")
        updated = self.repository.update_conversation_title(
            conversation["id"], "Rinominata"
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated["title"], "Rinominata")

        deleted = self.repository.delete_conversation(conversation["id"])
        self.assertTrue(deleted)
        self.assertIsNone(self.repository.get_conversation(conversation["id"]))
        self.assertFalse(
            self.repository.delete_conversation(conversation["id"])
        )

    def test_get_missing_conversation_returns_none(self) -> None:
        self.assertIsNone(self.repository.get_conversation("inesistente"))
        self.assertIsNone(
            self.repository.get_conversation_with_messages("inesistente")
        )

    def test_add_message_to_missing_conversation_returns_none(self) -> None:
        result = self.repository.add_message(
            conversation_id="inesistente",
            role="user",
            content="testo",
        )
        self.assertIsNone(result)

    def test_conversations_ordered_by_recent_activity(self) -> None:
        first = self.repository.create_conversation(title="Prima")
        time.sleep(0.01)
        second = self.repository.create_conversation(title="Seconda")
        time.sleep(0.01)
        self.repository.add_message(
            conversation_id=first["id"], role="user", content="messaggio nella prima"
        )
        conversations = self.repository.list_conversations()
        # La prima ha un messaggio piu recente, quindi deve apparire prima.
        self.assertEqual(conversations[0]["id"], first["id"])
        self.assertEqual(conversations[0]["message_count"], 1)
        self.assertEqual(conversations[1]["message_count"], 0)

    def test_database_file_is_private(self) -> None:
        import stat

        mode = stat.S_IMODE(self.database_path.stat().st_mode)
        self.assertEqual(mode, 0o600)


if __name__ == "__main__":
    unittest.main()
