import 'package:flutter/material.dart';

import '../models/chat_message.dart';
import '../theme/jack_theme.dart';
import 'jack_primitives.dart';

class ChatPanel extends StatelessWidget {
  const ChatPanel({
    required this.messages,
    required this.scrollController,
    required this.conversationTitle,
    required this.onExplore,
    super.key,
  });

  final List<ChatMessage> messages;
  final ScrollController scrollController;
  final String conversationTitle;
  final VoidCallback onExplore;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 14),
      decoration: BoxDecoration(
        color: const Color(0xFF191B1E),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: JackPalette.border),
      ),
      child: Column(
        children: [
          SizedBox(
            height: 42,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              child: Row(
                children: [
                  const SectionEyebrow('Conversazione'),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      conversationTitle,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: JackPalette.muted,
                        fontSize: 11,
                      ),
                    ),
                  ),
                  DemoBadge(label: 'DATI DEMO'),
                  const SizedBox(width: 12),
                  Text(
                    '${messages.length} messaggi',
                    style: const TextStyle(
                      color: JackPalette.dim,
                      fontSize: 10,
                    ),
                  ),
                  const SizedBox(width: 6),
                  IconButton(
                    tooltip: 'Esplora Knowledge Core',
                    onPressed: onExplore,
                    icon: const Icon(Icons.open_in_full_rounded, size: 13),
                    color: JackPalette.dim,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints.tightFor(
                      width: 24,
                      height: 24,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const Divider(height: 1, color: JackPalette.borderSoft),
          SizedBox(
            height: 44,
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              child: const Row(
                children: [
                  _ContextChip(
                    label: 'Riunione di prodotto del martedì',
                    color: JackPalette.amber,
                  ),
                  SizedBox(width: 7),
                  _ContextChip(
                    label: 'Luca Ferri — responsabile tecnico',
                    color: JackPalette.cyan,
                  ),
                  SizedBox(width: 7),
                  _ContextChip(
                    label: 'Scadenza contratto hosting',
                    color: JackPalette.lavender,
                  ),
                ],
              ),
            ),
          ),
          Expanded(
            child: ListView.separated(
              controller: scrollController,
              reverse: true,
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
              itemCount: messages.length,
              separatorBuilder: (context, index) => const SizedBox(height: 14),
              itemBuilder: (context, index) => _MessageBubble(
                message: messages[messages.length - 1 - index],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ContextChip extends StatelessWidget {
  const _ContextChip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: JackPalette.panelRaised,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: JackPalette.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          StatusDot(color: color, size: 4),
          const SizedBox(width: 6),
          Text(
            label,
            style: const TextStyle(color: JackPalette.muted, fontSize: 9),
          ),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message});

  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    if (message.isUser) {
      return Align(
        alignment: Alignment.centerRight,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 11),
            decoration: BoxDecoration(
              color: const Color(0xFF2A2C2F),
              borderRadius: BorderRadius.circular(18)
                  .copyWith(bottomRight: const Radius.circular(6)),
            ),
            child: Text(
              message.text,
              style: const TextStyle(color: JackPalette.text, fontSize: 13),
            ),
          ),
        ),
      );
    }

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 19,
          height: 19,
          margin: const EdgeInsets.only(top: 1),
          decoration: BoxDecoration(
            color: JackPalette.amber.withValues(alpha: 0.1),
            shape: BoxShape.circle,
            border: Border.all(
              color: JackPalette.amber.withValues(alpha: 0.25),
            ),
          ),
          child: const Center(
            child: Icon(Icons.circle, size: 5, color: JackPalette.amber),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 790),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text(
                      'J.A.C.K.',
                      style: TextStyle(
                        color: JackPalette.amber,
                        fontSize: 9,
                        letterSpacing: 1,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(width: 8),
                    const DemoBadge(label: 'RISPOSTA DEMO'),
                    const SizedBox(width: 8),
                    Text(
                      message.time,
                      style: const TextStyle(
                        color: JackPalette.dim,
                        fontSize: 9,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 7),
                Text(
                  message.text,
                  style: const TextStyle(
                    color: JackPalette.text,
                    fontSize: 12,
                    height: 1.55,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class ChatComposer extends StatelessWidget {
  const ChatComposer({
    required this.controller,
    required this.onSend,
    required this.onAttachment,
    required this.onVoice,
    super.key,
  });

  final TextEditingController controller;
  final ValueChanged<String> onSend;
  final VoidCallback onAttachment;
  final VoidCallback onVoice;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 9, 18, 12),
      child: Container(
        height: 58,
        padding: const EdgeInsets.symmetric(horizontal: 10),
        decoration: BoxDecoration(
          color: const Color(0xFF1B1D20),
          borderRadius: BorderRadius.circular(28),
          border: Border.all(color: JackPalette.border),
        ),
        child: Row(
          children: [
            IconButton(
              tooltip: 'Allegati non disponibili nella demo',
              onPressed: onAttachment,
              icon: const Icon(Icons.add_rounded, size: 17),
              color: JackPalette.dim,
              constraints: const BoxConstraints.tightFor(width: 34, height: 34),
              padding: EdgeInsets.zero,
            ),
            Expanded(
              child: TextField(
                key: const ValueKey('chat-input'),
                controller: controller,
                textInputAction: TextInputAction.send,
                onSubmitted: onSend,
                style: const TextStyle(fontSize: 13, color: JackPalette.text),
                cursorColor: JackPalette.amber,
                decoration: const InputDecoration(
                  hintText: 'Parla con J.A.C.K.…',
                  hintStyle: TextStyle(color: JackPalette.dim, fontSize: 13),
                  border: InputBorder.none,
                  isDense: true,
                  contentPadding: EdgeInsets.symmetric(horizontal: 10),
                ),
              ),
            ),
            IconButton(
              tooltip: 'Voce non collegata',
              onPressed: onVoice,
              icon: const Icon(Icons.mic_none_rounded, size: 16),
              color: JackPalette.muted,
              constraints: const BoxConstraints.tightFor(width: 34, height: 34),
              padding: EdgeInsets.zero,
            ),
            const SizedBox(width: 5),
            Material(
              color: JackPalette.panelHover,
              shape: const CircleBorder(),
              child: InkWell(
                key: const ValueKey('send-message'),
                onTap: () => onSend(controller.text),
                customBorder: const CircleBorder(),
                child: const SizedBox(
                  width: 36,
                  height: 36,
                  child: Icon(
                    Icons.arrow_upward_rounded,
                    size: 17,
                    color: JackPalette.muted,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
