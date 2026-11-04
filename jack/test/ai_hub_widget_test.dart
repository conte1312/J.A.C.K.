import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jack/app.dart';
import 'package:jack/models/ai_hub_configuration.dart';
import 'package:jack/services/ai_hub_demo_repository.dart';
import 'package:jack/services/backend_status_service.dart';

void main() {
  testWidgets('opens AI Hub and labels providers and routing as demo', (
    tester,
  ) async {
    _setDesktopViewport(tester);
    final repository = _MemoryAiHubRepository(
      AiHubConfiguration.demoDefaults(),
    );
    await _openAiHub(tester, repository);

    expect(find.text('AI Hub'), findsOneWidget);
    expect(find.text('GPT-4.1'), findsOneWidget);
    expect(find.textContaining('provider non collegato'), findsNWidgets(4));
    expect(find.text('SIMULATO'), findsOneWidget);
    expect(find.text('NESSUNA CHIAMATA AI'), findsOneWidget);
    expect(find.text('DATI DI ESEMPIO'), findsOneWidget);
    expect(find.text('Backend · offline'), findsOneWidget);
  });

  testWidgets('validates and adds a demo model', (tester) async {
    _setDesktopViewport(tester);
    final repository = _MemoryAiHubRepository(
      AiHubConfiguration.demoDefaults(),
    );
    await _openAiHub(tester, repository);

    await tester.ensureVisible(find.byKey(const ValueKey('add-ai-model')));
    await tester.tap(find.byKey(const ValueKey('add-ai-model')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('save-demo-model')));
    await tester.pumpAndSettle();
    expect(find.text('Inserisci il nome del modello.'), findsOneWidget);

    await tester.enterText(
      find.byKey(const ValueKey('model-name-field')),
      'J.A.C.K. Demo Local',
    );
    await tester.tap(find.byKey(const ValueKey('save-demo-model')));
    await tester.pumpAndSettle();

    expect(find.text('J.A.C.K. Demo Local'), findsOneWidget);
    expect(repository.configuration.models, hasLength(5));
  });

  testWidgets('edits, selects default, changes route and removes a model', (
    tester,
  ) async {
    _setDesktopViewport(tester);
    final repository = _MemoryAiHubRepository(
      AiHubConfiguration.demoDefaults(),
    );
    await _openAiHub(tester, repository);

    await tester.ensureVisible(
      find.byKey(const ValueKey('edit-ai-model-openai-gpt-4.1')),
    );
    await tester.tap(
      find.byKey(const ValueKey('edit-ai-model-openai-gpt-4.1')),
    );
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('model-name-field')),
      'GPT demo modificato',
    );
    await tester.tap(find.byKey(const ValueKey('save-demo-model')));
    await tester.pumpAndSettle();
    expect(find.text('GPT demo modificato'), findsOneWidget);

    await tester.ensureVisible(
      find.byKey(const ValueKey('set-default-model-anthropic-claude-sonnet')),
    );
    await tester.tap(
      find.byKey(const ValueKey('set-default-model-anthropic-claude-sonnet')),
    );
    await tester.pumpAndSettle();
    expect(repository.configuration.defaultModelId, 'anthropic-claude-sonnet');

    await tester.ensureVisible(
      find.byKey(const ValueKey('routing-select-vision')),
    );
    await tester.tap(find.byKey(const ValueKey('routing-select-vision')));
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(
        const ValueKey('routing-choice-vision-openai-gpt-4.1'),
        skipOffstage: false,
      ),
    );
    await tester.pumpAndSettle();
    expect(
      repository.configuration.routes[AiHubTaskCategory.vision],
      'openai-gpt-4.1',
    );

    await tester.ensureVisible(
      find.byKey(const ValueKey('remove-ai-model-google-gemini-flash')),
    );
    await tester.tap(
      find.byKey(const ValueKey('remove-ai-model-google-gemini-flash')),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('confirm-remove-model')));
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey('ai-model-card-google-gemini-flash')),
      findsNothing,
    );
    expect(repository.configuration.models, hasLength(3));
    expect(
      repository.configuration.routes[AiHubTaskCategory.vision],
      'openai-gpt-4.1',
    );
  });

  testWidgets('keeps the AI Hub usable in a compact desktop window', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(880, 720);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await _openAiHub(
      tester,
      _MemoryAiHubRepository(AiHubConfiguration.demoDefaults()),
    );
    expect(find.text('AI Hub'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}

Future<void> _openAiHub(
  WidgetTester tester,
  AiHubDemoRepository repository,
) async {
  await tester.pumpWidget(
    JackApp(
      backendStatusReader: _FakeBackendReader(),
      aiHubRepository: repository,
    ),
  );
  await tester.pump();
  await tester.tap(find.byKey(const ValueKey('nav-modules')));
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

class _FakeBackendReader implements BackendStatusReader {
  @override
  Future<BackendSnapshot?> check() async => null;
}

class _MemoryAiHubRepository extends AiHubDemoRepository {
  _MemoryAiHubRepository(this.configuration)
    : super(file: File('/unused/ai-hub-test.json'));

  AiHubConfiguration configuration;

  @override
  Future<AiHubConfiguration> load() async => configuration;

  @override
  Future<void> save(AiHubConfiguration next) async {
    next.validate();
    configuration = next;
  }
}
