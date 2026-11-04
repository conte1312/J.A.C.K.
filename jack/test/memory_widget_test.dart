import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jack/app.dart';
import 'package:jack/models/memory.dart';
import 'package:jack/services/backend_status_service.dart';
import 'package:jack/services/local_api_client.dart';
import 'package:jack/services/memory_api_service.dart';

void main() {
  testWidgets('creates, edits and deletes a locally saved memory', (
    tester,
  ) async {
    _setDesktopViewport(tester);
    final repository = _MemoryRepository();
    await _openMemory(tester, repository);

    expect(find.text('Ancora nessun ricordo salvato.'), findsOneWidget);
    expect(find.text('DATI DEMO'), findsNothing);

    await tester.tap(find.byKey(const ValueKey('add-memory')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('save-memory')));
    await tester.pumpAndSettle();
    expect(find.text('Inserisci un titolo.'), findsOneWidget);
    expect(find.text('Inserisci il contenuto del ricordo.'), findsOneWidget);

    await tester.enterText(
      find.byKey(const ValueKey('memory-title-field')),
      'Preparazione riunione',
    );
    await tester.enterText(
      find.byKey(const ValueKey('memory-content-field')),
      'Luca porta i dati del progetto.',
    );
    await tester.tap(find.byKey(const ValueKey('memory-category-field')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Lavoro').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('save-memory')));
    await tester.pumpAndSettle();

    expect(repository.memories, hasLength(1));
    expect(find.text('Preparazione riunione'), findsOneWidget);
    expect(find.text('Lavoro'), findsOneWidget);

    final memory = repository.memories.single;
    await tester.tap(find.byKey(ValueKey('edit-memory-${memory.id}')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('memory-title-field')),
      'Riunione aggiornata',
    );
    await tester.enterText(
      find.byKey(const ValueKey('memory-content-field')),
      'Le metriche sono pronte per la revisione.',
    );
    await tester.tap(find.byKey(const ValueKey('save-memory')));
    await tester.pumpAndSettle();

    expect(repository.memories.single.title, 'Riunione aggiornata');
    expect(find.text('Riunione aggiornata'), findsOneWidget);

    await tester.tap(find.byKey(ValueKey('delete-memory-${memory.id}')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('confirm-delete-memory')));
    await tester.pumpAndSettle();
    expect(repository.memories, isEmpty);
    expect(find.text('Ancora nessun ricordo salvato.'), findsOneWidget);
  });

  testWidgets(
    'searches and filters memories and preserves the last list offline',
    (tester) async {
      _setDesktopViewport(tester);
      final repository = _MemoryRepository(
        memories: [
          _memory(
            '1',
            'Riunione prodotto',
            'Giulia porta le metriche.',
            MemoryCategory.lavoro,
          ),
          _memory(
            '2',
            'Progetto Atlas',
            'Giulia coordina il progetto.',
            MemoryCategory.progetti,
          ),
          _memory(
            '3',
            'Nota personale',
            'Ricordare la spesa.',
            MemoryCategory.personale,
          ),
        ],
      );
      await _openMemory(tester, repository);

      await tester.enterText(
        find.byKey(const ValueKey('memory-search')),
        'Giulia',
      );
      await tester.pump(const Duration(milliseconds: 350));
      await tester.pump();
      expect(find.text('Riunione prodotto'), findsOneWidget);
      expect(find.text('Progetto Atlas'), findsOneWidget);
      expect(find.text('Nota personale'), findsNothing);
      expect(repository.lastQuery, 'Giulia');

      await tester.enterText(find.byKey(const ValueKey('memory-search')), '');
      await tester.pump(const Duration(milliseconds: 350));
      await tester.pump();
      await tester.tap(find.byKey(const ValueKey('memory-category-filter')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Progetti').last);
      await tester.pumpAndSettle();
      expect(find.text('Progetto Atlas'), findsOneWidget);
      expect(find.text('Riunione prodotto'), findsNothing);
      expect(repository.lastCategory, MemoryCategory.progetti);

      repository.offline = true;
      await tester.enterText(
        find.byKey(const ValueKey('memory-search')),
        'server down',
      );
      await tester.pump(const Duration(milliseconds: 350));
      await tester.pump();
      expect(find.text('Progetto Atlas'), findsOneWidget);
      expect(
        find.textContaining('Ultimo elenco caricato mantenuto sullo schermo'),
        findsOneWidget,
      );
      expect(
        tester
            .widget<OutlinedButton>(find.byKey(const ValueKey('add-memory')))
            .onPressed,
        isNull,
      );
    },
  );

  testWidgets('shows a clear offline state without pretending to save', (
    tester,
  ) async {
    _setDesktopViewport(tester);
    final repository = _MemoryRepository(offline: true);
    await _openMemory(tester, repository);

    expect(find.text('Backend locale offline'), findsOneWidget);
    expect(
      find.textContaining('Nessuna sincronizzazione cloud'),
      findsOneWidget,
    );
    expect(
      tester
          .widget<OutlinedButton>(find.byKey(const ValueKey('add-memory')))
          .onPressed,
      isNull,
    );
    expect(repository.memories, isEmpty);
  });

}

Future<void> _openMemory(
  WidgetTester tester,
  _MemoryRepository repository,
) async {
  await tester.pumpWidget(
    JackApp(
      backendStatusReader: _FakeBackendReader(),
      memoryRepository: repository,
    ),
  );
  await tester.pump();
  await tester.tap(find.byKey(const ValueKey('nav-memory')));
  await tester.pump();
  await tester.pump();
}

void _setDesktopViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(1440, 1000);
  tester.view.devicePixelRatio = 1;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

MemoryRecord _memory(
  String id,
  String title,
  String content,
  MemoryCategory category,
) {
  final time = DateTime.utc(2026, 11, 3, 12);
  return MemoryRecord(
    id: id,
    title: title,
    content: content,
    category: category,
    createdAt: time,
    updatedAt: time,
  );
}

class _FakeBackendReader implements BackendStatusReader {
  @override
  Future<BackendSnapshot?> check() async => null;
}

class _MemoryRepository implements MemoryRepository {
  _MemoryRepository({
    List<MemoryRecord> memories = const [],
    this.offline = false,
  }) : memories = List.of(memories);

  final List<MemoryRecord> memories;
  final List<MemoryLink> links = [];
  bool offline;
  String? lastQuery;
  MemoryCategory? lastCategory;
  int _nextId = 100;

  void _ensureOnline() {
    if (offline) {
      throw const LocalApiException(
        message: 'Backend locale offline. Avvia J.A.C.K. Backend e riprova.',
      );
    }
  }

  @override
  Future<List<MemoryRecord>> list({
    String? query,
    MemoryCategory? category,
    bool? excluded,
  }) async {
    _ensureOnline();
    lastQuery = query;
    lastCategory = category;
    return memories
        .where((memory) {
          if (category != null && memory.category != category) return false;
          if (excluded != null && memory.excluded != excluded) return false;
          final term = query?.trim().toLowerCase() ?? '';
          if (term.isEmpty) return true;
          return memory.title.toLowerCase().contains(term) ||
              memory.content.toLowerCase().contains(term);
        })
        .toList(growable: false);
  }

  @override
  Future<MemoryRecord> create(MemoryDraft draft) async {
    _ensureOnline();
    final now = DateTime.now().toUtc();
    final memory = MemoryRecord(
      id: '${_nextId++}',
      title: draft.title,
      content: draft.content,
      category: draft.category,
      sourceType: draft.sourceType,
      source: draft.source,
      verification: draft.verification,
      tags: draft.tags,
      importance: draft.importance,
      excluded: draft.excluded,
      conversationId: draft.conversationId,
      createdAt: now,
      updatedAt: now,
    );
    memories.add(memory);
    return memory;
  }

  @override
  Future<void> delete(String id) async {
    _ensureOnline();
    memories.removeWhere((memory) => memory.id == id);
  }

  @override
  Future<MemoryRecord> update(String id, MemoryDraft draft) async {
    _ensureOnline();
    final index = memories.indexWhere((memory) => memory.id == id);
    if (index == -1) {
      throw const LocalApiException(
        statusCode: 404,
        message: 'Il ricordo richiesto non è stato trovato.',
      );
    }
    final previous = memories[index];
    final updated = MemoryRecord(
      id: id,
      title: draft.title,
      content: draft.content,
      category: draft.category,
      sourceType: draft.sourceType,
      source: draft.source,
      verification: draft.verification,
      tags: draft.tags,
      importance: draft.importance,
      excluded: draft.excluded,
      conversationId: draft.conversationId,
      lastUsed: previous.lastUsed,
      createdAt: previous.createdAt,
      updatedAt: DateTime.now().toUtc(),
    );
    memories[index] = updated;
    return updated;
  }

  @override
  Future<MemoryGraph> graph({
    String? query,
    MemoryCategory? category,
    bool? excluded,
  }) async {
    final nodes = await list(
      query: query,
      category: category,
      excluded: excluded,
    );
    final nodeIds = nodes.map((node) => node.id).toSet();
    return MemoryGraph(
      nodes: nodes,
      edges: links
          .where(
            (link) =>
                nodeIds.contains(link.fromId) && nodeIds.contains(link.toId),
          )
          .toList(growable: false),
    );
  }

  @override
  Future<List<MemoryLink>> listLinks({String? memoryId}) async => links
      .where(
        (link) =>
            memoryId == null ||
            link.fromId == memoryId ||
            link.toId == memoryId,
      )
      .toList(growable: false);

  @override
  Future<MemoryLink> createLink(MemoryLinkDraft draft) async {
    _ensureOnline();
    final link = MemoryLink(
      id: 'link-${links.length + 1}',
      fromId: draft.fromId,
      toId: draft.toId,
      relation: draft.relation,
      strength: draft.strength,
      createdAt: DateTime.now().toUtc(),
    );
    links.add(link);
    return link;
  }

  @override
  Future<MemoryLink> updateLink(String id, MemoryLinkDraft draft) async {
    _ensureOnline();
    final index = links.indexWhere((link) => link.id == id);
    if (index < 0) throw StateError('Missing link');
    final previous = links[index];
    final link = MemoryLink(
      id: id,
      fromId: draft.fromId,
      toId: draft.toId,
      relation: draft.relation,
      strength: draft.strength,
      createdAt: previous.createdAt,
    );
    links[index] = link;
    return link;
  }

  @override
  Future<void> deleteLink(String id) async {
    _ensureOnline();
    links.removeWhere((link) => link.id == id);
  }

  @override
  Future<MemoryRecord> setExcluded(String id, bool excluded) async {
    _ensureOnline();
    return _replace(id, excluded: excluded);
  }

  @override
  Future<MemoryRecord> markUsed(String id) async {
    _ensureOnline();
    return _replace(id, lastUsed: DateTime.now().toUtc());
  }

  MemoryRecord _replace(String id, {bool? excluded, DateTime? lastUsed}) {
    final index = memories.indexWhere((memory) => memory.id == id);
    if (index < 0) throw StateError('Missing memory');
    final previous = memories[index];
    final updated = MemoryRecord(
      id: previous.id,
      title: previous.title,
      content: previous.content,
      category: previous.category,
      sourceType: previous.sourceType,
      source: previous.source,
      verification: previous.verification,
      tags: previous.tags,
      importance: previous.importance,
      excluded: excluded ?? previous.excluded,
      conversationId: previous.conversationId,
      lastUsed: lastUsed ?? previous.lastUsed,
      createdAt: previous.createdAt,
      updatedAt: DateTime.now().toUtc(),
    );
    memories[index] = updated;
    return updated;
  }
}
