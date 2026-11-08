import '../models/conversation.dart';
import 'local_api_client.dart';

abstract interface class ConversationRepository {
  Future<List<Conversation>> listConversations();

  Future<Conversation> createConversation(ConversationDraft draft);

  Future<ConversationWithMessages?> getConversation(String id);

  Future<Conversation> renameConversation(String id, String title);

  Future<void> deleteConversation(String id);

  Future<ConversationMessage> addMessage(
    String conversationId,
    ConversationMessageDraft draft,
  );

  Future<AiConversationResponse> chatInConversation({
    required String conversationId,
    required String modelId,
    required List<ConversationMessage> messages,
  });
}

/// Conversazione con i relativi messaggi caricati.
class ConversationWithMessages {
  const ConversationWithMessages({
    required this.conversation,
    required this.messages,
  });

  final Conversation conversation;
  final List<ConversationMessage> messages;
}

/// Servizio backend per conversazioni persistenti.
class ConversationApiService implements ConversationRepository {
  ConversationApiService({LocalApiClient? client})
    : _client = client ?? LocalApiClient();

  final LocalApiClient _client;

  @override
  Future<List<Conversation>> listConversations() async {
    final response = await _client.getJson('/api/v1/conversations');
    if (response is! List) {
      throw const FormatException('Il backend ha restituito un elenco non valido.');
    }
    return response.map((item) => Conversation.fromJson(item)).toList(growable: false);
  }

  @override
  Future<Conversation> createConversation(ConversationDraft draft) async {
    final response = await _client.postJson(
      '/api/v1/conversations',
      draft.toJson(),
    );
    if (response is! Map<String, dynamic>) {
      throw const FormatException('Risposta della conversazione non valida.');
    }
    return Conversation.fromJson(response);
  }

  @override
  Future<ConversationWithMessages?> getConversation(String id) async {
    final response = await _client.getJson('/api/v1/conversations/$id');
    if (response is! Map<String, dynamic>) {
      throw const FormatException('Dati della conversazione non validi.');
    }
    final conversation = Conversation.fromJson(response);
    final rawMessages = response['messages'];
    final messages = <ConversationMessage>[];
    if (rawMessages is List) {
      for (final item in rawMessages) {
        messages.add(ConversationMessage.fromJson(item));
      }
    }
    return ConversationWithMessages(
      conversation: conversation,
      messages: messages,
    );
  }

  @override
  Future<Conversation> renameConversation(String id, String title) async {
    final response = await _client.putJson(
      '/api/v1/conversations/$id/title',
      {'title': title},
    );
    if (response is! Map<String, dynamic>) {
      throw const FormatException('Risposta della rinomina non valida.');
    }
    return Conversation.fromJson(response);
  }

  @override
  Future<void> deleteConversation(String id) async {
    await _client.delete('/api/v1/conversations/$id');
  }

  @override
  Future<ConversationMessage> addMessage(
    String conversationId,
    ConversationMessageDraft draft,
  ) async {
    final response = await _client.postJson(
      '/api/v1/conversations/$conversationId/messages',
      draft.toJson(),
    );
    if (response is! Map<String, dynamic>) {
      throw const FormatException('Risposta del messaggio non valida.');
    }
    return ConversationMessage.fromJson(response);
  }

  @override
  Future<AiConversationResponse> chatInConversation({
    required String conversationId,
    required String modelId,
    required List<ConversationMessage> messages,
  }) async {
    final response = await _client.postJson(
      '/api/v1/conversations/$conversationId/chat',
      {
        'model_id': modelId,
        'messages': messages
            .map((message) => {'role': message.role, 'content': message.content})
            .toList(growable: false),
      },
    );
    if (response is! Map<String, dynamic>) {
      throw const FormatException('Risposta della chat non valida.');
    }
    return AiConversationResponse.fromJson(response);
  }
}
