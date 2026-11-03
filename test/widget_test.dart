import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:jack/app.dart';

void main() {
  testWidgets('shows the J.A.C.K. conversation workspace', (tester) async {
    _setDesktopViewport(tester);
    await tester.pumpWidget(const JackApp());

    expect(find.text('Buon pomeriggio, Francesco.'), findsOneWidget);
    expect(find.text('DATI DEMO'), findsOneWidget);
    expect(find.text('NON COLLEGATI'), findsOneWidget);
  });

  testWidgets('adds submitted text to the conversation demo', (tester) async {
    _setDesktopViewport(tester);
    await tester.pumpWidget(const JackApp());

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

  testWidgets('navigation opens a coherent memory placeholder', (tester) async {
    _setDesktopViewport(tester);
    await tester.pumpWidget(const JackApp());

    await tester.tap(find.byKey(const ValueKey('nav-memory')));
    await tester.pump();

    expect(
      find.text('Consulta i nodi e le categorie di memoria di esempio.'),
      findsOneWidget,
    );
    expect(
      find.text('Nessun servizio è collegato in questa milestone.'),
      findsOneWidget,
    );
    expect(find.text('Torna alla conversazione'), findsOneWidget);
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
