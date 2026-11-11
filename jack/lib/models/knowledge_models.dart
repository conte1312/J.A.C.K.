/// Modelli dati per il Knowledge Core API (M4.8).
/// Tutte le classi sono immutable e decodificano le risposte JSON del backend.


/// Risposta generica dell'API Knowledge.
class KnowledgeItem {
  final String id;
  final String domainId;
  final String title;
  final String content;
  final String? summary;
  final String knowledgeType;
  final String sourceType;
  final String? sourceId;
  final String? sourceTitle;
  final String? sourceUrl;
  final double confidenceScore;
  final String verificationStatus;
  final String itemState;
  final int version;
  final bool isCurrent;
  final DateTime acquiredAt;
  final DateTime? verifiedAt;
  final String? verificationReason;
  final DateTime? expiresAt;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<String> tags;
  final int importance;
  final bool excluded;
  final String? conversationId;
  final DateTime? lastUsed;

  KnowledgeItem({
    required this.id,
    required this.domainId,
    required this.title,
    required this.content,
    this.summary,
    required this.knowledgeType,
    required this.sourceType,
    this.sourceId,
    this.sourceTitle,
    this.sourceUrl,
    required this.confidenceScore,
    required this.verificationStatus,
    required this.itemState,
    required this.version,
    required this.isCurrent,
    required this.acquiredAt,
    this.verifiedAt,
    this.verificationReason,
    this.expiresAt,
    required this.createdAt,
    required this.updatedAt,
    required this.tags,
    required this.importance,
    required this.excluded,
    this.conversationId,
    this.lastUsed,
  });

  factory KnowledgeItem.fromJson(Map<String, dynamic> json) {
    return KnowledgeItem(
      id: json['id'] as String,
      domainId: json['domain_id'] as String,
      title: json['title'] as String,
      content: json['content'] as String,
      summary: json['summary'] as String?,
      knowledgeType: json['knowledge_type'] as String,
      sourceType: json['source_type'] as String,
      sourceId: json['source_id'] as String?,
      sourceTitle: json['source_title'] as String?,
      sourceUrl: json['source_url'] as String?,
      confidenceScore: (json['confidence_score'] as num).toDouble(),
      verificationStatus: json['verification_status'] as String,
      itemState: json['item_state'] as String,
      version: json['version'] as int,
      isCurrent: json['is_current'] as bool,
      acquiredAt: DateTime.parse(json['acquired_at'] as String),
      verifiedAt: json['verified_at'] != null
          ? DateTime.parse(json['verified_at'] as String)
          : null,
      verificationReason: json['verification_reason'] as String?,
      expiresAt: json['expires_at'] != null
          ? DateTime.parse(json['expires_at'] as String)
          : null,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      tags: List<String>.from(json['tags'] as List),
      importance: json['importance'] as int,
      excluded: json['excluded'] as bool,
      conversationId: json['conversation_id'] as String?,
      lastUsed: json['last_used'] != null
          ? DateTime.parse(json['last_used'] as String)
          : null,
    );
  }
}

/// Proposta di conoscenza (M4.1/M4.2).
class KnowledgeProposal {
  final String id;
  final String title;
  final String content;
  final String domainId;
  final String knowledgeType;
  final String sourceType;
  final String? sourceId;
  final String? sourceTitle;
  final String? sourceUrl;
  final double confidenceScore;
  final String verificationStatus;
  final List<String> tags;
  final int importance;
  final bool excluded;
  final String? conversationId;
  final String processState;
  final DateTime createdAt;
  final DateTime expiresAt;
  final DateTime? resolvedAt;
  final String? publishedItemId;

  KnowledgeProposal({
    required this.id,
    required this.title,
    required this.content,
    required this.domainId,
    required this.knowledgeType,
    required this.sourceType,
    this.sourceId,
    this.sourceTitle,
    this.sourceUrl,
    required this.confidenceScore,
    required this.verificationStatus,
    required this.tags,
    required this.importance,
    required this.excluded,
    this.conversationId,
    required this.processState,
    required this.createdAt,
    required this.expiresAt,
    this.resolvedAt,
    this.publishedItemId,
  });

  factory KnowledgeProposal.fromJson(Map<String, dynamic> json) {
    return KnowledgeProposal(
      id: json['id'] as String,
      title: json['title'] as String,
      content: json['content'] as String,
      domainId: json['domain_id'] as String,
      knowledgeType: json['knowledge_type'] as String,
      sourceType: json['source_type'] as String,
      sourceId: json['source_id'] as String?,
      sourceTitle: json['source_title'] as String?,
      sourceUrl: json['source_url'] as String?,
      confidenceScore: (json['confidence_score'] as num).toDouble(),
      verificationStatus: json['verification_status'] as String,
      tags: List<String>.from(json['tags'] as List),
      importance: json['importance'] as int,
      excluded: json['excluded'] as bool,
      conversationId: json['conversation_id'] as String?,
      processState: json['process_state'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      expiresAt: DateTime.parse(json['expires_at'] as String),
      resolvedAt: json['resolved_at'] != null
          ? DateTime.parse(json['resolved_at'] as String)
          : null,
      publishedItemId: json['published_item_id'] as String?,
    );
  }
}

/// Relazione tra elementi di conoscenza.
class KnowledgeLink {
  final String id;
  final String fromId;
  final String toId;
  final String relationType;
  final String relationKey;
  final int strength;
  final String? description;
  final DateTime createdAt;

