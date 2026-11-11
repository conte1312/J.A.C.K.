/// Knowledge API service (M4.2+).
/// Chiama il backend FastAPI su loopback 127.0.0.1:8000.
library jack_knowledge_api_service;

import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/knowledge_models.dart';

class KnowledgeApiService {
  KnowledgeApiService({this.baseUrl = 'http://127.0.0.1:8000', this.client});

  final String baseUrl;
  final http.Client? client;

  http.Client get _effectiveClient => client ?? http.Client();

  Future<Map<String, dynamic>> _get(String path) async {
    final uri = Uri.parse('$baseUrl$path');
    try {
      final response = await _effectiveClient.get(uri);
      return _handle(response);
    } catch (e) {
      throw Exception('Errore contattando il backend: $e');
    }
  }

  Future<Map<String, dynamic>> _post(String path,
      {Map<String, dynamic>? body}) async {
    final uri = Uri.parse('$baseUrl$path');
    try {
      final response = await _effectiveClient.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: body == null ? null : jsonEncode(body),
      );
      return _handle(response);
    } catch (e) {
      throw Exception('Errore contattando il backend: $e');
    }
  }

  Future<Map<String, dynamic>> _put(String path,
      {required Map<String, dynamic> body}) async {
    final uri = Uri.parse('$baseUrl$path');
    final response = await _effectiveClient.put(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    return _handle(response);
  }

  Map<String, dynamic> _handle(http.Response response) {
    if (response.statusCode >= 500) {
      throw Exception('Backend errore: ${response.statusCode}');
    }
    if (response.statusCode >= 400) {
      String detail = 'Richiesta non valida';
      try {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>?;
        detail = decoded?['detail']?.toString() ?? detail;
      } catch (_) {}
      throw Exception(detail);
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  // ---------- Health ----------
  Future<KnowledgeHealth> getHealth() async {
    final data = await _get('/api/v2/knowledge/health');
    return KnowledgeHealth.fromJson(data);
  }

  // ---------- Domains ----------
  Future<List<KnowledgeDomain>> listDomains({
    String? parentDomainId,
  }) async {
    final q = <String, String>{};
    if (parentDomainId != null) q['parent_domain_id'] = parentDomainId;
    final uri = Uri.parse('$baseUrl/api/v2/knowledge/domains').replace(
      queryParameters: q,
    );
    final response = await _effectiveClient.get(uri);
    return (_handle(response) as List)
        .map((e) => KnowledgeDomain.fromJson(e))
        .toList();
  }

  Future<KnowledgeDomain> createDomain({
    required String name,
    required String slug,
    String? description,
    String? parentDomainId,
  }) async {
    final data = await _post('/api/v2/knowledge/domains', body: {
      'name': name,
      'slug': slug,
      'description': description,
      'parent_domain_id': parentDomainId,
    });
    return KnowledgeDomain.fromJson(data);
  }

  Future<KnowledgeDomain> getDomain(String domainId) async {
    final data = await _get('/api/v2/knowledge/domains/$domainId');
    return KnowledgeDomain.fromJson(data);
  }

  Future<KnowledgeDomain> updateDomain({
    required String domainId,
    required String name,
    required String slug,
    String? description,
    String? parentDomainId,
  }) async {
    final data = await _put('/api/v2/knowledge/domains/$domainId', body: {
      'name': name,
      'slug': slug,
      'description': description,
      'parent_domain_id': parentDomainId,
    });
    return KnowledgeDomain.fromJson(data);
  }

  Future<bool> deleteDomain(String domainId) async {
    final uri = Uri.parse('$baseUrl/api/v2/knowledge/domains/$domainId');
    final response = await _effectiveClient.delete(uri);
    if (response.statusCode >= 400) {
      throw Exception('Errore eliminazione dominio: ${response.statusCode}');
    }
    return true;
  }

  // ---------- Items ----------
  Future<List<KnowledgeItem>> listItems({
    String? domainId,
    String? knowledgeType,
    String? sourceType,
    String? verificationStatus,
    String? itemState,
    bool? isCurrent,
    List<String>? tags,
    int? importanceMin,
    int? importanceMax,
    bool? excluded,
    String? query,
    int limit = 50,
    int offset = 0,
  }) async {
    final q = <String, String>{};
    if (domainId != null) q['domain_id'] = domainId;
    if (knowledgeType != null) q['knowledge_type'] = knowledgeType;
    if (sourceType != null) q['source_type'] = sourceType;
    if (verificationStatus != null)
      q['verification_status'] = verificationStatus;
    if (itemState != null) q['item_state'] = itemState;
    if (isCurrent != null) q['is_current'] = isCurrent.toString();
    if (tags != null) q['tags'] = tags.join(',');
    if (importanceMin != null) q['importance_min'] = importanceMin.toString();
    if (importanceMax != null) q['importance_max'] = importanceMax.toString();
    if (excluded != null) q['excluded'] = excluded.toString();
    if (query != null) q['q'] = query;
    q['limit'] = limit.toString();
    q['offset'] = offset.toString();
    final uri = Uri.parse('$baseUrl/api/v2/knowledge/items').replace(
      queryParameters: q,
    );
    final response = await _effectiveClient.get(uri);
    return (_handle(response) as List)
        .map((e) => KnowledgeItem.fromJson(e))
        .toList();
  }

  Future<KnowledgeItem> createItem({
    required String title,
    required String content,
    required String domainId,
    String knowledgeType = 'concept',
    String sourceType = 'system',
    String? sourceId,
    String? sourceTitle,
    String? sourceUrl,
    double? confidenceScore,
    String? verificationStatus,
    String? itemState,
    List<String>? tags,
    int? importance,
    bool? excluded,
    String? conversationId,
  }) async {
    final body = <String, dynamic>{
      'title': title,
      'content': content,
      'domain_id': domainId,
      'knowledge_type': knowledgeType,
      'source_type': sourceType,
    };
    if (sourceId != null) body['source_id'] = sourceId;
    if (sourceTitle != null) body['source_title'] = sourceTitle;
    if (sourceUrl != null) body['source_url'] = sourceUrl;
    if (confidenceScore != null) body['confidence_score'] = confidenceScore;
    if (verificationStatus != null)
      body['verification_status'] = verificationStatus;
    if (itemState != null) body['item_state'] = itemState;
    if (tags != null) body['tags'] = tags;
    if (importance != null) body['importance'] = importance;
    if (excluded != null) body['excluded'] = excluded;
    if (conversationId != null) body['conversation_id'] = conversationId;

    final data = await _post('/api/v2/knowledge/items', body: body);
    return KnowledgeItem.fromJson(data);
  }

  Future<KnowledgeItem> getItem(String itemId) async {
    final data = await _get('/api/v2/knowledge/items/$itemId');
    return KnowledgeItem.fromJson(data);
  }

  Future<KnowledgeItem> updateItem({
    required String itemId,
    String? title,
    String? content,
    String? summary,
    String? knowledgeType,
    String? sourceType,
    String? sourceId,
    String? sourceTitle,
    String? sourceUrl,
    double? confidenceScore,
    String? verificationStatus,
    String? itemState,
    String? verificationReason,
    DateTime? expiresAt,
  }) async {
    final body = <String, dynamic>{};
    if (title != null) body['title'] = title;
    if (content != null) body['content'] = content;
    if (summary != null) body['summary'] = summary;
    if (knowledgeType != null) body['knowledge_type'] = knowledgeType;
    if (sourceType != null) body['source_type'] = sourceType;
    if (sourceId != null) body['source_id'] = sourceId;
    if (sourceTitle != null) body['source_title'] = sourceTitle;
    if (sourceUrl != null) body['source_url'] = sourceUrl;
    if (confidenceScore != null) body['confidence_score'] = confidenceScore;
    if (verificationStatus != null)
      body['verification_status'] = verificationStatus;
    if (itemState != null) body['item_state'] = itemState;
    if (verificationReason != null)
      body['verification_reason'] = verificationReason;
    if (expiresAt != null) body['expires_at'] = expiresAt.toIso8601String();

    final data = await _put('/api/v2/knowledge/items/$itemId', body: body);
    return KnowledgeItem.fromJson(data);
  }

  Future<bool> archiveItem(String itemId) async {
    final uri = Uri.parse('$baseUrl/api/v2/knowledge/items/$itemId');
    final response = await _effectiveClient.delete(uri);
    if (response.statusCode >= 400) {
      throw Exception('Errore archiviazione elemento: ${response.statusCode}');
    }
    return true;
  }

  Future<List<KnowledgeItem>> searchItems({
    required String query,
    String? domainId,
    String? knowledgeType,
    String? verificationStatus,
    String? itemState,
    int limit = 50,
  }) async {
    final q = <String, String>{
      'q': query,
      'limit': limit.toString(),
    };
    if (domainId != null) q['domain_id'] = domainId;
    if (knowledgeType != null) q['knowledge_type'] = knowledgeType;
    if (verificationStatus != null)
      q['verification_status'] = verificationStatus;
    if (itemState != null) q['item_state'] = itemState;
    final uri = Uri.parse('$baseUrl/api/v2/knowledge/items/search').replace(
      queryParameters: q,
    );
    final response = await _effectiveClient.get(uri);
    return (_handle(response) as List)
        .map((e) => KnowledgeItem.fromJson(e))
        .toList();
  }

  // ---------- Links ----------
  Future<List<KnowledgeLink>> listLinks({
    String? itemId,
    String? relationType,
    int limit = 50,
  }) async {
    final q = <String, String>{};
    if (itemId != null) q['item_id'] = itemId;
    if (relationType != null) q['relation_type'] = relationType;
    final uri = Uri.parse('$baseUrl/api/v2/knowledge/links').replace(
      queryParameters: q,
    );
    final response = await _effectiveClient.get(uri);
    return (_handle(response) as List)
        .map((e) => KnowledgeLink.fromJson(e))
        .toList();
  }

  Future<KnowledgeLink> createLink({
    required String fromId,
    required String toId,
    required String relationType,
    int strength = 1,
    String? description,
  }) async {
    final data = await _post('/api/v2/knowledge/links', body: {
      'from_id': fromId,
      'to_id': toId,
      'relation_type': relationType,
      'strength': strength,
      'description': description,
    });
    return KnowledgeLink.fromJson(data);
  }

  Future<bool> deleteLink(String linkId) async {
    final uri = Uri.parse('$baseUrl/api/v2/knowledge/links/$linkId');
    final response = await _effectiveClient.delete(uri);
    if (response.statusCode >= 400) {
      throw Exception('Errore eliminazione link: ${response.statusCode}');
    }
    return true;
  }

  // ---------- Proposals ----------
  Future<List<KnowledgeProposal>> listProposals({
    String? processState,
  }) async {
    final q = <String, String>{};
    if (processState != null) q['process_state'] = processState;
    final uri = Uri.parse('$baseUrl/api/v2/knowledge/proposals').replace(
      queryParameters: q,
    );
    final response = await _effectiveClient.get(uri);
    return (_handle(response) as List)
        .map((e) => KnowledgeProposal.fromJson(e))
        .toList();
  }

  Future<KnowledgeProposal> createProposal({
    required String title,
    required String content,
    required String domainId,
    String knowledgeType = 'concept',
    String sourceType = 'autonomous',
    String? sourceId,
    String? sourceTitle,
    String? sourceUrl,
    double? confidenceScore,
    String? verificationStatus,
    List<String>? tags,
    int? importance,
    bool? excluded,
    String? conversationId,
  }) async {
    final body = <String, dynamic>{
      'title': title,
      'content': content,
      'domain_id': domainId,
      'knowledge_type': knowledgeType,
      'source_type': sourceType,
    };
    if (sourceId != null) body['source_id'] = sourceId;
    if (sourceTitle != null) body['source_title'] = sourceTitle;
    if (sourceUrl != null) body['source_url'] = sourceUrl;
    if (confidenceScore != null) body['confidence_score'] = confidenceScore;
    if (verificationStatus != null)
      body['verification_status'] = verificationStatus;
    if (tags != null) body['tags'] = tags;
    if (importance != null) body['importance'] = importance;
    if (excluded != null) body['excluded'] = excluded;
    if (conversationId != null) body['conversation_id'] = conversationId;

    final data = await _post('/api/v2/knowledge/proposals', body: body);
    return KnowledgeProposal.fromJson(data);
  }

  Future<KnowledgeProposal> getProposal(String proposalId) async {
    final data = await _get('/api/v2/knowledge/proposals/$proposalId');
    return KnowledgeProposal.fromJson(data);
  }

  Future<KnowledgeItem> approveProposal(String proposalId) async {
    final data = await _post(
      '/api/v2/knowledge/proposals/$proposalId/approve',
    );
    return KnowledgeItem.fromJson(data);
  }

  Future<KnowledgeProposal> rejectProposal(String proposalId) async {
    final data = await _post(
      '/api/v2/knowledge/proposals/$proposalId/reject',
    );
    return KnowledgeProposal.fromJson(data);
  }

  // ---------- Documents ----------
  Future<List<KnowledgeSource>> listDocuments() async {
    final data = await _get('/api/v2/knowledge/documents');
    return (data as List)
        .map((e) => KnowledgeSource.fromJson(e))
        .toList();
  }

  Future<KnowledgeSource> getDocument(String sourceId) async {
    final data = await _get('/api/v2/knowledge/documents/$sourceId');
    return KnowledgeSource.fromJson(data);
  }

  Future<List<KnowledgeChunk>> getDocumentChunks(String sourceId) async {
    final data = await _get('/api/v2/knowledge/documents/$sourceId/chunks');
    return (data as List).map((e) => KnowledgeChunk.fromJson(e)).toList();
  }

  Future<KnowledgeProposal> reprocessDocument({
    required String sourceId,
    bool skipDuplicate = true,
  }) async {
    final data = await _post(
      '/api/v2/knowledge/documents/$sourceId/reprocess',
      body: {'skip_duplicate': skipDuplicate},
    );
    return KnowledgeProposal.fromJson(data);
  }

  Future<bool> deleteDocument(String sourceId) async {
    final uri = Uri.parse('$baseUrl/api/v2/knowledge/documents/$sourceId');
    final response = await _effectiveClient.delete(uri);
    if (response.statusCode >= 400) {
      throw Exception('Errore eliminazione documento: ${response.statusCode}');
    }
    return true;
  }

  Future<KnowledgeItem> importDocumentFile({
    required String filePath,
    String? domainId,
    bool skipDuplicate = true,
  }) async {
    final q = <String, String>{
      'file_path': filePath,
      if (domainId != null) 'domain_id': domainId,
      'skip_duplicate': skipDuplicate.toString(),
    };
    final uri = Uri.parse('$baseUrl/api/v2/knowledge/documents/import/file')
        .replace(queryParameters: q);
    final response = await _effectiveClient.post(uri);
    return _handleItemResponse(response);
  }

  KnowledgeItem _handleItemResponse(http.Response response) {
    if (response.statusCode >= 400) {
      String detail = 'Richiesta non valida';
      try {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>?;
        detail = decoded?['detail']?.toString() ?? detail;
      } catch (_) {}
      throw Exception(detail);
    }
    return KnowledgeItem.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  // ---------- Search (M4.4) ----------
  Future<List<KnowledgeSearchResult>> searchHybrid({
    required String query,
    String? domainId,
    String? knowledgeType,
    String? verificationStatus,
    String? itemState = 'published',
    int limit = 10,
    int offset = 0,
    double minSimilarity = 0.1,
  }) async {
    final body = <String, dynamic>{
      'query': query,
      'limit': limit,
      'offset': offset,
      'min_similarity': minSimilarity,
    };
    if (domainId != null) body['domain_id'] = domainId;
    if (knowledgeType != null) body['knowledge_type'] = knowledgeType;
    if (verificationStatus != null)
      body['verification_status'] = verificationStatus;
    if (itemState != null) body['item_state'] = itemState;

    final data = await _post('/api/v2/knowledge/search/hybrid', body: body);
    return (data['results'] as List)
        .map((e) => KnowledgeSearchResult.fromJson(e))
        .toList();
  }

  Future<List<KnowledgeSearchResult>> searchSemantic({
    required String query,
    String? domainId,
    String? knowledgeType,
    String? verificationStatus,
    String? itemState = 'published',
    int limit = 10,
    int offset = 0,
    double minSimilarity = 0.1,
  }) async {
    final body = <String, dynamic>{
      'query': query,
      'limit': limit,
      'offset': offset,
      'min_similarity': minSimilarity,
    };
    if (domainId != null) body['domain_id'] = domainId;
    if (knowledgeType != null) body['knowledge_type'] = knowledgeType;
    if (verificationStatus != null)
      body['verification_status'] = verificationStatus;
    if (itemState != null) body['item_state'] = itemState;

    final data = await _post('/api/v2/knowledge/search/semantic', body: body);
    return (data['results'] as List)
        .map((e) => KnowledgeSearchResult.fromJson(e))
        .toList();
  }

  Future<SearchStatus> getSearchStatus() async {
    final data = await _get('/api/v2/knowledge/search/status');
    return SearchStatus.fromJson(data);
  }

  // ---------- Context (M4.6) ----------
  Future<ResolutionPlan> resolveContext({
    required String query,
    String? conversationContext,
    String? domainId,
    int maxItems = 10,
  }) async {
    final body = <String, dynamic>{
      'query': query,
      'max_items': maxItems,
    };
    if (conversationContext != null)
      body['conversation_context'] = conversationContext;
    if (domainId != null) body['domain_id'] = domainId;

    final data = await _post('/api/v2/knowledge/context/resolve', body: body);
    return ResolutionPlan.fromJson(data);
  }

  Future<ContextPackage> buildContext({
    required String query,
    String? conversationContext,
    String? domainId,
    int maxItems = 10,
    int? targetModelContext,
    bool includePersonal = false,
  }) async {
    final body = <String, dynamic>{
      'query': query,
      'max_items': maxItems,
      'include_personal': includePersonal,
    };
    if (conversationContext != null)
      body['conversation_context'] = conversationContext;
    if (domainId != null) body['domain_id'] = domainId;
    if (targetModelContext != null)
      body['target_model_context'] = targetModelContext;

    final data = await _post('/api/v2/knowledge/context/build', body: body);
    return ContextPackage.fromJson(data);
  }

  // ---------- Maintenance (M4.7) ----------
  Future<Map<String, dynamic>> runMaintenance({
    int staleDays = 180,
  }) async {
    return await _post(
      '/api/v2/knowledge/maintenance/run',
      body: {'stale_days': staleDays},
    );
  }

  Future<List<Map<String, dynamic>>> listDuplicates() async {
    final data = await _get('/api/v2/knowledge/maintenance/duplicates');
    return (data as List).cast<Map<String, dynamic>>();
  }

  // ---------- Validation (M4.7) ----------
  Future<Map<String, dynamic>> evaluateSource(String sourceId) async {
    return await _get(
      '/api/v2/validation/evaluate-source?source_id=$sourceId',
    );
  }

  Future<Map<String, dynamic>> evaluatePolicy({
    required String sourceId,
    String contentSensitivity = 'general',
    double? sourceTrust,
  }) async {
    final body = <String, dynamic>{
      'source_id': sourceId,
      'content_sensitivity': contentSensitivity,
    };
    if (sourceTrust != null) body['source_trust'] = sourceTrust;
    return await _post('/api/v2/validation/evaluate-policy', body: body);
  }

  Future<bool> validateTransition({
    required String itemId,
    required String currentState,
    required String targetState,
    required String stateType,
  }) async {
    final data = await _post(
      '/api/v2/validation/validate-transition',
      body: {
        'item_id': itemId,
        'current_state': currentState,
        'target_state': targetState,
        'state_type': stateType,
      },
    );
    return data['allowed'] as bool;
  }

  Future<List<Map<String, dynamic>>> getVersions(String itemId) async {
    final data = await _get('/api/v2/validation/versions/$itemId');
    return (data as List).cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> getContradictions({
    String? itemId,
  }) async {
    final q = <String, String>{};
    if (itemId != null) q['item_id'] = itemId;
    final uri = Uri.parse('$baseUrl/api/v2/validation/contradictions')
        .replace(queryParameters: q);
    final response = await _effectiveClient.get(uri);
    return (jsonDecode(response.body) as List)
        .cast<Map<String, dynamic>>();
  }
}
