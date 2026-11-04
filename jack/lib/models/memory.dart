enum MemoryCategory {
  identity('identity', 'Identità'),
  work('work', 'Lavoro'),
  projects('projects', 'Progetti'),
  people('people', 'Persone'),
  technical('technical', 'Tecnica'),
  preferences('preferences', 'Preferenze'),
  events('events', 'Eventi'),
  other('other', 'Altro');

  const MemoryCategory(this.apiValue, this.label);

  final String apiValue;
  final String label;

  // Source-compatible aliases for existing Flutter callers.
  static const personale = identity;
  static const lavoro = work;
  static const progetti = projects;
  static const preferenze = preferences;
  static const note = other;

  static MemoryCategory fromApiValue(String value) {
    final canonical = switch (value) {
      'personale' => 'identity',
      'lavoro' => 'work',
      'progetti' => 'projects',
      'preferenze' => 'preferences',
      'note' => 'other',
      _ => value,
    };
    return MemoryCategory.values.firstWhere(
      (category) => category.apiValue == canonical,
    );
  }
}

enum MemorySourceType {
  saved,
  retrieved,
  inference;

  static MemorySourceType fromApiValue(String value) =>
      MemorySourceType.values.firstWhere((type) => type.name == value);
}

enum MemoryVerification {
  verified,
  toVerify,
  inferred;

  String get apiValue => switch (this) {
    MemoryVerification.verified => 'verified',
    MemoryVerification.toVerify => 'to_verify',
    MemoryVerification.inferred => 'inferred',
  };

  static MemoryVerification fromApiValue(String value) => switch (value) {
    'verified' => MemoryVerification.verified,
    'to_verify' => MemoryVerification.toVerify,
    'inferred' => MemoryVerification.inferred,
    _ => throw const FormatException('Verifica del ricordo non valida.'),
  };
}

class MemoryDraft {
  const MemoryDraft({
    required this.title,
    required this.content,
    required this.category,
    this.sourceType = MemorySourceType.saved,
    this.source = 'user_entry',
    this.verification = MemoryVerification.toVerify,
    this.tags = const [],
    this.importance = 3,
    this.excluded = false,
    this.conversationId,
  });

  final String title;
  final String content;
  final MemoryCategory category;
  final MemorySourceType sourceType;
  final String? source;
  final MemoryVerification verification;
  final List<String> tags;
  final int importance;
  final bool excluded;
  final String? conversationId;

  Map<String, Object?> toJson() => {
    'title': title,
    'content': content,
    'category': category.apiValue,
    'source_type': sourceType.name,
    'source': source,
    'verification': verification.apiValue,
    'tags': tags,
    'importance': importance,
    'excluded': excluded,
    'conversation_id': conversationId,
  };
}

class MemoryRecord {
  const MemoryRecord({
    required this.id,
    required this.title,
    required this.content,
    required this.category,
    required this.createdAt,
    required this.updatedAt,
    this.sourceType = MemorySourceType.saved,
    this.source,
    this.verification = MemoryVerification.toVerify,
    this.tags = const [],
    this.importance = 3,
    this.excluded = false,
    this.conversationId,
    this.lastUsed,
  });

  final String id;
  final String title;
  final String content;
  final MemoryCategory category;
  final MemorySourceType sourceType;
  final String? source;
  final MemoryVerification verification;
  final List<String> tags;
  final int importance;
  final bool excluded;
  final String? conversationId;
  final DateTime? lastUsed;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory MemoryRecord.fromJson(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Formato del ricordo non valido.');
    }
    final id = value['id'];
    final title = value['title'];
    final content = value['content'];
    final category = value['category'];
    final createdAt = value['created_at'];
    final updatedAt = value['updated_at'];
    final rawSource = value['source'];
    final rawSourceType = value['source_type'] ?? 'saved';
    final rawVerification = value['verification'] ?? 'to_verify';
    final rawTags = value['tags'] ?? const <Object?>[];
    final rawImportance = value['importance'] ?? 3;
    final rawExcluded = value['excluded'] ?? false;
    final rawConversationId = value['conversation_id'];
    final rawLastUsed = value['last_used'];

