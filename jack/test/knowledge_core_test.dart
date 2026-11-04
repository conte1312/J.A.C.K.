import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jack/widgets/knowledge_core.dart';

void main() {
  testWidgets('Knowledge Core repaints over time and disposes cleanly', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(360, 360);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      const MaterialApp(
        home: SizedBox(width: 360, height: 360, child: KnowledgeCore()),
      ),
    );

    const painterKey = ValueKey('knowledge-core-painter');
    final initialPainter = tester
        .widget<CustomPaint>(find.byKey(painterKey))
        .painter!;

    await tester.pump(const Duration(seconds: 2));
    final animatedPainter = tester
        .widget<CustomPaint>(find.byKey(painterKey))
        .painter!;
    expect(animatedPainter.shouldRepaint(initialPainter), isTrue);

    await tester.pumpWidget(const SizedBox.shrink());
    expect(tester.takeException(), isNull);
  });
}
