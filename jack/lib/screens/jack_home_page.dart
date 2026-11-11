import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../models/ai_provider.dart';
import '../models/chat_message.dart';
import '../models/conversation.dart';
import '../models/memory.dart';
import '../models/jack_section.dart';
import '../screens/ai_hub_screen.dart';
import '../services/ai_provider_service.dart';
import '../services/backend_status_service.dart';
import '../services/conversation_api_service.dart';
import '../services/local_api_client.dart';
import '../services/memory_api_service.dart';
import '../theme/jack_theme.dart';
import '../widgets/chat_panel.dart';
import '../widgets/jack_primitives.dart';
import '../widgets/jack_sidebar.dart';
import '../widgets/jack_top_bar.dart';
import '../widgets/jack_core/jack_core.dart';
import '../widgets/jack_core/jack_core_graph.dart';
import '../widgets/jack_core/jack_core_preview_panel.dart';
import '../widgets/jack_core/jack_core_state.dart';
import 'memory_screen.dart';
import '../widgets/right_rail.dart';

class JackHomePage extends StatefulWidget {
  const JackHomePage({
    this.backendStatusReader,
    this.memoryRepository,
    this.aiProviderGateway,
    this.conversationRepository,
    super.key,
  });

  final BackendStatusReader? backendStatusReader;
  final MemoryRepository? memoryRepository;
  final AiProviderGateway? aiProviderGateway;
  final ConversationRepository? conversationRepository;

  @override
  State<JackHomePage> createState() => _JackHomePageState();
}

class _JackHomePageState extends State<JackHomePage> {
  late final BackendStatusReader _backendReader;
  late final AiProviderGateway _aiGateway;
  late final ConversationRepository _conversationRepository;
  Timer? _backendPollTimer;
  BackendConnectionState _backendState = BackendConnectionState.loading;
  BackendSnapshot? _backendSnapshot;
  bool _backendCheckInProgress = false;

  AiMultiProviderConfiguration? _aiConfiguration;
  String? _aiError;
  bool _aiLoading = true;

  final _inputController = TextEditingController();
  final _messageScrollController = ScrollController();
  final _scaffoldKey = GlobalKey<ScaffoldState>();
  final ValueNotifier<JackCoreNode?> _selectedCoreNode = ValueNotifier(null);

  JackSection _selectedSection = JackSection.conversations;
  bool _isListening = false;
  bool _isSending = false;

  List<Conversation> _conversations = [];
  JackCoreGraph? _liveGraph;
  bool _graphLoading = false;
  String? _activeConversationId;
  ConversationWithMessages? _activeConversationWithMessages;
  bool _conversationsLoading = true;

  @override
  void initState() {
    super.initState();
    _backendReader = widget.backendStatusReader ?? BackendStatusService();
    _aiGateway = widget.aiProviderGateway ?? AiProviderService();
    _conversationRepository =
        widget.conversationRepository ?? ConversationApiService();
    WidgetsBinding.instance.addPostFrameCallback((_) => _refreshBackend());
    unawaited(_loadAiConfiguration());
    unawaited(_loadConversations());
    _backendPollTimer = Timer.periodic(
      const Duration(seconds: 5),
      (_) => _refreshBackend(),
    );
  }

  void _refreshBackend({bool showLoading = false}) {
    if (_backendCheckInProgress) return;
    _backendCheckInProgress = true;
    if (showLoading && mounted) {
      setState(() => _backendState = BackendConnectionState.loading);
    }
    unawaited(_loadBackend());
  }

  Future<void> _loadBackend() async {
    BackendSnapshot? snapshot;
    try {
      snapshot = await _backendReader.check();
    } catch (_) {
      snapshot = null;
    }

    _backendCheckInProgress = false;
    if (!mounted) return;
    setState(() {
      _backendSnapshot = snapshot;
      _backendState = snapshot == null
          ? BackendConnectionState.disconnected
          : BackendConnectionState.connected;
    });
    if (snapshot != null && _aiConfiguration == null) {
      unawaited(_loadAiConfiguration());
    }
    if (snapshot != null && _conversations.isEmpty && !_conversationsLoading) {
      unawaited(_loadConversations());
    }
    if (snapshot != null && _liveGraph == null && !_graphLoading) {
      unawaited(_loadLiveGraph());
    }
  }

