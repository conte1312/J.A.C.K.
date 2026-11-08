/// Un messaggio appartenente a una conversazione persistente.
class ConversationMessage {
  const ConversationMessage({
    required this.id,
    required this.conversationId,
    required this.role,
    required this.content,
    required this.createdAt,
    this.isDemo = false,
    this.providerLabel,
  });

  final String id;
  final String conversationId;
  final String role; // 'user', 'assistant', 'system'
  final String content;
  final DateTime createdAt;
  final bool isDemo;
  final String? providerLabel;

  bool get isUser => role == 'user';
  bool get isAssistant => role == 'assistant';

  factory ConversationMessage.fromJson(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Formato del messaggio non valido.');
    }
    final id = value['id'];
    final conversationId = value['conversation_id'];
    final role = value['role'];
    final content = value['content'];
    final createdAt = value['created_at'];
    final isDemo = value['is_demo'] ?? false;
    final providerLabel = value['provider_label'];
    if (id is! String ||
        conversationId is! String ||
        role is! String ||
        content is! String ||
        createdAt is! String) {
      throw const FormatException('Campi del messaggio non validi.');
    }
    return ConversationMessage(
      id: id,
      conversationId: conversationId,
      role: role,
      content: content,
      createdAt: DateTime.parse(createdAt).toUtc(),
      isDemo: isDemo,
      providerLabel: providerLabel as String?,
    );
  }

  Map<String, Object?> toJson() => {
    'id': id,
    'conversation_id': conversationId,
    'role': role,
    'content': content,
    'created_at': createdAt.toIso8601String(),
    'is_demo': isDemo,
    'provider_label': providerLabel,
  };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ConversationMessage &&
          runtimeType == other.runtimeType &&
          id == other.id;

  @override
  int get hashCode => id.hashCode;
}

/// Una conversazione persistente con i suoi metadati.
class Conversation {
  const Conversation({
    required this.id,
    required this.title,
    required this.createdAt,
    required this.updatedAt,
    this.providerId,
    this.modelId,
    this.metadata = const {},
    this.messageCount = 0,
  });

  final String id;
  final String title;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? providerId;
  final String? modelId;
  final Map<String, Object?> metadata;
  final int messageCount;

  factory Conversation.fromJson(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Formato della conversazione non valido.');
    }
    final id = value['id'];
    final title = value['title'];
    final createdAt = value['created_at'];
    final updatedAt = value['updated_at'];
    final providerId = value['provider_id'];
    final modelId = value['model_id'];
    final rawMetadata = value['metadata'] ?? const <String, dynamic>{};
    final messageCount = value['message_count'] ?? 0;
    if (id is! String || title is! String || createdAt is! String || updatedAt is! String) {
      throw const FormatException('Campi della conversazione non validi.');
    }
    final metadata = <String, Object?>{};
    if (rawMetadata is Map) {
      rawMetadata.forEach((key, value) {
        if (key is String) {
          metadata[key] = value;
        }
      });
    }
    return Conversation(
      id: id,
      title: title,
      createdAt: DateTime.parse(createdAt).toUtc(),
      updatedAt: DateTime.parse(updatedAt).toUtc(),
      providerId: providerId as String?,
      modelId: modelId as String?,
      metadata: metadata,
      messageCount: messageCount is int ? messageCount : 0,
    );
  }

  Map<String, Object?> toJson() => {
    'id': id,
    'title': title,
    'created_at': createdAt.toIso8601String(),
    'updated_at': updatedAt.toIso8601String(),
    'provider_id': providerId,
    'model_id': modelId,
    'metadata': metadata,
    'message_count': messageCount,
  };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Conversation && runtimeType == other.runtimeType && id == other.id;

  @override
  int get hashCode => id.hashCode;
}

/// Input per la creazione di una conversazione.
class ConversationDraft {
  const ConversationDraft({
    required this.title,
    this.providerId,
    this.modelId,
    this.metadata,
  });

  final String title;
  final String? providerId;
  final String? modelId;
  final Map<String, Object?>? metadata;

  Map<String, Object?> toJson() => {
    'title': title,
    if (providerId != null) 'provider_id': providerId,
    if (modelId != null) 'model_id': modelId,
    if (metadata != null) 'metadata': metadata,
  };
}

/// Input per l'aggiunta di un messaggio a una conversazione.
class ConversationMessageDraft {
  const ConversationMessageDraft({
    required this.role,
    required this.content,
    this.isDemo = false,
    this.providerLabel,
  });

  final String role;
  final String content;
  final bool isDemo;
  final String? providerLabel;

  Map<String, Object?> toJson() => {
    'role': role,
    'content': content,
    'is_demo': isDemo,
    'provider_label': providerLabel,
  };
}

/// Risposta dell'endpoint chat in conversazione.
class AiConversationResponse {
  const AiConversationResponse({
    required this.providerId,
    required this.modelId,
    required this.content,
  });

  final String providerId;
  final String modelId;
  final String content;

  factory AiConversationResponse.fromJson(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Formato della risposta AI non valido.');
    }
    final providerId = value['provider_id'];
    final modelId = value['model_id'];
    final content = value['content'];
    if (providerId is! String || modelId is! String || content is! String) {
      throw const FormatException('Campi della risposta AI non validi.');
    }
    return AiConversationResponse(
      providerId: providerId,
      modelId: modelId,
      content: content,
    );
  }
}
