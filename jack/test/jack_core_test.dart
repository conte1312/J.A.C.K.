import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jack/widgets/jack_core/jack_core.dart';
import 'package:jack/widgets/jack_core/jack_core_demo_data.dart';
import 'package:jack/widgets/jack_core/jack_core_graph.dart';
import 'package:jack/widgets/jack_core/jack_core_interaction.dart';
import 'package:jack/widgets/jack_core/jack_core_motion.dart';
import 'package:jack/widgets/jack_core/jack_core_painter.dart';
import 'package:jack/widgets/jack_core/jack_core_projection.dart';
import 'package:jack/widgets/jack_core/jack_core_state.dart';
import 'package:jack/widgets/jack_core/jack_core_visual_mapping.dart';

void main() {
  group('JackCore data and profiles', () {
    test('demo graph is explicit, neutral, and meets the Base44 baseline', () {
      expect(jackCoreDemoGraph.origin, JackCoreGraphOrigin.demo);
      expect(jackCoreDemoGraph.nodes, hasLength(12));
      expect(jackCoreDemoGraph.edges, hasLength(12));
      expect(jackCoreDemoGraph.validate(), isNull);
      expect(
        jackCoreDemoGraph.nodes.every(
          (node) =>
              node.id.startsWith('demo-') &&
              node.title.startsWith('Concetto dimostrativo') &&
              node.source == 'Dataset demo',
        ),
        isTrue,
      );
      expect(jackCoreDemoGraph.nodes.any((node) => node.excluded), isTrue);
    });

    test('every blueprint cognitive state has a centralized profile', () {
      expect(
        JackCoreMotionProfile.profiles.keys.toSet(),
        JackCognitiveState.values.toSet(),
      );
      final waiting = JackCoreMotionProfile.forState(
        JackCognitiveState.waiting,
      );
      final executing = JackCoreMotionProfile.forState(
        JackCognitiveState.executing,
      );
      final error = JackCoreMotionProfile.forState(JackCognitiveState.error);
      expect(waiting.spin, 0.028);
      expect(waiting.glow, 0.44);
      expect(executing.spin, 0.22);
      expect(executing.glow, 0.88);
      expect(error.jitter, 1);
      expect(jackCoreDefaultOrbits.map((orbit) => orbit.radius), [
        1.16,
        1.34,
        1.03,
        1.52,
      ]);
      expect(jackCoreDefaultOrbits.map((orbit) => orbit.opacity), [
        0.30,
        0.20,
        0.24,
        0.13,
      ]);
    });

    test('excluded nodes stay represented with reduced visual opacity', () {
      final visible = JackCoreVisualMapping.forNode(
        jackCoreDemoGraph.nodes.firstWhere((node) => !node.excluded),
      );
      final excluded = JackCoreVisualMapping.forNode(
        jackCoreDemoGraph.nodes.firstWhere((node) => node.excluded),
      );
      expect(excluded.opacity, lessThan(visible.opacity));
      expect(excluded.radius, greaterThan(0));
    });

    test('projection is deterministic and separates both visual shells', () {
      final first = JackCoreProjection.projectGraph(
        graph: jackCoreDemoGraph,
        size: const Size(360, 360),
        rotationX: 0,
        rotationY: 0,
        zoom: 1,
        baseScale: 0.36,
      );
      final second = JackCoreProjection.projectGraph(
        graph: jackCoreDemoGraph,
        size: const Size(360, 360),
        rotationX: 0,
        rotationY: 0,
        zoom: 1,
        baseScale: 0.36,
      );
      expect(
        first.nodes.map((node) => node.node.id),
        second.nodes.map((node) => node.node.id),
      );
      expect(
        first.nodes.map((node) => node.position),
        second.nodes.map((node) => node.position),
      );
      expect(
        jackCoreDemoGraph.nodes.map((node) => node.shell).toSet(),
        JackCoreShell.values.toSet(),
      );
    });
  });

  group('JackCore interactions', () {
    test('click movement below six pixels remains a selection gesture', () {
      final interaction = JackCoreInteraction();
      interaction.begin(
        const PointerDownEvent(
          pointer: 1,
          position: Offset(10, 10),
          buttons: kPrimaryMouseButton,
        ),
      );
      expect(
        interaction.end(
          const PointerUpEvent(
            pointer: 1,
            position: Offset(15, 10),
            kind: PointerDeviceKind.mouse,
          ),
        ),
        const Offset(15, 10),
      );
    });

    test('movement at six pixels rotates and no longer selects', () {
      final interaction = JackCoreInteraction();
      interaction.begin(
        const PointerDownEvent(
          pointer: 1,
          position: Offset.zero,
          buttons: kPrimaryMouseButton,
        ),
      );
      expect(
        interaction.move(
          const PointerMoveEvent(
            pointer: 1,
            position: Offset(6, 0),
            buttons: kPrimaryMouseButton,
          ),
        ),
        isTrue,
      );
      expect(interaction.rotationY, greaterThan(0));
      expect(
        interaction.end(
          const PointerUpEvent(
            pointer: 1,
            position: Offset(6, 0),
            kind: PointerDeviceKind.mouse,
          ),
        ),
        isNull,
      );
    });

    test('wheel zoom is clamped to the supported interval', () {
      final interaction = JackCoreInteraction();
      interaction.zoomBy(-1000);
      expect(interaction.zoom, JackCoreInteraction.maxZoom);
      interaction.zoomBy(1000);
      expect(interaction.zoom, JackCoreInteraction.minZoom);
    });
  });

  testWidgets('renders the demo graph, selects a node, and disposes', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(400, 400);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    String? selectedNodeId;
    await tester.pumpWidget(
      MaterialApp(
        home: Center(
          child: SizedBox.square(
            dimension: 360,
            child: JackCore(
              graph: jackCoreDemoGraph,
              reducedMotion: true,
              onNodeSelected: (node) => selectedNodeId = node.id,
            ),
          ),
        ),
      ),
    );

    final painterFinder = find.byKey(const ValueKey('jack-core-painter'));
    final initialPainter =
        tester.widget<CustomPaint>(painterFinder).painter! as JackCorePainter;
    expect(initialPainter.currentPhase, 0);
    expect(
      find.byKey(const ValueKey('jack-core-render-boundary')),
      findsOneWidget,
    );
    expect(tester.getSemantics(find.byType(JackCore)), isNotNull);

    final coreOrigin = tester.getTopLeft(painterFinder);
    final nodePosition = initialPainter
        .project(const Size(360, 360))
        .nodes
        .first
        .position;
    await tester.tapAt(coreOrigin + nodePosition);
    await tester.pump();
    expect(selectedNodeId, isNotNull);

    await tester.pumpWidget(const SizedBox.shrink());
    expect(tester.takeException(), isNull);
  });

  testWidgets('continuous idle motion repaints only the isolated core', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(400, 400);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      MaterialApp(
        home: SizedBox.square(
          dimension: 360,
          child: JackCore(graph: jackCoreDemoGraph, reducedMotion: false),
        ),
      ),
    );
    expect(tester.binding.hasScheduledFrame, isTrue);
    await tester.pump(const Duration(milliseconds: 250));
    expect(
      find.byKey(const ValueKey('jack-core-render-boundary')),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);

    await tester.pumpWidget(const SizedBox.shrink());
    expect(tester.takeException(), isNull);
  });
}
