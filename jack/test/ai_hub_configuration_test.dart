import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:jack/models/ai_hub_configuration.dart';
import 'package:jack/services/ai_hub_demo_repository.dart';

void main() {
  group('AiHubConfiguration', () {
    test('provides clearly separated demo providers and routes', () {
      final configuration = AiHubConfiguration.demoDefaults();

      expect(configuration.models, hasLength(4));
      expect(
        configuration.models.map((model) => model.provider).toSet(),
        containsAll(DemoAiProvider.values),
      );
      expect(configuration.defaultModel?.id, 'openai-gpt-4.1');
      expect(configuration.routes[AiHubTaskCategory.offline], 'local-llama');
      expect(
        configuration.models.every(
          (model) =>
              model.demoCostLabel.contains('demo') ||
              model.demoCostLabel.contains('dato demo'),
        ),
        isTrue,
      );
    });

    test('serializes and restores models, default and routing', () {
      final initial = AiHubConfiguration.demoDefaults();
      final restored = AiHubConfiguration.fromJson(
        jsonDecode(jsonEncode(initial.toJson())),
      );

      expect(restored.defaultModelId, initial.defaultModelId);
      expect(restored.routes, initial.routes);
      expect(restored.models.map((model) => model.id), [
        for (final model in initial.models) model.id,
      ]);
      expect(restored.models.last.demoQuotaLabel, 'sessione locale demo');
    });

    test('rejects invalid default and unassigned routing', () {
      final initial = AiHubConfiguration.demoDefaults();

      expect(
        () => initial.copyWith(defaultModelId: 'missing').validate(),
        throwsFormatException,
      );
      expect(
        () => initial
            .copyWith(
              routes: {...initial.routes}..remove(AiHubTaskCategory.vision),
            )
            .validate(),
        throwsFormatException,
      );
    });
  });

  group('AiHubDemoRepository', () {
    late Directory temporaryDirectory;
    late AiHubDemoRepository repository;

    setUp(() async {
      temporaryDirectory = await Directory.systemTemp.createTemp(
        'jack-ai-hub-test-',
      );
      repository = AiHubDemoRepository(
        file: File('${temporaryDirectory.path}/ai_hub_demo.json'),
      );
    });

    tearDown(() async {
      if (await temporaryDirectory.exists()) {
        await temporaryDirectory.delete(recursive: true);
      }
    });

    test('returns initial demo data when no local file exists', () async {
      final configuration = await repository.load();

      expect(configuration.models, hasLength(4));
      expect(
        await File('${temporaryDirectory.path}/ai_hub_demo.json').exists(),
        isFalse,
      );
    });

    test('saves and restores the local demo configuration', () async {
      final initial = AiHubConfiguration.demoDefaults();
      final changed = initial.copyWith(
        defaultModelId: 'anthropic-claude-sonnet',
        routes: {
          ...initial.routes,
          AiHubTaskCategory.coding: 'google-gemini-flash',
        },
      );

      await repository.save(changed);
      final restored = await repository.load();
      final stored = await File('${temporaryDirectory.path}/ai_hub_demo.json')
          .readAsString();

      expect(restored.defaultModelId, changed.defaultModelId);
      expect(restored.routes, changed.routes);
      expect(stored, contains('schemaVersion'));
      expect(stored, isNot(contains('apiKey')));
      expect(stored, isNot(contains('apiToken')));
    });

    test(
      'reports corrupted local data without silently replacing it',
      () async {
        final file = File('${temporaryDirectory.path}/ai_hub_demo.json');
        await file.writeAsString('{not valid json');

        await expectLater(
          repository.load(),
          throwsA(isA<AiHubStorageException>()),
        );
        expect(await file.readAsString(), '{not valid json');
      },
    );

    test('does not save an invalid configuration', () async {
      final invalid = AiHubConfiguration.demoDefaults().copyWith(
        defaultModelId: 'unknown-model',
      );

      await expectLater(repository.save(invalid), throwsFormatException);
      expect(
        await File('${temporaryDirectory.path}/ai_hub_demo.json').exists(),
        isFalse,
      );
    });
  });
}
