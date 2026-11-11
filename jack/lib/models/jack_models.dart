/// Shared domain models for J.A.C.K. 2.0.
library jack_models;

/// A memory entry (persistent memory domain).
class MemoryEntry {
  final String id;
  final String title;
  final String content;
  final String category;
  final String sourceType;
  final String? source;
  final String verification;
  final List<String> tags;
  final int importance;
  final bool excluded;
  final String? conversationId;
  final String? lastUsed;
  final String createdAt;
  final String updatedAt;

  const MemoryEntry({
    required this.id,
    required this.title,
    required this.content,
    required this.category,
    required this.sourceType,
    this.source,
    required this.verification,
    this.tags = const [],
    this.importance = 3,
    this.excluded = false,
    this.conversationId,
    this.lastUsed,
    required this.createdAt,
    required this.updatedAt,
  });

  MemoryEntry copyWith({
    String? id,
    String? title,
    String? content,
    String? category,
    String? sourceType,
    String? source,
    String? verification,
    List<String>? tags,
    int? importance,
    bool? excluded,
    String? conversationId,
    String? lastUsed,
    String? createdAt,
    String? updatedAt,
  }) {
    return MemoryEntry(
      id: id ?? this.id,
      title: title ?? this.title,
      content: content ?? this.content,
      category: category ?? this.category,
      sourceType: sourceType ?? this.sourceType,
      source: source ?? this.source,
      verification: verification ?? this.verification,
      tags: tags ?? this.tags,
      importance: importance ?? this.importance,
      excluded: excluded ?? this.excluded,
      conversationId: conversationId ?? this.conversationId,
      lastUsed: lastUsed ?? this.lastUsed,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is MemoryEntry &&
          runtimeType == other.runtimeType &&
          id == other.id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() =>
      'MemoryEntry(id: $id, title: $title, category: $category)';
}

/// A conversation.
class Conversation {
  final String id;
  final String title;
  final String createdAt;
  final String updatedAt;

  const Conversation({
    required this.id,
    required this.title,
    required this.createdAt,
    required this.updatedAt,
  });

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Conversation &&
          runtimeType == other.runtimeType &&
          id == other.id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() => 'Conversation(id: $id, title: $title)';
}

/// A chat message.
class ChatMessage {
  final String id;
  final String conversationId;
  final String role; // 'user' | 'assistant'
  final String content;
  final String createdAt;

  const ChatMessage({
    required this.id,
    required this.conversationId,
    required this.role,
    required this.content,
    required this.createdAt,
  });

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ChatMessage &&
          runtimeType == other.runtimeType &&
          id == other.id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() => 'ChatMessage(id: $id, role: $role)';
}

/// Provider state (AI Hub domain).
class AiProviderState {
  final String id;
  final String name;
  final String kind; // 'local' | 'cloud'
  final bool enabled;
  final bool connected;
  final List<String> models;
  final double timeoutSeconds;
  final bool fallback;
  final String? lastError;
  final String? lastVerifiedAt;

  const AiProviderState({
    required this.id,
    required this.name,
    required this.kind,
    required this.enabled,
    required this.connected,
    required this.models,
    this.timeoutSeconds = 30.0,
    this.fallback = true,
    this.lastError,
    this.lastVerifiedAt,
  });

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AiProviderState &&
          runtimeType == other.runtimeType &&
          id == other.id;

  @override
  int get hashCode => id.hashCode;

  @override
  String toString() => 'AiProviderState(id: $id, connected: $connected)';
}

/// System status.
class SystemStatus {
  final bool bindLoopback;
  final bool autonomousExecution;
  final bool approvalsEnforced;
  final bool backupsEncrypted;
  final bool restoreImplemented;
  final String note;

  const SystemStatus({
    required this.bindLoopback,
    required this.autonomousExecution,
    required this.approvalsEnforced,
    required this.backupsEncrypted,
    required this.restoreImplemented,
    required this.note,
  });

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is SystemStatus && runtimeType == other.runtimeType;

  @override
  int get hashCode => Object.hash(
    bindLoopback,
    autonomousExecution,
    approvalsEnforced,
    backupsEncrypted,
    restoreImplemented,
  );

  @override
  String toString() => 'SystemStatus(bindLoopback: $bindLoopback)';
}
