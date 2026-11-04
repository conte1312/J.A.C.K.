import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:jack/app.dart';
import 'package:jack/models/memory.dart';
import 'package:jack/services/backend_status_service.dart';
import 'package:jack/services/local_api_client.dart';
import 'package:jack/services/memory_api_service.dart';

void main() {
  testWidgets('shows the workspace and disconnected backend state', (
    tester,
  ) async {
    _setDesktopViewport(tester);
    await tester.pumpWidget(
      JackApp(
        backendStatusReader: _FakeBackendReader(
          Future<BackendSnapshot?>.value(null),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Buon pomeriggio, Francesco.'), findsOneWidget);
    expect(find.text('DATI DEMO'), findsOneWidget);
    expect(find.text('Backend · offline'), findsOneWidget);
    expect(find.text('NON COLLEGATI'), findsOneWidget);
  });

  testWidgets('shows loading and connected backend states separately', (
    tester,
  ) async {
    _setDesktopViewport(tester);
    final response = Completer<BackendSnapshot?>();
    await tester.pumpWidget(
      JackApp(backendStatusReader: _FakeBackendReader(response.future)),
    );

    expect(find.text('Backend · verifica'), findsOneWidget);
    response.complete(
      const BackendSnapshot(
        name: 'J.A.C.K. Local Backend',
        version: '0.1.0',
        modules: ['health', 'info', 'memories'],
      ),
    );
    await tester.pump();
    await tester.pump();

    expect(find.text('Backend · connesso'), findsOneWidget);
    expect(find.text('NON COLLEGATI'), findsOneWidget);
  });

  testWidgets('adds submitted text to the local conversation', (tester) async {
    _setDesktopViewport(tester);
    await tester.pumpWidget(
      JackApp(
        backendStatusReader: _FakeBackendReader(
          Future<BackendSnapshot?>.value(null),
        ),
      ),
    );
    await tester.pump();

    await tester.enterText(
      find.byKey(const ValueKey('chat-input')),
      'Messaggio di prova',
    );
    await tester.tap(find.byKey(const ValueKey('send-message')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('Messaggio di prova'), findsOneWidget);
    expect(
      find.text('Messaggio aggiunto alla demo. Nessun modello AI è collegato.'),
      findsOneWidget,
    );
  });

  testWidgets('navigation shows the real memory offline state', (tester) async {
    _setDesktopViewport(tester);
    await tester.pumpWidget(
      JackApp(
        backendStatusReader: _FakeBackendReader(
          Future<BackendSnapshot?>.value(null),
        ),
        memoryRepository: _FakeMemoryRepository(
          const LocalApiException(
            message:
                'Backend locale offline. Avvia J.A.C.K. Backend e riprova.',
          ),
        ),
      ),
    );
    await tester.pump();

    await tester.tap(find.byKey(const ValueKey('nav-memory')));
    await tester.pumpAndSettle();

    expect(find.text('Backend locale offline'), findsOneWidget);
    expect(
      find.textContaining('salvati localmente su questo Mac'),
      findsOneWidget,
    );
    expect(find.byKey(const ValueKey('add-memory')), findsOneWidget);
    expect(
      tester
          .widget<OutlinedButton>(find.byKey(const ValueKey('add-memory')))
          .onPressed,
      isNull,
    );
  });
}

void _setDesktopViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(1440, 1000);
  tester.view.devicePixelRatio = 1;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

class _FakeBackendReader implements BackendStatusReader {
  const _FakeBackendReader(this.response);

  final Future<BackendSnapshot?> response;

  @override
  Future<BackendSnapshot?> check() => response;
}

class _FakeMemoryRepository implements MemoryRepository {
  const _FakeMemoryRepository(this.error);

  final LocalApiException error;

  @override
  Future<MemoryRecord> create(MemoryDraft draft) async => throw error;

  @override
  Future<void> delete(String id) async => throw error;

  @override
  Future<MemoryRecord> update(String id, MemoryDraft draft) async =>
      throw error;

  @override
  Future<List<MemoryRecord>> list({
    String? query,
    MemoryCategory? category,
    bool? excluded,
  }) async => throw error;

  @override
  Future<MemoryGraph> graph({
    String? query,
    MemoryCategory? category,
    bool? excluded,
  }) async => throw error;

  @override
  Future<List<MemoryLink>> listLinks({String? memoryId}) async => throw error;

  @override
  Future<MemoryLink> createLink(MemoryLinkDraft draft) async => throw error;

  @override
  Future<MemoryLink> updateLink(String id, MemoryLinkDraft draft) async =>
      throw error;

  @override
  Future<void> deleteLink(String id) async => throw error;

  @override
  Future<MemoryRecord> setExcluded(String id, bool excluded) async =>
      throw error;

  @override
  Future<MemoryRecord> markUsed(String id) async => throw error;
}
