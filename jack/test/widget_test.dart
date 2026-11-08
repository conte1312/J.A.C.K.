import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:jack/app.dart';
import 'package:jack/models/ai_provider.dart';
import 'package:jack/models/conversation.dart';
import 'package:jack/models/memory.dart';
import 'package:jack/services/ai_provider_service.dart';
import 'package:jack/services/conversation_api_service.dart';
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
    expect(find.text('Backend · offline'), findsOneWidget);
    expect(find.text('UI'), findsOneWidget);
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
    expect(find.text('UI'), findsOneWidget);
  });

  testWidgets(
    'aggiunge il messaggio utente e segnala il backend offline',
    (tester) async {
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
      find.textContaining('Backend locale non disponibile'),
      findsOneWidget,
    );
    expect(find.text('Risposta di prova'), findsNothing);
  });

  testWidgets(
    'invia un messaggio al servizio AI e mostra la risposta reale',
    (tester) async {
    _setDesktopViewport(tester);
    final gateway = _FakeAiGateway(response: 'Risposta di prova di Nemotron.');
    final conversationRepository = _FakeConversationRepository(
      response: 'Risposta di prova di Nemotron.',
    );
    await tester.pumpWidget(
      JackApp(
        backendStatusReader: _FakeBackendReader(
          Future<BackendSnapshot?>.value(
            const BackendSnapshot(
              name: 'J.A.C.K. Local Backend',
              version: '0.1.0',
              modules: ['health', 'info', 'memories'],
            ),
          ),
        ),
        aiProviderGateway: gateway,
        conversationRepository: conversationRepository,
      ),
    );
    await tester.pump();
    await tester.pump();

    await tester.enterText(
      find.byKey(const ValueKey('chat-input')),
      'Ciao J.A.C.K.',
    );
    await tester.tap(find.byKey(const ValueKey('send-message')));
    await tester.pump();
    await tester.pump();

    expect(find.text('Ciao J.A.C.K.'), findsOneWidget);
    expect(find.text('Risposta di prova di Nemotron.'), findsOneWidget);
    expect(find.textContaining('NEMOTRON'), findsOneWidget);
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

class _FakeAiGateway implements AiProviderGateway {
  const _FakeAiGateway({required this.response});

  final String response;

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
  Future<AiMultiProviderConfiguration> loadProviderConfiguration() async =>
      _configuration;

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
        content: response,
      );
}

class _FakeConversationRepository implements ConversationRepository {
  const _FakeConversationRepository({required this.response});

  final String response;

  @override
  Future<List<Conversation>> listConversations() async => [];

  @override
  Future<Conversation> createConversation(ConversationDraft draft) async =>
      Conversation(
        id: 'conv-test-1',
        title: draft.title,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
        providerId: draft.providerId,
        modelId: draft.modelId,
        metadata: draft.metadata ?? {},
        messageCount: 0,
      );

  @override
  Future<ConversationWithMessages?> getConversation(String id) async => null;

  @override
  Future<Conversation> renameConversation(String id, String title) async =>
      Conversation(
        id: id,
        title: title,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
        messageCount: 0,
      );

  @override
  Future<void> deleteConversation(String id) async {}

  @override
  Future<ConversationMessage> addMessage(
    String conversationId,
    ConversationMessageDraft draft,
  ) async =>
      ConversationMessage(
        id: 'msg-test-1',
        conversationId: conversationId,
        role: draft.role,
        content: draft.content,
        createdAt: DateTime.now(),
        isDemo: draft.isDemo,
        providerLabel: draft.providerLabel,
      );

  @override
  Future<AiConversationResponse> chatInConversation({
    required String conversationId,
    required String modelId,
    required List<ConversationMessage> messages,
  }) async =>
      AiConversationResponse(
        providerId: 'nvidia',
        modelId: modelId,
        content: response,
      );
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