    if (id is! String ||
        title is! String ||
        content is! String ||
        category is! String ||
        createdAt is! String ||
        updatedAt is! String ||
        (rawSource != null && rawSource is! String) ||
        rawSourceType is! String ||
        rawVerification is! String ||
        rawTags is! List ||
        rawTags.any((tag) => tag is! String) ||
        rawImportance is! int ||
        rawImportance < 1 ||
        rawImportance > 5 ||
        rawExcluded is! bool ||
        (rawConversationId != null && rawConversationId is! String) ||
        (rawLastUsed != null && rawLastUsed is! String)) {
      throw const FormatException('Campi del ricordo non validi.');
    }

    try {
      return MemoryRecord(
        id: id,
        title: title,
        content: content,
        category: MemoryCategory.fromApiValue(category),
        sourceType: MemorySourceType.fromApiValue(rawSourceType),
        source: rawSource as String?,
        verification: MemoryVerification.fromApiValue(rawVerification),
        tags: List<String>.unmodifiable(rawTags.cast<String>()),
        importance: rawImportance,
        excluded: rawExcluded,
        conversationId: rawConversationId as String?,
        lastUsed: rawLastUsed == null
            ? null
            : DateTime.parse(rawLastUsed).toUtc(),
        createdAt: DateTime.parse(createdAt).toUtc(),
        updatedAt: DateTime.parse(updatedAt).toUtc(),
      );
    } on Object {
      throw const FormatException('Campi del ricordo non validi.');
    }
  }
}

class MemoryLinkDraft {
  const MemoryLinkDraft({
    required this.fromId,
    required this.toId,
    required this.relation,
    this.strength = 2,
  });

  final String fromId;
  final String toId;
  final String relation;
  final int strength;

  Map<String, Object> toJson() => {
    'from_id': fromId,
    'to_id': toId,
    'relation': relation,
    'strength': strength,
  };
}

class MemoryLink {
  const MemoryLink({
    required this.id,
    required this.fromId,
    required this.toId,
    required this.relation,
    required this.strength,
    required this.createdAt,
  });

  final String id;
  final String fromId;
  final String toId;
  final String relation;
  final int strength;
  final DateTime createdAt;

  factory MemoryLink.fromJson(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Formato del collegamento non valido.');
    }
    final id = value['id'];
    final fromId = value['from_id'];
    final toId = value['to_id'];
    final relation = value['relation'];
    final strength = value['strength'];
    final createdAt = value['created_at'];
    if (id is! String ||
        fromId is! String ||
        toId is! String ||
        relation is! String ||
        strength is! int ||
        strength < 1 ||
        strength > 3 ||
        createdAt is! String) {
      throw const FormatException('Campi del collegamento non validi.');
    }
    try {
      return MemoryLink(
        id: id,
        fromId: fromId,
        toId: toId,
        relation: relation,
        strength: strength,
        createdAt: DateTime.parse(createdAt).toUtc(),
      );
    } on FormatException {
      throw const FormatException('Campi del collegamento non validi.');
    }
  }
}

class MemoryGraph {
  const MemoryGraph({required this.nodes, required this.edges});

  final List<MemoryRecord> nodes;
  final List<MemoryLink> edges;

  factory MemoryGraph.fromJson(Object? value) {
    if (value is! Map<String, dynamic> ||
        value['nodes'] is! List ||
        value['edges'] is! List) {
      throw const FormatException('Formato del grafo non valido.');
    }
    try {
      return MemoryGraph(
        nodes: List<MemoryRecord>.unmodifiable(
          (value['nodes'] as List).map(MemoryRecord.fromJson),
        ),
        edges: List<MemoryLink>.unmodifiable(
          (value['edges'] as List).map(MemoryLink.fromJson),
        ),
      );
    } on FormatException {
      throw const FormatException('Dati del grafo non validi.');
    }
  }
}
