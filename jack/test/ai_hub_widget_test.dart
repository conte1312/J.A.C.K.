import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jack/app.dart';
import 'package:jack/models/ai_provider.dart';
import 'package:jack/services/ai_provider_service.dart';
import 'package:jack/services/backend_status_service.dart';

void main() {
  testWidgets('opens AI Hub and shows real provider panel', (
    tester,
  ) async {
    _setDesktopViewport(tester);
    final gateway = _FakeMultiProviderGateway();
    await _openAiHub(tester, gateway);

    expect(find.text('AI Hub'), findsOneWidget);
    expect(find.text('PROVIDER AI'), findsNWidgets(2));
    expect(find.text('ORDINE DI ROUTING'), findsOneWidget);
    expect(find.text('NVIDIA Nemotron'), findsAtLeastNWidgets(1));
    expect(tester.takeException(), isNull);
  });

  testWidgets('shows provider as unconfigured when no key is set', (
    tester,
  ) async {
    _setDesktopViewport(tester);
    final gateway = _FakeMultiProviderGateway(
      configured: false,
    );
    await _openAiHub(tester, gateway);

    expect(find.text('Da configurare'), findsOneWidget);
    expect(tester.takeException(), isNull);
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

    final gateway = _FakeMultiProviderGateway();
    await _openAiHub(tester, gateway);
    expect(find.text('AI Hub'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}

Future<void> _openAiHub(
  WidgetTester tester,
  AiProviderGateway gateway,
) async {
  await tester.pumpWidget(
    JackApp(
      backendStatusReader: _FakeBackendReader(),
      aiProviderGateway: gateway,
    ),
  );
  await tester.pump();
  await tester.pump();
  await tester.tap(find.byKey(const ValueKey('nav-modules')));
  await tester.pump();
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

class _FakeMultiProviderGateway implements AiProviderGateway {
  _FakeMultiProviderGateway({this.configured = true});

  final bool configured;

  static final _model = AiProviderModel(
    id: 'nvidia/nemotron-3.5-lightning-30b-a3b',
    name: 'Nemotron 3.5 Lightning 30B A3B',
    description: 'Modello Nemotron orientato a chat.',
    isFree: true,
    contextWindow: 16384,
    maxOutputTokens: 1024,
    enabled: true,
    selected: true,
    availabilityNote: 'Piano gratuito disponibile',
  );

  static final _provider = AiProviderInfo(
    id: 'nvidia',
    name: 'NVIDIA Nemotron',
    type: AiProviderType.online,
    baseUrl: 'https://integrate.api.nvidia.com/v1/chat/completions',
    requiresCredential: true,
    isFreeTierAvailable: true,
    configured: true,
    credentialSource: 'keychain',
    available: true,
    lastError: null,
    quotaExhausted: false,
    models: [_model],
    selectedProvider: true,
  );

  static final _routerConfig = AiRouterConfig(
    providerOrder: ['nvidia'],
    enabledProviders: ['nvidia'],
    maxRetriesPerProvider: 1,
    failoverEnabled: true,
  );

  static final _configuration = AiMultiProviderConfiguration(
    providers: [_provider],
    selectedProviderId: 'nvidia',
    selectedModelId: 'nvidia/nemotron-3.5-lightning-30b-a3b',
    providerOrder: ['nvidia'],
    enabledProviders: ['nvidia'],
    routerConfig: _routerConfig,
  );

  @override
  Future<AiMultiProviderConfiguration> loadProviderConfiguration() async {
    final config = _configuration;
    return AiMultiProviderConfiguration(
      providers: [
        for (final p in config.providers)
          AiProviderInfo(
            id: p.id,
            name: p.name,
            type: p.type,
            baseUrl: p.baseUrl,
            requiresCredential: p.requiresCredential,
            isFreeTierAvailable: p.isFreeTierAvailable,
            configured: configured,
            credentialSource: configured ? 'keychain' : null,
            available: p.available,
            lastError: p.lastError,
            quotaExhausted: p.quotaExhausted,
            models: p.models,
            selectedProvider: p.selectedProvider,
          ),
      ],
      selectedProviderId: configured ? 'nvidia' : null,
      selectedModelId: config.selectedModelId,
      providerOrder: config.providerOrder,
      enabledProviders: config.enabledProviders,
      routerConfig: config.routerConfig,
    );
  }

  @override
  Future<AiMultiProviderConfiguration> saveProviderApiKey(
    String providerId,
    String value,
  ) async =>
      _configuration;

  @override
  Future<AiMultiProviderConfiguration> removeProviderApiKey(
    String providerId,
  ) async =>
      _configuration;

  @override
  Future<AiMultiProviderConfiguration> testProviderConnection(
    String providerId,
    String modelId,
  ) async =>
      _configuration;

  @override
  Future<AiMultiProviderConfiguration> setProviderOrder(
    List<String> order,
  ) async =>
      _configuration;

  @override
  Future<AiMultiProviderConfiguration> setProviderEnabled(
    String providerId,
    bool enabled,
  ) async =>
      _configuration;

  @override
  Future<AiMultiProviderConfiguration> selectProviderAndModel(
    String providerId,
    String? modelId,
  ) async =>
      _configuration;

  @override
  Future<AiChatResponse> sendChat({
    required String? modelId,
    required List<AiChatTurn> messages,
  }) async =>
      AiChatResponse(
        providerId: 'nvidia',
        modelId: modelId ?? 'nvidia/nemotron-3.5-lightning-30b-a3b',
        content: 'Risposta di prova.',
      );
}
