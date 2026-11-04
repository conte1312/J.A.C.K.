import '../models/memory.dart';
import 'local_api_client.dart';

abstract interface class MemoryRepository {
  Future<List<MemoryRecord>> list({
    String? query,
    MemoryCategory? category,
    bool? excluded,
  });

  Future<MemoryRecord> create(MemoryDraft draft);

  Future<MemoryRecord> update(String id, MemoryDraft draft);

  Future<void> delete(String id);

  Future<MemoryGraph> graph({
    String? query,
    MemoryCategory? category,
    bool? excluded,
  });

  Future<List<MemoryLink>> listLinks({String? memoryId});

  Future<MemoryLink> createLink(MemoryLinkDraft draft);

  Future<MemoryLink> updateLink(String id, MemoryLinkDraft draft);

  Future<void> deleteLink(String id);

  Future<MemoryRecord> setExcluded(String id, bool excluded);

  Future<MemoryRecord> markUsed(String id);
}

class MemoryApiService implements MemoryRepository {
  MemoryApiService({LocalApiClient? client})
    : _client = client ?? LocalApiClient();

  final LocalApiClient _client;

  @override
  Future<List<MemoryRecord>> list({
    String? query,
    MemoryCategory? category,
    bool? excluded,
  }) async {
    final parameters = <String, String>{};
    if (query != null && query.trim().isNotEmpty) {
      parameters['q'] = query.trim();
    }
    if (category != null) parameters['category'] = category.apiValue;
    if (excluded != null) parameters['excluded'] = '$excluded';

    final response = await _client.getJson(
      '/api/v1/memories',
      queryParameters: parameters,
    );
    if (response is! List) {
      throw const FormatException(
        'El backend ha restituito un elenco non valido.',
      );
    }
    return response.map(MemoryRecord.fromJson).toList(growable: false);
  }

  @override
  Future<MemoryRecord> create(MemoryDraft draft) async {
    final response = await _client.postJson('/api/v1/memories', draft.toJson());
    return MemoryRecord.fromJson(response);
  }

  @override
  Future<MemoryRecord> update(String id, MemoryDraft draft) async {
    final response = await _client.putJson(
      '/api/v1/memories/${Uri.encodeComponent(id)}',
      draft.toJson(),
    );
    return MemoryRecord.fromJson(response);
  }

  @override
  Future<void> delete(String id) =>
      _client.delete('/api/v1/memories/${Uri.encodeComponent(id)}');

  @override
  Future<MemoryGraph> graph({
    String? query,
    MemoryCategory? category,
    bool? excluded,
  }) async {
    final parameters = _memoryQueryParameters(
      query: query,
      category: category,
      excluded: excluded,
    );
    final response = await _client.getJson(
      '/api/v1/memories/graph',
      queryParameters: parameters,
    );
    return MemoryGraph.fromJson(response);
  }

  @override
  Future<List<MemoryLink>> listLinks({String? memoryId}) async {
    final response = await _client.getJson(
      '/api/v1/memories/links',
      queryParameters: memoryId == null ? {} : {'memory_id': memoryId},
    );
    if (response is! List) {
      throw const FormatException(
        'Il backend ha restituito un elenco di collegamenti non valido.',
      );
    }
    return response.map(MemoryLink.fromJson).toList(growable: false);
  }

  @override
  Future<MemoryLink> createLink(MemoryLinkDraft draft) async {
    final response = await _client.postJson(
      '/api/v1/memories/links',
      draft.toJson(),
    );
    return MemoryLink.fromJson(response);
  }

  @override
  Future<MemoryLink> updateLink(String id, MemoryLinkDraft draft) async {
    final response = await _client.putJson(
      '/api/v1/memories/links/${Uri.encodeComponent(id)}',
      draft.toJson(),
    );
    return MemoryLink.fromJson(response);
  }

  @override
  Future<void> deleteLink(String id) =>
      _client.delete('/api/v1/memories/links/${Uri.encodeComponent(id)}');

  @override
  Future<MemoryRecord> setExcluded(String id, bool excluded) async {
    final response = await _client.putJson(
      '/api/v1/memories/${Uri.encodeComponent(id)}/exclusion',
      {'excluded': excluded},
    );
    return MemoryRecord.fromJson(response);
  }

  @override
  Future<MemoryRecord> markUsed(String id) async {
    final response = await _client.putJson(
      '/api/v1/memories/${Uri.encodeComponent(id)}/last-used',
      const <String, Object?>{},
    );
    return MemoryRecord.fromJson(response);
  }

  Map<String, String> _memoryQueryParameters({
    String? query,
    MemoryCategory? category,
    bool? excluded,
  }) {
    final parameters = <String, String>{};
    if (query != null && query.trim().isNotEmpty) {
      parameters['q'] = query.trim();
    }
    if (category != null) parameters['category'] = category.apiValue;
    if (excluded != null) parameters['excluded'] = '$excluded';
    return parameters;
  }
}