  KnowledgeLink({
    required this.id,
    required this.fromId,
    required this.toId,
    required this.relationType,
    required this.relationKey,
    required this.strength,
    this.description,
    required this.createdAt,
  });

  factory KnowledgeLink.fromJson(Map<String, dynamic> json) {
    return KnowledgeLink(
      id: json['id'] as String,
      fromId: json['from_id'] as String,
      toId: json['to_id'] as String,
      relationType: json['relation_type'] as String,
      relationKey: json['relation_key'] as String,
      strength: json['strength'] as int,
      description: json['description'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

/// Dominio di conoscenza.
class KnowledgeDomain {
  final String id;
  final String name;
  final String slug;
  final String? description;
  final String? parentDomainId;
  final DateTime createdAt;
  final DateTime updatedAt;

  KnowledgeDomain({
    required this.id,
    required this.name,
    required this.slug,
    this.description,
    this.parentDomainId,
    required this.createdAt,
    required this.updatedAt,
  });

  factory KnowledgeDomain.fromJson(Map<String, dynamic> json) {
    return KnowledgeDomain(
      id: json['id'] as String,
      name: json['name'] as String,
      slug: json['slug'] as String,
      description: json['description'] as String?,
      parentDomainId: json['parent_domain_id'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }
}

/// Documento importato (M4.3).
class KnowledgeSource {
  final String id;
  final String title;
  final String documentType;
  final String? filePath;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? contentHash;
  final int? pageCount;

  KnowledgeSource({
    required this.id,
    required this.title,
    required this.documentType,
    this.filePath,
    required this.createdAt,
    required this.updatedAt,
    this.contentHash,
    this.pageCount,
  });

  factory KnowledgeSource.fromJson(Map<String, dynamic> json) {
    return KnowledgeSource(
      id: json['id'] as String,
      title: json['title'] as String,
      documentType: json['document_type'] as String,
      filePath: json['file_path'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      contentHash: json['content_hash'] as String?,
      pageCount: json['page_count'] as int?,
    );
  }
}

/// Chunk di documento (M4.3).
class KnowledgeChunk {
  final String id;
  final String sourceId;
  final String? itemId;
  final int chunkIndex;
  final String content;
  final int? pageNumber;
  final String? sectionTitle;
  final int? charStart;
  final int? charEnd;
  final String? embeddingId;
  final DateTime createdAt;

  KnowledgeChunk({
    required this.id,
    required this.sourceId,
    this.itemId,
    required this.chunkIndex,
    required this.content,
    this.pageNumber,
    this.sectionTitle,
    this.charStart,
    this.charEnd,
    this.embeddingId,
    required this.createdAt,
  });

  factory KnowledgeChunk.fromJson(Map<String, dynamic> json) {
    return KnowledgeChunk(
      id: json['id'] as String,
      sourceId: json['source_id'] as String,
      itemId: json['item_id'] as String?,
      chunkIndex: json['chunk_index'] as int,
      content: json['content'] as String,
      pageNumber: json['page_number'] as int?,
      sectionTitle: json['section_title'] as String?,
      charStart: json['char_start'] as int?,
      charEnd: json['char_end'] as int?,
      embeddingId: json['embedding_id'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

/// Risultato di ricerca ibrida (M4.4).
class KnowledgeSearchResult {
  final KnowledgeItem item;
  final double score;
  final double? ftScore;
  final double? semanticScore;
  final List<String> matchReasons;

  KnowledgeSearchResult({
    required this.item,
    required this.score,
    this.ftScore,
    this.semanticScore,
    required this.matchReasons,
  });

  factory KnowledgeSearchResult.fromJson(Map<String, dynamic> json) {
    return KnowledgeSearchResult(
      item: KnowledgeItem.fromJson(json['item'] as Map<String, dynamic>),
      score: json['score'] as double,
      ftScore: json['ft_score'] != null
          ? (json['ft_score'] as num).toDouble()
          : null,
      semanticScore: json['semantic_score'] != null
          ? (json['semantic_score'] as num).toDouble()
          : null,
      matchReasons: List<String>.from(json['match_reasons'] as List),
    );
  }
}

/// Stato del servizio di ricerca semantica (M4.4).
class SearchStatus {
  final String embeddingProvider;
  final String embeddingVersion;
  final int embeddingDimensions;
  final int storedEmbeddings;
  final bool fts5Available;

  SearchStatus({
    required this.embeddingProvider,
    required this.embeddingVersion,
    required this.embeddingDimensions,
    required this.storedEmbeddings,
    required this.fts5Available,
  });

  factory SearchStatus.fromJson(Map<String, dynamic> json) {
    return SearchStatus(
      embeddingProvider: json['embedding_provider'] as String,
      embeddingVersion: json['embedding_version'] as String,
      embeddingDimensions: json['embedding_dimensions'] as int,
      storedEmbeddings: json['stored_embeddings'] as int,
      fts5Available: json['fts5_available'] as bool,
    );
  }
}

/// Stato di salute del Knowledge Engine (M4.1/M4.4).
class KnowledgeHealth {
  final String status;
  final int schemaVersion;

  KnowledgeHealth({
    required this.status,
    required this.schemaVersion,
  });

  factory KnowledgeHealth.fromJson(Map<String, dynamic> json) {
    return KnowledgeHealth(
      status: json['status'] as String,
      schemaVersion: json['schema_version'] as int,
    );
  }
}

/// Pacchetto di contesto (M4.6).
class ContextPackage {
  final String query;
  final List<ContextItem> items;
  final int totalItems;
  final int totalTokensEstimated;
  final int tokenBudget;
  final Map<String, int> verificationSummary;
  final List<Map<String, dynamic>> sources;
  final List<Map<String, dynamic>> graphLinks;
  final List<String> uncertaintyNotes;
  final DateTime generatedAt;
  final String contextVersion;

  ContextPackage({
    required this.query,
    required this.items,
    required this.totalItems,
    required this.totalTokensEstimated,
    required this.tokenBudget,
    required this.verificationSummary,
    required this.sources,
    required this.graphLinks,
    required this.uncertaintyNotes,
    required this.generatedAt,
    this.contextVersion = '1.0',
  });

  factory ContextPackage.fromJson(Map<String, dynamic> json) {
    return ContextPackage(
      query: json['query'] as String,
      items: List<ContextItem>.from(
        (json['items'] as List).map((e) => ContextItem.fromJson(e)),
      ),
      totalItems: json['total_items'] as int,
      totalTokensEstimated: json['total_tokens_estimated'] as int,
      tokenBudget: json['token_budget'] as int,
      verificationSummary: Map<String, int>.from(
        (json['verification_summary'] as Map).map(
          (k, v) => MapEntry(k as String, v as int),
        ),
      ),
      sources: List<Map<String, dynamic>>.from(
        (json['sources'] as List).map((e) => e as Map<String, dynamic>),
      ),
      graphLinks: List<Map<String, dynamic>>.from(
        (json['graph_links'] as List).map((e) => e as Map<String, dynamic>),
      ),
      uncertaintyNotes: List<String>.from(
        json['uncertainty_notes'] as List,
      ),
      generatedAt: DateTime.parse(json['generated_at'] as String),
      contextVersion: json['context_version'] as String,
    );
  }
}

/// Elemento di contesto (M4.6).
class ContextItem {
  final String itemId;
  final String title;
  final String content;
  final String sourceType;
  final String? sourceId;
  final String domainId;
  final String verificationStatus;
  final String itemState;
  final double confidence;
  final bool isPersonal;
  final Map<String, dynamic>? sourceProvenance;
  final int tokensEstimated;

  ContextItem({
    required this.itemId,
    required this.title,
    required this.content,
    required this.sourceType,
    this.sourceId,
    required this.domainId,
    required this.verificationStatus,
    required this.itemState,
    required this.confidence,
    required this.isPersonal,
    this.sourceProvenance,
    required this.tokensEstimated,
  });

  factory ContextItem.fromJson(Map<String, dynamic> json) {
    return ContextItem(
      itemId: json['item_id'] as String,
      title: json['title'] as String,
      content: json['content'] as String,
      sourceType: json['source_type'] as String,
      sourceId: json['source_id'] as String?,
      domainId: json['domain_id'] as String,
      verificationStatus: json['verification_status'] as String,
      itemState: json['item_state'] as String,
      confidence: json['confidence'] as double,
      isPersonal: json['is_personal'] as bool,
      sourceProvenance: json['source_provenance'] != null
          ? Map<String, dynamic>.from(json['source_provenance'])
          : null,
      tokensEstimated: json['tokens_estimated'] as int,
    );
  }
}

/// Piano di risoluzione contesto (M4.6).
class ResolutionPlan {
  final String query;
  final List<String> keyTerms;
  final List<String> relevantDomains;
  final List<String> relevantItemTypes;
  final List<String> suggestedVerification;
  final bool includeGraph;
  final int maxItems;
  final int maxChunks;
  final String reason;

  ResolutionPlan({
    required this.query,
    required this.keyTerms,
    required this.relevantDomains,
    required this.relevantItemTypes,
    required this.suggestedVerification,
    required this.includeGraph,
    required this.maxItems,
    required this.maxChunks,
    required this.reason,
  });

  factory ResolutionPlan.fromJson(Map<String, dynamic> json) {
    return ResolutionPlan(
      query: json['query'] as String,
      keyTerms: List<String>.from(json['key_terms'] as List),
      relevantDomains: List<String>.from(json['relevant_domains'] as List),
      relevantItemTypes:
          List<String>.from(json['relevant_item_types'] as List),
      suggestedVerification:
          List<String>.from(json['suggested_verification'] as List),
      includeGraph: json['include_graph'] as bool,
      maxItems: json['max_items'] as int,
      maxChunks: json['max_chunks'] as int,
      reason: json['reason'] as String,
    );
  }
}
