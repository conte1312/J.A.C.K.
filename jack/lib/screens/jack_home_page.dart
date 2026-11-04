import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../models/chat_message.dart';
import '../models/jack_section.dart';
import '../screens/ai_hub_screen.dart';
import '../services/ai_hub_demo_repository.dart';
import '../services/backend_status_service.dart';
import '../services/memory_api_service.dart';
import '../theme/jack_theme.dart';
import '../widgets/chat_panel.dart';
import '../widgets/jack_primitives.dart';
import '../widgets/jack_sidebar.dart';
import '../widgets/jack_top_bar.dart';
import '../widgets/jack_core/jack_core.dart';
import '../widgets/jack_core/jack_core_demo_data.dart';
import '../widgets/jack_core/jack_core_graph.dart';
import '../widgets/jack_core/jack_core_preview_panel.dart';
import '../widgets/jack_core/jack_core_state.dart';
import 'memory_screen.dart';
import '../widgets/right_rail.dart';

class JackHomePage extends StatefulWidget {
  const JackHomePage({
    this.backendStatusReader,
    this.aiHubRepository,
    this.memoryRepository,
    super.key,
  });

  final BackendStatusReader? backendStatusReader;
  final AiHubDemoRepository? aiHubRepository;
  final MemoryRepository? memoryRepository;

  @override
  State<JackHomePage> createState() => _JackHomePageState();
}

class _JackHomePageState extends State<JackHomePage> {
  late final BackendStatusReader _backendReader;
  Timer? _backendPollTimer;
  BackendConnectionState _backendState = BackendConnectionState.loading;
  BackendSnapshot? _backendSnapshot;
  bool _backendCheckInProgress = false;

  final _inputController = TextEditingController();
  final _messageScrollController = ScrollController();
  final _scaffoldKey = GlobalKey<ScaffoldState>();
  final ValueNotifier<JackCoreNode?> _selectedCoreNode = ValueNotifier(null);

  JackSection _selectedSection = JackSection.conversations;
  bool _isListening = false;
  String _activeConversation = 'Preparazione riunione prodotto';
  final List<ChatMessage> _messages = [
    const ChatMessage(
      author: MessageAuthor.user,
      time: '16:25',
      text: 'Ricordami chi segue le metriche di adozione.',
    ),
    const ChatMessage(
      author: MessageAuthor.jack,
      time: '16:25',
      text: 'Dalla memoria risulta la riunione di prodotto del martedì alle 10:00 con Luca e Giulia. Per la demo: Luca segue lo stato tecnico della migrazione, Giulia le metriche di adozione. Le informazioni mostrate sono esempi e non provengono da una memoria collegata.',
    ),
    const ChatMessage(
      author: MessageAuthor.user,
      time: '16:27',
      text: 'Cosa devo preparare per la riunione di prodotto di domani?',
    ),
    const ChatMessage(
      author: MessageAuthor.jack,
      time: '16:27',
      text: 'Questa risposta è dimostrativa: in questa milestone non è collegato alcun modello AI né una memoria reale.',
    ),
  ];

  @override
  void initState() {
    super.initState();
    _backendReader = widget.backendStatusReader ?? BackendStatusService();
    WidgetsBinding.instance.addPostFrameCallback((_) => _refreshBackend());
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
    graph: jackCoreDemoGraph,
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

  void _newConversation() {
    _selectedCoreNode.value = null;
    _scaffoldKey.currentState?.closeEndDrawer();
    setState(() {
      _activeConversation = 'Nuova conversazione';
      _messages.clear();
      _selectedSection = JackSection.conversations;
    });
  }

  void _selectConversation(String title) {
    _selectedCoreNode.value = null;
    _scaffoldKey.currentState?.closeEndDrawer();
    setState(() {
      _activeConversation = title;
      _selectedSection = JackSection.conversations;
    });
  }

  void _sendMessage(String value) {
    final text = value.trim();
    if (text.isEmpty) return;

    setState(() {
      _messages.add(
        ChatMessage(
          author: MessageAuthor.user,
          time: TimeOfDay.now().format(context),
          text: text,
        ),
      );
    });
    _inputController.clear();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_messageScrollController.hasClients) {
        _messageScrollController.animateTo(
          _messageScrollController.position.minScrollExtent,
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOut,
        );
      }
    });

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        const SnackBar(
          content: Text(
            'Messaggio aggiunto alla demo. Nessun modello AI è collegato.',
          ),
          duration: Duration(seconds: 2),
        ),
      );
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
                      'Profilo locale dimostrativo, senza account collegato.',
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
                              activeConversation: _activeConversation,
                              onSectionSelected: _selectSection,
                              onNewConversation: _newConversation,
                              onConversationSelected: _selectConversation,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: switch (_selectedSection) {
                              JackSection.conversations =>
                                _ConversationWorkspace(
                                  conversationTitle: _activeConversation,
                                  selectedCoreNode: _selectedCoreNode,
                                  onCoreNodeSelected: _selectCoreNode,
                                  onOpenCorePreview: _openCorePreview,
                                  showPreviewButton: !showRightRail,
                                  messages: _messages,
                                  inputController: _inputController,
                                  scrollController: _messageScrollController,
                                  onSend: _sendMessage,
                                  onExplore: () =>
                                      _selectSection(JackSection.exploration),
                                  onAttachment: () => _showLocalNotice(
                                    'Gli allegati non sono attivi nella demo.',
                                  ),
                                  onVoice: () => _showLocalNotice(
                                    'L’input vocale non è collegato.',
                                  ),
                                ),
                              JackSection.modules => AiHubScreen(
                                repository: widget.aiHubRepository,
                                onReturn: () =>
                                    _selectSection(JackSection.conversations),
                              ),
                              JackSection.memory => MemoryScreen(
                                repository: widget.memoryRepository,
                              ),
                              _ => _SectionPlaceholder(
                                section: _selectedSection,
                                selectedCoreNode: _selectedCoreNode,
                                onCoreNodeSelected: _selectCoreNode,
                                onReturn: () =>
                                    _selectSection(JackSection.conversations),
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
    required this.onExplore,
    required this.onAttachment,
    required this.onVoice,
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
  final VoidCallback onExplore;
  final VoidCallback onAttachment;
  final VoidCallback onVoice;

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
            ),
          ),
          Expanded(
            flex: 4,
            child: ChatPanel(
              conversationTitle: conversationTitle,
              messages: messages,
              scrollController: scrollController,
              onExplore: onExplore,
            ),
          ),
          ChatComposer(
            controller: inputController,
            onSend: onSend,
            onAttachment: onAttachment,
            onVoice: onVoice,
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
                      'Nucleo locale · dati demo',
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
  });

  final VoidCallback onExplore;
  final ValueListenable<JackCoreNode?> selectedCoreNode;
  final ValueChanged<JackCoreNode> onCoreNodeSelected;
  final VoidCallback onOpenPreview;
  final bool showPreviewButton;

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
                    graph: jackCoreDemoGraph,
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

class _SectionPlaceholder extends StatelessWidget {
  const _SectionPlaceholder({
    required this.section,
    required this.selectedCoreNode,
    required this.onCoreNodeSelected,
    required this.onReturn,
  });

  final JackSection section;
  final ValueListenable<JackCoreNode?> selectedCoreNode;
  final ValueChanged<JackCoreNode> onCoreNodeSelected;
  final VoidCallback onReturn;

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
                        graph: jackCoreDemoGraph,
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
                      ? 'CORE DIMOSTRATIVO'
                      : 'ANTEPRIMA · DEMO',
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
                  'Nessun servizio è collegato in questa milestone.',
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
