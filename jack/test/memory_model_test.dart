import 'package:flutter_test/flutter_test.dart';
import 'package:jack/models/memory.dart';

void main() {
  final timestamp = DateTime.utc(2026, 11, 4, 10).toIso8601String();

  test('MemoryRecord reads complete metadata and legacy category aliases', () {
    final memory = MemoryRecord.fromJson({
      'id': 'memory-1',
      'title': 'Neutral example',
      'content': 'No personal information.',
      'category': 'personale',
      'source_type': 'retrieved',
      'source': null,
      'verification': 'inferred',
      'tags': ['sample'],
      'importance': 4,
      'excluded': true,
      'conversation_id': 'conversation-1',
      'last_used': timestamp,
      'created_at': timestamp,
      'updated_at': timestamp,
    });

    expect(memory.category, MemoryCategory.identity);
    expect(memory.sourceType, MemorySourceType.retrieved);
    expect(memory.source, isNull);
    expect(memory.verification, MemoryVerification.inferred);
    expect(memory.tags, ['sample']);
    expect(memory.importance, 4);
    expect(memory.excluded, isTrue);
    expect(memory.conversationId, 'conversation-1');
    expect(memory.lastUsed, DateTime.parse(timestamp));
  });

  test('old memory responses still deserialize with conservative defaults', () {
    final memory = MemoryRecord.fromJson({
      'id': 'legacy-1',
      'title': 'Old record',
      'content': 'Preserved content.',
      'category': 'note',
      'created_at': timestamp,
      'updated_at': timestamp,
    });

    expect(memory.category, MemoryCategory.other);
    expect(memory.sourceType, MemorySourceType.saved);
    expect(memory.verification, MemoryVerification.toVerify);
    expect(memory.source, isNull);
    expect(memory.importance, 3);
    expect(memory.tags, isEmpty);
  });

  test('draft and link serialization use the API schema', () {
    const memory = MemoryDraft(
      title: 'Concept',
      content: 'Neutral sample.',
      category: MemoryCategory.technical,
      sourceType: MemorySourceType.inference,
      source: 'manual fixture',
      verification: MemoryVerification.toVerify,
      tags: ['sample'],
      importance: 2,
      excluded: true,
      conversationId: 'conversation-2',
    );
    expect(memory.toJson(), {
      'title': 'Concept',
      'content': 'Neutral sample.',
      'category': 'technical',
      'source_type': 'inference',
      'source': 'manual fixture',
      'verification': 'to_verify',
      'tags': ['sample'],
      'importance': 2,
      'excluded': true,
      'conversation_id': 'conversation-2',
    });

    const link = MemoryLinkDraft(
      fromId: 'a',
      toId: 'b',
      relation: 'related to',
      strength: 3,
    );
    expect(link.toJson(), {
      'from_id': 'a',
      'to_id': 'b',
      'relation': 'related to',
      'strength': 3,
    });
  });

  test('MemoryGraph deserializes node and edge collections', () {
    final graph = MemoryGraph.fromJson({
      'nodes': [
        {
          'id': 'memory-1',
          'title': 'Node A',
          'content': 'A',
          'category': 'work',
          'source_type': 'saved',
          'source': 'user_entry',
          'verification': 'to_verify',
          'tags': [],
          'importance': 3,
          'excluded': false,
          'conversation_id': null,
          'last_used': null,
          'created_at': timestamp,
          'updated_at': timestamp,
        },
      ],
      'edges': [
        {
          'id': 'link-1',
          'from_id': 'memory-1',
          'to_id': 'memory-2',
          'relation': 'related to',
          'strength': 2,
          'created_at': timestamp,
        },
      ],
    });

    expect(graph.nodes.single.category, MemoryCategory.work);
    expect(graph.edges.single.toId, 'memory-2');
    expect(graph.edges.single.strength, 2);
  });

  test('invalid importance and link strength are rejected', () {
    expect(
      () => MemoryRecord.fromJson({
        'id': 'memory-1',
        'title': 'Bad',
        'content': 'Invalid importance.',
        'category': 'other',
        'importance': 6,
        'created_at': timestamp,
        'updated_at': timestamp,
      }),
      throwsFormatException,
    );
    expect(
      () => MemoryLink.fromJson({
        'id': 'link-1',
        'from_id': 'a',
        'to_id': 'b',
        'relation': 'bad strength',
        'strength': 4,
        'created_at': timestamp,
      }),
      throwsFormatException,
    );
  });
}
