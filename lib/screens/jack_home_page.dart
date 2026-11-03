import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../models/chat_message.dart';
import '../models/jack_section.dart';
import '../theme/jack_theme.dart';
import '../widgets/chat_panel.dart';
import '../widgets/jack_primitives.dart';
import '../widgets/jack_sidebar.dart';
import '../widgets/jack_top_bar.dart';
import '../widgets/knowledge_core.dart';
import '../widgets/right_rail.dart';

class JackHomePage extends StatefulWidget {
  const JackHomePage({super.key});

  @override
  State<JackHomePage> createState() => _JackHomePageState();
}

class _JackHomePageState extends State<JackHomePage> {
  final _inputController = TextEditingController();
  final _messageScrollController = ScrollController();

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
  void dispose() {
    _inputController.dispose();
    _messageScrollController.dispose();
    super.dispose();
  }

  void _selectSection(JackSection section) {
    setState(() => _selectedSection = section);
  }

  void _newConversation() {
    setState(() {
      _activeConversation = 'Nuova conversazione';
      _messages.clear();
      _selectedSection = JackSection.conversations;
    });
  }

  void _selectConversation(String title) {
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
        final compactNavigation = width < 1500;
        final showRightRail = width >= 1320;
        final navigationWidth = compactNavigation
            ? 74.0
            : (width >= 1800 ? 282.0 : 246.0);
        final rightRailWidth = width >= 1800 ? 340.0 : 300.0;

        return Scaffold(
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
                            child: _selectedSection == JackSection.conversations
                                ? _ConversationWorkspace(
                                    conversationTitle: _activeConversation,
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
                                  )
                                : _SectionPlaceholder(
                                    section: _selectedSection,
                                    onReturn: () => _selectSection(
                                      JackSection.conversations,
                                    ),
                                  ),
                          ),
                          if (showRightRail) ...[
                            const SizedBox(width: 12),
                            SizedBox(
                              width: rightRailWidth,
                              child: RightRail(
                                onSectionSelected: _selectSection,
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
    required this.messages,
    required this.inputController,
    required this.scrollController,
    required this.onSend,
    required this.onExplore,
    required this.onAttachment,
    required this.onVoice,
  });

  final String conversationTitle;
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
          Expanded(flex: 6, child: _CoreStage(onExplore: onExplore)),
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
  const _CoreStage({required this.onExplore});

  final VoidCallback onExplore;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final diameter = math.min(
          540.0,
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
                child: const KnowledgeCore(),
              ),
            ),
            const Positioned(
              left: 8,
              right: 8,
              bottom: 13,
              child: Text(
                'TRASCINA PER RUOTARE · SCORRI PER LO ZOOM',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: JackPalette.dim,
                  fontSize: 8,
                  letterSpacing: 1.1,
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
          ],
        );
      },
    );
  }
}

class _SectionPlaceholder extends StatelessWidget {
  const _SectionPlaceholder({required this.section, required this.onReturn});

  final JackSection section;
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
                  const SizedBox(
                    width: 300,
                    height: 300,
                    child: KnowledgeCore(),
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
