import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jack/app.dart';
import 'package:jack/services/backend_status_service.dart';
import 'package:jack/widgets/jack_core/jack_core.dart';
import 'package:jack/widgets/jack_core/jack_core_demo_data.dart';
import 'package:jack/widgets/jack_core/jack_core_painter.dart';
import 'package:jack/widgets/jack_core/jack_core_preview_panel.dart';

void main() {
  testWidgets('empty node preview explains how to inspect the demo graph', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: Center(
              child: SizedBox(
                width: 340,
                child: JackCorePreviewPanel(
                  graph: jackCoreDemoGraph,
                  node: null,
                  onOpenInGraph: () {},
                ),
              ),
            ),
          ),
        ),
      ),
    );

    expect(find.text('ANTEPRIMA NODO'), findsOneWidget);
    expect(find.text('Nessun nodo selezionato'), findsOneWidget);
    expect(find.text('GRAFO DEMO'), findsOneWidget);
  });

  testWidgets('selected preview shows available fields and its actions', (
    tester,
  ) async {
    var opened = false;
    var cleared = false;
    final node = jackCoreDemoGraph.nodes.first;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: Center(
              child: SizedBox(
                width: 360,
                child: JackCorePreviewPanel(
                  graph: jackCoreDemoGraph,
                  node: node,
                  onOpenInGraph: () => opened = true,
                  onClearSelection: () => cleared = true,
                ),
              ),
            ),
          ),
        ),
      ),
    );

    expect(find.text(node.title), findsOneWidget);
    expect(find.text('Progetti'), findsOneWidget);
    expect(find.text('Memoria salvata'), findsOneWidget);
    expect(find.text('Dataset demo'), findsOneWidget);
    expect(find.text('Verificata'), findsOneWidget);
    expect(find.text('4 / 5'), findsOneWidget);
    expect(find.text('Incluso nel recupero'), findsOneWidget);
    expect(find.text('Non disponibile'), findsOneWidget);
    expect(find.text('Nessun tag'), findsOneWidget);
    expect(find.text('Concetto dimostrativo 02'), findsOneWidget);
    expect(
      find.text(
        'Informazioni dimostrative, non provenienti da memorie personali.',
      ),
      findsOneWidget,
    );

    final openButton = find.byKey(
      const ValueKey('open-selected-node-in-graph'),
    );
    await tester.ensureVisible(openButton);
    await tester.pump();
    await tester.tap(openButton);
    final clearButton = find.byKey(const ValueKey('clear-node-selection'));
    await tester.ensureVisible(clearButton);
    await tester.pump();
    await tester.tap(clearButton);
    expect(opened, isTrue);
    expect(cleared, isTrue);
  });

  testWidgets('selecting a node updates the rail without replacing JackCore', (
    tester,
  ) async {
    _setViewport(tester, const Size(1600, 1100));
    await tester.pumpWidget(
      JackApp(backendStatusReader: _OfflineBackendReader()),
    );
    await tester.pump();

    final coreFinder = find.byKey(const ValueKey('conversation-jack-core'));
    final painterFinder = find.byKey(const ValueKey('jack-core-painter'));
    final originalState = tester.state(coreFinder);
    final painter =
        tester.widget<CustomPaint>(painterFinder).painter! as JackCorePainter;
    final coreRect = tester.getRect(painterFinder);
    final node = painter.project(coreRect.size).nodes.first;

    await tester.tapAt(coreRect.topLeft + node.position);
    await tester.pump();

    expect(find.text(node.node.title), findsOneWidget);
    expect(identical(tester.state(coreFinder), originalState), isTrue);
    expect(find.text('GRAFO DEMO'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('clear-node-selection')));
    await tester.pump();
    expect(find.text('Nessun nodo selezionato'), findsOneWidget);
    expect(identical(tester.state(coreFinder), originalState), isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets('compact layout opens the preview as an end drawer', (
    tester,
  ) async {
    _setViewport(tester, const Size(1000, 800));
    await tester.pumpWidget(
      JackApp(backendStatusReader: _OfflineBackendReader()),
    );
    await tester.pump();

    expect(find.byKey(const ValueKey('open-node-preview')), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('open-node-preview')));
    await tester.pump(const Duration(milliseconds: 350));

    expect(find.text('ANTEPRIMA NODO'), findsOneWidget);
    expect(find.text('Nessun nodo selezionato'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('core selection opens its preview drawer on compact layouts', (
    tester,
  ) async {
    _setViewport(tester, const Size(1000, 800));
    await tester.pumpWidget(
      JackApp(backendStatusReader: _OfflineBackendReader()),
    );
    await tester.pump();

    final core = tester.widget<JackCore>(
      find.byKey(const ValueKey('conversation-jack-core')),
    );
    final selected = jackCoreDemoGraph.nodes.first;
    core.onNodeSelected!(selected);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 350));

    expect(
      tester
          .widget<JackCore>(
            find.byKey(const ValueKey('conversation-jack-core')),
          )
          .selectedNodeId,
      selected.id,
    );
    expect(find.byKey(const ValueKey('clear-node-selection')), findsOneWidget);
    expect(find.text(selected.title), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}

void _setViewport(WidgetTester tester, Size size) {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

class _OfflineBackendReader implements BackendStatusReader {
  @override
  Future<BackendSnapshot?> check() async => null;
}