  Future<void> _loadConversations() async {
    if (mounted) {
      setState(() => _conversationsLoading = true);
    }
    try {
      final conversations = await _conversationRepository.listConversations();
      if (!mounted) return;
      setState(() {
        _conversations = conversations;
        _conversationsLoading = false;
      });
    } on LocalApiException catch (_) {
      if (!mounted) return;
      setState(() {
        _conversationsLoading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() => _conversationsLoading = false);
    }
  }

  Future<void> _loadLiveGraph() async {
    if (widget.memoryRepository == null) return;
    if (mounted) {
      setState(() => _graphLoading = true);
    }
    try {
      final graph = await widget.memoryRepository!.graph();
      if (!mounted) return;
      setState(() {
        _liveGraph = _memoryGraphToJackCoreGraph(graph);
        _graphLoading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() => _graphLoading = false);
    }
  }

  JackCoreGraph _memoryGraphToJackCoreGraph(MemoryGraph graph) {
    final nodes = graph.nodes.map((memory) {
      return JackCoreNode(
        id: memory.id,
        title: memory.title,
        content: memory.content,
        category: _memoryCategoryToJackCore(memory.category),
        sourceType: _memorySourceTypeToJackCore(memory.sourceType),
        source: memory.source ?? 'Memoria locale',
        verification: _memoryVerificationToJackCore(memory.verification),
        tags: memory.tags,
        importance: memory.importance,
        excluded: memory.excluded,
        conversationId: memory.conversationId,
        lastUsed: memory.lastUsed,
        shell: memory.excluded
            ? JackCoreShell.surface
            : JackCoreShell.interior,
      );
    }).toList(growable: false);
    final edges = graph.edges.map((link) {
      return JackCoreEdge(
        id: link.id,
        fromId: link.fromId,
        toId: link.toId,
        relation: link.relation,
        strength: link.strength,
      );
    }).toList(growable: false);
    return JackCoreGraph(
      nodes: nodes,
      edges: edges,
      origin: JackCoreGraphOrigin.live,
    );
  }

  JackCoreCategory _memoryCategoryToJackCore(MemoryCategory category) {
    return JackCoreCategory.values.firstWhere(
      (c) => c.name == category.name,
      orElse: () => JackCoreCategory.other,
    );
  }

  JackCoreSourceType _memorySourceTypeToJackCore(
    MemorySourceType sourceType,
  ) {
    return JackCoreSourceType.values.firstWhere(
      (s) => s.name == sourceType.name,
      orElse: () => JackCoreSourceType.saved,
    );
  }

  JackCoreVerification _memoryVerificationToJackCore(
    MemoryVerification verification,
  ) {
    return JackCoreVerification.values.firstWhere(
      (v) => v.name == verification.name,
      orElse: () => JackCoreVerification.toVerify,
    );
  }

  Future<void> _loadAiConfiguration() async {
    if (mounted) {
      setState(() {
        _aiLoading = true;
        _aiError = null;
      });
    }
    try {
      final configuration = await _aiGateway.loadProviderConfiguration();
      if (!mounted) return;
      setState(() {
        _aiConfiguration = configuration;
        _aiLoading = false;
      });
    } on LocalApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _aiError = error.message;
        _aiLoading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() {
        _aiError = 'Impossibile leggere la configurazione AI dal backend.';
        _aiLoading = false;
      });
    }
  }

  bool get _aiAvailable =>
      _backendState == BackendConnectionState.connected &&
      _aiConfiguration != null &&
      _aiConfiguration!.selectedProvider != null &&
      _aiConfiguration!.selectedProvider!.configured &&
      _aiConfiguration!.selectedModel != null;

