import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:jack/models/memory.dart';
import 'package:jack/services/local_api_client.dart';
import 'package:jack/services/memory_api_service.dart';

void main() {
  test('memory and graph service uses the local REST endpoints', () async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    final calls = <({String method, String path, String? body})>[];
    final now = DateTime.utc(2026, 11, 3, 12).toIso8601String();
    final memory = {
      'id': 'memory-1',
      'title': 'Riunione',
      'content': 'Luca segue il progetto.',
      'category': 'work',
      'source_type': 'saved',
      'source': 'user_entry',
      'verification': 'to_verify',
      'tags': ['local'],
      'importance': 3,
      'excluded': false,
      'conversation_id': null,
      'last_used': null,
      'created_at': now,
      'updated_at': now,
    };
    final link = {
      'id': 'link-1',
      'from_id': 'memory-1',
      'to_id': 'memory-2',
      'relation': 'related to',
      'strength': 2,
      'created_at': now,
    };
    final subscription = server.listen((request) async {
      final body = await utf8.decoder.bind(request).join();
      calls.add((
        method: request.method,
        path: request.uri.toString(),
        body: body.isEmpty ? null : body,
      ));
      request.response.headers.contentType = ContentType.json;

      final result = switch ((request.method, request.uri.path)) {
        ('GET', '/api/v1/memories/graph') => {
          'nodes': [memory],
          'edges': [link],
        },
        ('GET', '/api/v1/memories/links') => [link],
        ('POST', '/api/v1/memories/links') ||
        ('PUT', '/api/v1/memories/links/link-1') => link,
        ('PUT', '/api/v1/memories/memory-1/exclusion') ||
        ('PUT', '/api/v1/memories/memory-1/last-used') => memory,
        ('GET', '/api/v1/memories') => [memory],
        ('POST', '/api/v1/memories') ||
        ('PUT', '/api/v1/memories/memory-1') => memory,
        _ => null,
      };
      request.response.statusCode = switch (request.method) {
        'POST' => HttpStatus.created,
        'DELETE' => HttpStatus.noContent,
        _ => HttpStatus.ok,
      };
      if (result != null) request.response.write(jsonEncode(result));
      await request.response.close();
    });
    addTearDown(() async {
      await subscription.cancel();
      await server.close(force: true);
    });

    final service = MemoryApiService(
      client: LocalApiClient(
        baseUri: Uri(
          scheme: 'http',
          host: InternetAddress.loopbackIPv4.address,
          port: server.port,
        ),
      ),
    );
    final results = await service.list(
      query: 'luca & team',
      category: MemoryCategory.work,
      excluded: false,
    );
    final draft = const MemoryDraft(
      title: 'Riunione',
      content: 'Luca segue il progetto.',
      category: MemoryCategory.work,
      tags: ['local'],
      importance: 3,
    );
    final created = await service.create(draft);
    final updated = await service.update('memory-1', draft);
    await service.delete('memory-1');
    final graph = await service.graph(category: MemoryCategory.work);
    final links = await service.listLinks(memoryId: 'memory-1');
    final linkDraft = const MemoryLinkDraft(
      fromId: 'memory-1',
      toId: 'memory-2',
      relation: 'related to',
      strength: 2,
    );
    final createdLink = await service.createLink(linkDraft);
    final updatedLink = await service.updateLink('link-1', linkDraft);
    await service.deleteLink('link-1');
    final excluded = await service.setExcluded('memory-1', true);
    final used = await service.markUsed('memory-1');

    expect(results.single.category, MemoryCategory.work);
    expect(results.single.tags, ['local']);
    expect(created.title, 'Riunione');
    expect(updated.id, 'memory-1');
    expect(graph.nodes.single.id, 'memory-1');
    expect(graph.edges.single.id, 'link-1');
    expect(links.single.id, 'link-1');
    expect(createdLink.strength, 2);
    expect(updatedLink.relation, 'related to');
    expect(excluded.excluded, isFalse); // response fixture remains unchanged
    expect(used.sourceType, MemorySourceType.saved);
    expect(calls.map((call) => call.method), [
      'GET',
      'POST',
      'PUT',
      'DELETE',
      'GET',
      'GET',
      'POST',
      'PUT',
      'DELETE',
      'PUT',
      'PUT',
    ]);
    expect(calls.first.path, contains('q=luca+%26+team'));
    expect(calls.first.path, contains('category=work'));
    expect(calls.first.path, contains('excluded=false'));
    expect(jsonDecode(calls[1].body!)['source_type'], 'saved');
    expect(jsonDecode(calls[1].body!)['importance'], 3);
    expect(calls[4].path, contains('/api/v1/memories/graph'));
    expect(calls[6].path, '/api/v1/memories/links');
    expect(jsonDecode(calls[9].body!)['excluded'], isTrue);
    expect(calls[10].path, '/api/v1/memories/memory-1/last-used');
  });

  test(
    'maps offline network failures to a clear local-backend error',
    () async {
      final service = MemoryApiService(
        client: LocalApiClient(
          baseUri: Uri.parse('http://127.0.0.1:1'),
          timeout: const Duration(milliseconds: 100),
        ),
      );

      await expectLater(
        service.list(),
        throwsA(
          isA<LocalApiException>().having(
            (error) => error.statusCode,
            'statusCode',
            isNull,
          ),
        ),
      );
    },
  );
}