  bool get _noProvidersConfigured =>
      _backendState == BackendConnectionState.connected &&
      _aiConfiguration != null &&
      _aiConfiguration!.providers.isNotEmpty &&
      !_aiConfiguration!.providers.any((p) => p.configured);

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_messageScrollController.hasClients) return;
      _messageScrollController.animateTo(
        _messageScrollController.position.minScrollExtent,
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOut,
      );
    });
  }

  void _showChatError({
    required String message,
    String? retryText,
    VoidCallback? onRetry,
  }) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: const Color(0xFF572D2B),
          duration: const Duration(seconds: 4),
          action: onRetry != null
              ? SnackBarAction(
                  label: 'Apri AI Hub',
                  onPressed: onRetry,
                )
              : retryText != null
                  ? SnackBarAction(
                      label: 'Riprova',
                      onPressed: () => unawaited(_sendMessage(retryText)),
                    )
                  : null,
        ),
      );
  }

  @override
  void dispose() {
    _backendPollTimer?.cancel();
    _inputController.dispose();
    _messageScrollController.dispose();
    _selectedCoreNode.dispose();
    super.dispose();
  }

  void _selectSection(JackSection section) {
    if (section != JackSection.conversations &&
        section != JackSection.exploration) {
      _selectedCoreNode.value = null;
    }
    _scaffoldKey.currentState?.closeEndDrawer();
    setState(() => _selectedSection = section);
  }

  void _selectCoreNode(JackCoreNode node) {
    _selectedCoreNode.value = node;
    if (MediaQuery.sizeOf(context).width < 1320) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _scaffoldKey.currentState?.openEndDrawer();
      });
    }
  }

  void _clearCoreNodeSelection() {
    _selectedCoreNode.value = null;
  }

  void _openCorePreview() {
    _scaffoldKey.currentState?.openEndDrawer();
  }

  Widget _buildCorePreviewPanel(JackCoreNode? node) => JackCorePreviewPanel(
    graph: _liveGraph ?? JackCoreGraph.empty,
    node: node,
    onOpenInGraph: () => _selectSection(JackSection.exploration),
    onClearSelection: _clearCoreNodeSelection,
  );

  Widget _buildCorePreviewDrawer(double viewportWidth) {
    return Drawer(
      width: math.min(380, viewportWidth * 0.9),
      backgroundColor: JackPalette.canvas,
      child: SafeArea(
        child: ValueListenableBuilder<JackCoreNode?>(
          valueListenable: _selectedCoreNode,
          builder: (context, node, child) => SingleChildScrollView(
            padding: const EdgeInsets.all(14),
            child: _buildCorePreviewPanel(node),
          ),
        ),
      ),
    );
  }

  String? get _activeConversationTitle =>
      _activeConversationWithMessages?.conversation.title;

  List<ChatMessage> get _chatMessages {
    if (_activeConversationWithMessages == null) return <ChatMessage>[];
    return _toChatMessages(_activeConversationWithMessages!.messages);
  }

  List<ChatMessage> _toChatMessages(
    List<ConversationMessage> messages,
  ) {
    return messages
        .map((message) => ChatMessage(
          id: message.id,
          author: message.isUser ? MessageAuthor.user : MessageAuthor.jack,
          time: TimeOfDay.fromDateTime(message.createdAt).format(context),
          text: message.content,
          createdAt: message.createdAt,
          isDemo: message.isDemo,
          providerLabel: message.providerLabel,
        ))
        .toList(growable: false);
  }

  Future<void> _newConversation() async {
    _selectedCoreNode.value = null;
    _scaffoldKey.currentState?.closeEndDrawer();
    if (!_aiAvailable) {
      if (_noProvidersConfigured) {
        _showChatError(
          message:
              'Nessun provider AI configurato. Apri l’AI Hub per configurare un provider gratuito (es. Ollama locale, Gemini, Groq o OpenRouter).',
          onRetry: () => _selectSection(JackSection.modules),
        );
      } else {
        _showChatError(
          message:
              'Configura la chiave API del provider selezionato nell’AI Hub.',
        );
      }
      return;
    }
    try {
      final draft = ConversationDraft(
        title: 'Nuova conversazione',
        providerId: _aiConfiguration!.selectedProviderId,
        modelId: _aiConfiguration!.selectedModelId,
      );
      final created = await _conversationRepository.createConversation(draft);
      if (!mounted) return;
      setState(() {
        _conversations.add(created);
        _activeConversationId = created.id;
        _activeConversationWithMessages = null;
        _selectedSection = JackSection.conversations;
      });
      unawaited(_selectConversationById(created.id));
    } on Exception catch (error) {
      if (!mounted) return;
      _showChatError(
        message: 'Impossibile creare la conversazione: ${error.toString()}',
      );
    }
  }

  Future<void> _selectConversationById(String id) async {
    _selectedCoreNode.value = null;
    _scaffoldKey.currentState?.closeEndDrawer();
    setState(() {
      _activeConversationId = id;
      _activeConversationWithMessages = null;
      _selectedSection = JackSection.conversations;
    });
    try {
      final loaded =
          await _conversationRepository.getConversation(id);
      if (!mounted) return;
      final resolved = loaded ??
          ConversationWithMessages(
            conversation: _conversations.firstWhere(
              (c) => c.id == id,
              orElse: () => Conversation(
                id: id,
                title: '',
                createdAt: DateTime.now(),
                updatedAt: DateTime.now(),
                messageCount: 0,
              ),
            ),
            messages: const [],
          );
      setState(() {
        _activeConversationWithMessages = resolved;
        // Aggiorna message_count nella lista.
        _conversations = _conversations.map((c) {
          if (c.id == id) {
            return Conversation(
              id: c.id,
              title: c.title,
              createdAt: c.createdAt,
              updatedAt: c.updatedAt,
              providerId: c.providerId,
              modelId: c.modelId,
              metadata: c.metadata,
              messageCount: resolved.messages.length,
            );
          }
          return c;
        }).toList(growable: false);
      });
    } on LocalApiException catch (error) {
      if (!mounted) return;
      _showChatError(message: error.message);
    } on Exception catch (error) {
      if (!mounted) return;
      _showChatError(
        message: 'Impossibile caricare la conversazione: ${error.toString()}',
      );
    }
  }

  Future<void> _sendMessage(String value) async {
    final text = value.trim();
    if (text.isEmpty) return;

    final conversationId = _activeConversationId;
    if (conversationId == null) {
      // Nessuna conversazione attiva: ne crea una se il backend è disponibile.
      if (!_aiAvailable) {
        _showChatError(
          message:
              'Backend locale non disponibile. Avvia J.A.C.K. Backend e riprova.',
        );
        return;
      }
      await _newConversation();
      if (_activeConversationId == null || !mounted) return;
    }

    setState(() {
      _isSending = true;
    });
    _inputController.clear();
    _scrollToBottom();

    if (!_aiAvailable) {
      if (mounted) setState(() => _isSending = false);
      String message;
      if (_backendState != BackendConnectionState.connected) {
        message =
            'Backend locale non disponibile. Avvia J.A.C.K. Backend e riprova.';
      } else if (_aiLoading) {
        message = 'Caricamento della configurazione AI… riprova tra un istante.';
      } else if (_aiConfiguration == null) {
        message = _aiError ?? 'Impossibile leggere la configurazione AI.';
      } else if (_noProvidersConfigured) {
        _showChatError(
          message:
              'Nessun provider AI configurato. Configura un provider gratuito (es. Ollama locale, Gemini, Groq o OpenRouter) nell’AI Hub.',
          onRetry: () => _selectSection(JackSection.modules),
        );
        return;
      } else if (_aiConfiguration!.selectedProvider == null) {
        message =
            'Seleziona un provider AI nell’AI Hub.';
      } else if (!_aiConfiguration!.selectedProvider!.configured) {
        message =
            'Configura la chiave API del provider selezionato nell’AI Hub.';
      } else {
        message = 'Seleziona un modello abilitato nell’AI Hub.';
      }
      _showChatError(message: message, retryText: text);
      return;
    }

    try {
      // Salva il messaggio utente nella conversazione persistente.
      final savedUser = await _conversationRepository.addMessage(
        _activeConversationId!,
        ConversationMessageDraft(role: 'user', content: text),
      );
      if (!mounted) return;

      setState(() {
        _activeConversationWithMessages = _activeConversationWithMessages != null
            ? ConversationWithMessages(
                conversation: _activeConversationWithMessages!.conversation,
                messages: [
                  ..._activeConversationWithMessages!.messages,
                  savedUser,
                ],
              )
            : null;
        _conversations = _conversations.map((c) {
          if (c.id == _activeConversationId) {
            return Conversation(
              id: c.id,
              title: c.title,
              createdAt: c.createdAt,
              updatedAt: c.updatedAt,
              providerId: c.providerId,
              modelId: c.modelId,
              metadata: c.metadata,
              messageCount: c.messageCount + 1,
            );
          }
          return c;
        }).toList(growable: false);
        _isSending = true;
      });
      _scrollToBottom();

      final history = _activeConversationWithMessages?.messages ??
          <ConversationMessage>[];
      final response = await _conversationRepository.chatInConversation(
        conversationId: _activeConversationId!,
        modelId: _aiConfiguration!.selectedModel!.id,
        messages: history,
      );
      if (!mounted) return;

      setState(() {
        _activeConversationWithMessages = _activeConversationWithMessages != null
            ? ConversationWithMessages(
                conversation: _activeConversationWithMessages!.conversation,
                messages: [
                  ..._activeConversationWithMessages!.messages,
                  ConversationMessage(
                    id: DateTime.now().millisecondsSinceEpoch.toString(),
                    conversationId: _activeConversationId!,
                    role: 'assistant',
                    content: response.content,
                    createdAt: DateTime.now(),
                    isDemo: false,
                    providerLabel: response.providerId,
                  ),
                ],
              )
            : null;
        _conversations = _conversations.map((c) {
          if (c.id == _activeConversationId) {
            return Conversation(
              id: c.id,
              title: c.title,
              createdAt: c.createdAt,
              updatedAt: c.updatedAt,
              providerId: c.providerId,
              modelId: c.modelId,
              metadata: c.metadata,
              messageCount: c.messageCount + 1,
            );
          }
          return c;
        }).toList(growable: false);
        _isSending = false;
      });
      _scrollToBottom();
    } on LocalApiException catch (error) {
      if (!mounted) return;
      setState(() => _isSending = false);
      _showChatError(message: error.message, retryText: text);
    } on Exception {
      if (!mounted) return;
      setState(() => _isSending = false);
      _showChatError(
        message:
            'La risposta dell’assistente non è stata ricevuta. Riprova.',
        retryText: text,
      );
    }
  }

  void _showLocalNotice(String text) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(content: Text(text), duration: const Duration(seconds: 2)),
      );
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final compactNavigation = width < 1120;
        final showRightRail = width >= 1320;
        final navigationWidth = compactNavigation
            ? 76.0
            : (width >= 1800 ? 272.0 : 232.0);
        final rightRailWidth = width >= 1800 ? 340.0 : 300.0;

        return Scaffold(
          key: _scaffoldKey,
          endDrawer: showRightRail ? null : _buildCorePreviewDrawer(width),
          drawerEnableOpenDragGesture: false,
          endDrawerEnableOpenDragGesture: false,
          body: DecoratedBox(
            decoration: const BoxDecoration(
              color: JackPalette.canvas,
              gradient: RadialGradient(
                center: Alignment.topLeft,
                radius: 1.25,
                colors: [Color(0xFF211711), JackPalette.canvas],
                stops: [0, 0.57],
              ),
            ),
            child: SafeArea(
              child: Column(
                children: [
                  JackTopBar(
                    isListening: _isListening,
                    backendState: _backendState,
                    backendVersion: _backendSnapshot?.version,
                    onRetryBackend: () => _refreshBackend(showLoading: true),
                    onToggleListening: () =>
                        setState(() => _isListening = !_isListening),
                    onExplore: () => _selectSection(JackSection.exploration),
                    onSettings: () => _selectSection(JackSection.settings),
                    onProfile: () => _showLocalNotice(
                      'Profilo locale, senza account collegato.',
                    ),
                    showIdentity: width > 930,
                  ),
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(12, 7, 12, 10),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          SizedBox(
                            width: navigationWidth,
                            child: JackSidebar(
                              selectedSection: _selectedSection,
                              compact: compactNavigation,
                              activeConversationId: _activeConversationId,
                              conversations: _conversations,
                              onSectionSelected: _selectSection,
                              onNewConversation: _newConversation,
                              onConversationSelected: _selectConversationById,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: switch (_selectedSection) {
                              JackSection.conversations =>
                                Column(
                                  children: [
                                    if (_noProvidersConfigured)
                                      _NoProviderNotice(
                                        onConfigureProvider: () =>
                                            _selectSection(
                                              JackSection.modules,
                                            ),
                                      ),
                                    Expanded(
                                      child: _ConversationWorkspace(
                                        conversationTitle:
                                            _activeConversationTitle ??
                                            'Nuova conversazione',
                                        selectedCoreNode:
                                            _selectedCoreNode,
                                        onCoreNodeSelected:
                                            _selectCoreNode,
                                        onOpenCorePreview: _openCorePreview,
                                        showPreviewButton: !showRightRail,
                                        messages: _chatMessages,
                                        inputController: _inputController,
                                        scrollController:
                                            _messageScrollController,
                                        onSend: _sendMessage,
                                        isGenerating: _isSending,
                                        activeModelLabel: _aiAvailable
                                            ? _aiConfiguration!
                                                .selectedModel!.name
                                            : null,
                                        inputEnabled: !_isSending,
                                        onExplore: () =>
                                            _selectSection(
                                              JackSection.exploration,
                                            ),
                                        onAttachment: () =>
                                            _showLocalNotice(
                                              'Gli allegati non sono ancora supportati.',
                                            ),
                                        onVoice: () => _showLocalNotice(
                                          'L’input vocale non è collegato.',
                                        ),
                                        graph: _liveGraph ?? JackCoreGraph.empty,
                                      ),
                                    ),
                                  ],
                                ),
                              JackSection.modules => AiHubScreen(
                                providerGateway: _aiGateway,
                                onReturn: () =>
                                    _selectSection(JackSection.conversations),
                              ),
                              JackSection.memory => MemoryScreen(
                                repository: widget.memoryRepository,
                                onMemoryChanged: () =>
                                    unawaited(_loadLiveGraph()),
                              ),
                              _ => _SectionPlaceholder(
                                section: _selectedSection,
                                selectedCoreNode: _selectedCoreNode,
                                onCoreNodeSelected: _selectCoreNode,
                                onReturn: () =>
                                    _selectSection(JackSection.conversations),
                                graph: _liveGraph ?? JackCoreGraph.empty,
                              ),
                            },
                          ),
                          if (showRightRail) ...[
                            const SizedBox(width: 12),
                            SizedBox(
                              width: rightRailWidth,
                              child: RightRail(
                                backendState: _backendState,
                                backendVersion: _backendSnapshot?.version,
                                onSectionSelected: _selectSection,
                                selectedCoreNode: _selectedCoreNode,
                                onClearCoreNodeSelection:
                                    _clearCoreNodeSelection,
                                showCorePreview:
                                    _selectedSection ==
                                        JackSection.conversations ||
                                    _selectedSection == JackSection.exploration,
                                graph: _liveGraph ?? JackCoreGraph.empty,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _ConversationWorkspace extends StatelessWidget {
  const _ConversationWorkspace({
    required this.conversationTitle,
    required this.selectedCoreNode,
    required this.onCoreNodeSelected,
    required this.onOpenCorePreview,
    required this.showPreviewButton,
    required this.messages,
    required this.inputController,
    required this.scrollController,
    required this.onSend,
    required this.isGenerating,
    required this.activeModelLabel,
    required this.inputEnabled,
    required this.onExplore,
    required this.onAttachment,
    required this.onVoice,
    required this.graph,
  });

  final String conversationTitle;
  final ValueListenable<JackCoreNode?> selectedCoreNode;
  final ValueChanged<JackCoreNode> onCoreNodeSelected;
  final VoidCallback onOpenCorePreview;
  final bool showPreviewButton;
  final List<ChatMessage> messages;
  final TextEditingController inputController;
  final ScrollController scrollController;
  final ValueChanged<String> onSend;
  final bool isGenerating;
  final String? activeModelLabel;
  final bool inputEnabled;
  final VoidCallback onExplore;
  final VoidCallback onAttachment;
  final VoidCallback onVoice;
  final JackCoreGraph graph;

  @override
  Widget build(BuildContext context) {
    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: JackPalette.panel,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: JackPalette.border),
      ),
      child: Column(
        children: [
          const _GreetingHeader(),
          Expanded(
            flex: 6,
            child: _CoreStage(
              onExplore: onExplore,
              selectedCoreNode: selectedCoreNode,
              onCoreNodeSelected: onCoreNodeSelected,
              onOpenPreview: onOpenCorePreview,
              showPreviewButton: showPreviewButton,
              graph: graph,
            ),
          ),
          Expanded(
            flex: 4,
            child: ChatPanel(
              conversationTitle: conversationTitle,
              messages: messages,
              scrollController: scrollController,
              onExplore: onExplore,
              isGenerating: isGenerating,
              activeModelLabel: activeModelLabel,
            ),
          ),
          ChatComposer(
            controller: inputController,
            onSend: onSend,
            onAttachment: onAttachment,
            onVoice: onVoice,
            enabled: inputEnabled,
          ),
        ],
      ),
    );
  }
}

class _GreetingHeader extends StatelessWidget {
  const _GreetingHeader();

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 620;
        return SizedBox(
          height: compact ? 120 : 132,
          child: Padding(
            padding: EdgeInsets.fromLTRB(compact ? 20 : 32, 16, 24, 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text(
                      'J.A.C.K.',
                      style: TextStyle(
                        color: JackPalette.amber,
                        fontSize: 8,
                        letterSpacing: 2.3,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Container(
                      width: 38,
                      height: 1,
                      color: JackPalette.amberSoft,
                    ),
                  ],
                ),
                const SizedBox(height: 9),
                Text(
                  'Buon pomeriggio, Francesco.',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: JackPalette.text,
                    fontSize: compact ? 21 : 27,
                    fontWeight: FontWeight.w300,
                    letterSpacing: -0.35,
                  ),
                ),
                const SizedBox(height: 5),
                const Text(
                  'La conversazione è aperta: riprendi da dove eravamo.',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(color: JackPalette.muted, fontSize: 11),
                ),
                const SizedBox(height: 7),
                const Row(
                  children: [
                    Text(
                      'IN ATTESA',
                      style: TextStyle(
                        color: JackPalette.dim,
                        fontSize: 8,
                        letterSpacing: 1.3,
                      ),
                    ),
                    SizedBox(width: 9),
                    StatusDot(color: JackPalette.amber, size: 4),
                    SizedBox(width: 6),
                    Text(
                      'Nucleo locale',
                      style: TextStyle(color: JackPalette.dim, fontSize: 9),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _CoreStage extends StatelessWidget {
  const _CoreStage({
    required this.onExplore,
    required this.selectedCoreNode,
    required this.onCoreNodeSelected,
    required this.onOpenPreview,
    required this.showPreviewButton,
    required this.graph,
  });

  final VoidCallback onExplore;
  final ValueListenable<JackCoreNode?> selectedCoreNode;
  final ValueChanged<JackCoreNode> onCoreNodeSelected;
  final VoidCallback onOpenPreview;
  final bool showPreviewButton;
  final JackCoreGraph graph;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final diameter = math.min(
          620.0,
          math.max(
            120.0,
            math.min(constraints.maxHeight - 36, constraints.maxWidth * 0.66),
          ),
        );

        return Stack(
          children: [
            Center(
              child: SizedBox(
                width: diameter,
                height: diameter,
                child: ValueListenableBuilder<JackCoreNode?>(
                  valueListenable: selectedCoreNode,
                  builder: (context, selectedNode, child) => JackCore(
                    key: const ValueKey('conversation-jack-core'),
                    graph: graph,
                    cognitiveState: JackCognitiveState.idle,
                    selectedNodeId: selectedNode?.id,
                    onNodeSelected: onCoreNodeSelected,
                  ),
                ),
              ),
            ),
            Positioned(
              left: showPreviewButton ? 16 : 8,
              right: showPreviewButton ? 132 : 8,
              bottom: 13,
              child: const Text(
                'TRASCINA PER RUOTARE · ROTELLA PER ZOOM · CLICCA UN NODO',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: JackPalette.muted,
                  fontSize: 9,
                  letterSpacing: 0.55,
                ),
              ),
            ),
            Positioned(
              right: 20,
              bottom: 5,
              child: OutlinedButton.icon(
                onPressed: onExplore,
                icon: const Icon(Icons.explore_outlined, size: 13),
                label: const Text('Esplora'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: JackPalette.muted,
                  side: const BorderSide(color: JackPalette.border),
                  textStyle: const TextStyle(fontSize: 9),
                  minimumSize: const Size(0, 32),
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  shape: const StadiumBorder(),
                ),
              ),
            ),
            if (showPreviewButton)
              Positioned(
                left: 16,
                bottom: 5,
                child: OutlinedButton.icon(
                  key: const ValueKey('open-node-preview'),
                  onPressed: onOpenPreview,
                  icon: const Icon(Icons.view_sidebar_outlined, size: 13),
                  label: const Text('Anteprima nodo'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: JackPalette.muted,
                    side: const BorderSide(color: JackPalette.border),
                    textStyle: const TextStyle(fontSize: 9),
                    minimumSize: const Size(0, 32),
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    shape: const StadiumBorder(),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

class _NoProviderNotice extends StatelessWidget {
  const _NoProviderNotice({required this.onConfigureProvider});

  final VoidCallback onConfigureProvider;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: JackPalette.amber.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: JackPalette.amber.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(
                Icons.info_outline_rounded,
                color: JackPalette.amber,
                size: 18,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Configura un provider AI',
                      style: TextStyle(
                        color: JackPalette.text,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Per conversare con J.A.C.K. è necessario configurare almeno un provider AI. Ollama (locale) non richiede chiave API; gli altri provider richiedono una chiave gratuita.',
                      style: TextStyle(
                        color: JackPalette.muted,
                        fontSize: 10,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              OutlinedButton.icon(
                key: const ValueKey('configure-provider-ai-hub'),
                onPressed: onConfigureProvider,
                icon: const Icon(Icons.settings_rounded, size: 14),
                label: const Text('Apri AI Hub'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: JackPalette.amber,
                  side: BorderSide(color: JackPalette.amber),
                  minimumSize: const Size.fromHeight(36),
                  textStyle: const TextStyle(fontSize: 11),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SectionPlaceholder extends StatelessWidget {
  const _SectionPlaceholder({
    required this.section,
    required this.selectedCoreNode,
    required this.onCoreNodeSelected,
    required this.onReturn,
    required this.graph,
  });

  final JackSection section;
  final ValueListenable<JackCoreNode?> selectedCoreNode;
  final ValueChanged<JackCoreNode> onCoreNodeSelected;
  final VoidCallback onReturn;
  final JackCoreGraph graph;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: JackPalette.panel,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: JackPalette.border),
      ),
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 660),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (section == JackSection.exploration) ...[
                  SizedBox(
                    width: 300,
                    height: 300,
                    child: ValueListenableBuilder<JackCoreNode?>(
                      valueListenable: selectedCoreNode,
                      builder: (context, selectedNode, child) => JackCore(
                        key: const ValueKey('exploration-jack-core'),
                        graph: graph,
                        cognitiveState: JackCognitiveState.idle,
                        selectedNodeId: selectedNode?.id,
                        onNodeSelected: onCoreNodeSelected,
                      ),
                    ),
                  ),
                ] else
                  Container(
                    width: 58,
                    height: 58,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: JackPalette.amber.withValues(alpha: 0.08),
                      border: Border.all(
                        color: JackPalette.amber.withValues(alpha: 0.25),
                      ),
                    ),
                    child: Icon(
                      section.icon,
                      size: 24,
                      color: section == JackSection.memory
                          ? JackPalette.cyan
                          : JackPalette.amber,
                    ),
                  ),
                const SizedBox(height: 10),
                DemoBadge(
                  label: section == JackSection.exploration
                      ? 'KNOWLEDGE CORE'
                      : 'ANTEPRIMA',
                ),
                const SizedBox(height: 16),
                Text(
                  section.title,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: JackPalette.text,
                    fontSize: 25,
                    fontWeight: FontWeight.w300,
                  ),
                ),
                const SizedBox(height: 9),
                Text(
                  section.description,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: JackPalette.muted,
                    fontSize: 12,
                    height: 1.6,
                  ),
                ),
                const SizedBox(height: 10),
                const Text(
                  'Sezione in attesa di configurazione.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: JackPalette.dim, fontSize: 10),
                ),
                const SizedBox(height: 22),
                OutlinedButton.icon(
                  onPressed: onReturn,
                  icon: const Icon(Icons.arrow_back_rounded, size: 14),
                  label: const Text('Torna alla conversazione'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: JackPalette.muted,
                    side: const BorderSide(color: JackPalette.border),
                    textStyle: const TextStyle(fontSize: 10),
                    shape: const StadiumBorder(),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
