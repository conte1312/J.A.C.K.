import 'package:flutter/material.dart';

import '../models/jack_section.dart';
import '../theme/jack_theme.dart';
import 'jack_primitives.dart';

class JackSidebar extends StatelessWidget {
  const JackSidebar({
    required this.selectedSection,
    required this.compact,
    required this.onSectionSelected,
    required this.onNewConversation,
    required this.onConversationSelected,
    required this.activeConversation,
    super.key,
  });

  final JackSection selectedSection;
  final bool compact;
  final ValueChanged<JackSection> onSectionSelected;
  final VoidCallback onNewConversation;
  final ValueChanged<String> onConversationSelected;
  final String activeConversation;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: JackPalette.panel,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: JackPalette.border),
      ),
      child: Column(
        children: [
          const SizedBox(height: 10),
          for (final section in JackSection.values)
            _NavigationItem(
              section: section,
              selected: selectedSection == section,
              compact: compact,
              onTap: () => onSectionSelected(section),
            ),
          if (!compact) ...[
            const Padding(
              padding: EdgeInsets.fromLTRB(14, 14, 14, 0),
              child: Divider(height: 1, color: JackPalette.borderSoft),
            ),
            Expanded(
              child: _ConversationHistory(
                activeConversation: activeConversation,
                onNewConversation: onNewConversation,
                onConversationSelected: onConversationSelected,
              ),
            ),
          ] else
            const Spacer(),
          _DeviceFooter(compact: compact),
        ],
      ),
    );
  }
}

class _NavigationItem extends StatelessWidget {
  const _NavigationItem({
    required this.section,
    required this.selected,
    required this.compact,
    required this.onTap,
  });

  final JackSection section;
  final bool selected;
  final bool compact;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final content = Container(
      height: 42,
      margin: EdgeInsets.symmetric(horizontal: compact ? 8 : 10, vertical: 2),
      decoration: BoxDecoration(
        color: selected ? JackPalette.panelHover : Colors.transparent,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: selected
              ? JackPalette.amber.withValues(alpha: 0.12)
              : Colors.transparent,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 2,
            height: 18,
            decoration: BoxDecoration(
              color: selected ? JackPalette.amber : Colors.transparent,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          SizedBox(width: compact ? 9 : 11),
          Icon(
            section.icon,
            size: 17,
            color: selected
                ? JackPalette.amber
                : (section == JackSection.exploration
                      ? JackPalette.cyan
                      : JackPalette.muted),
          ),
          if (!compact) ...[
            const SizedBox(width: 11),
            Expanded(
              child: Text(
                section.title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: selected ? JackPalette.text : JackPalette.muted,
                  fontSize: 13,
                  fontWeight: selected ? FontWeight.w500 : FontWeight.w400,
                ),
              ),
            ),
          ],
        ],
      ),
    );

    return Tooltip(
      message: section.title,
      child: InkWell(
        key: ValueKey('nav-${section.name}'),
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: content,
      ),
    );
  }
}

class _ConversationHistory extends StatelessWidget {
  const _ConversationHistory({
    required this.activeConversation,
    required this.onNewConversation,
    required this.onConversationSelected,
  });

  final String activeConversation;
  final VoidCallback onNewConversation;
  final ValueChanged<String> onConversationSelected;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 14, 8),
          child: Row(
            children: [
              const Expanded(child: SectionEyebrow('Conversazioni')),
              Text(
                'In attesa',
                style: TextStyle(
                  color: JackPalette.dim.withValues(alpha: 0.9),
                  fontSize: 9,
                ),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: OutlinedButton.icon(
            key: const ValueKey('new-conversation'),
            onPressed: onNewConversation,
            icon: const Icon(Icons.add, size: 15),
            label: const Text('Nuova conversazione'),
            style: OutlinedButton.styleFrom(
              foregroundColor: JackPalette.muted,
              side: const BorderSide(color: JackPalette.border),
              minimumSize: const Size.fromHeight(36),
              textStyle: const TextStyle(fontSize: 11),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(11),
              ),
            ),
          ),
        ),
        const SizedBox(height: 8),
        _ConversationItem(
          title: 'Preparazione riunione prodotto',
          age: '1 ora fa',
          active: activeConversation == 'Preparazione riunione prodotto',
          onTap: () => onConversationSelected('Preparazione riunione prodotto'),
        ),
        _ConversationItem(
          title: 'Riassumi lo stato del progetto',
          age: '1 ora fa',
          active: activeConversation == 'Riassumi lo stato del progetto',
          onTap: () => onConversationSelected('Riassumi lo stato del progetto'),
        ),
      ],
    );
  }
}

class _ConversationItem extends StatelessWidget {
  const _ConversationItem({
    required this.title,
    required this.age,
    required this.active,
    required this.onTap,
  });

  final String title;
  final String age;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(11),
        child: Container(
          height: 42,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          decoration: BoxDecoration(
            color: active ? JackPalette.panelHover : Colors.transparent,
            borderRadius: BorderRadius.circular(11),
          ),
          child: Row(
            children: [
              StatusDot(
                color: active ? JackPalette.amber : JackPalette.dim,
                size: 5,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: active ? JackPalette.text : JackPalette.muted,
                    fontSize: 11,
                  ),
                ),
              ),
              const SizedBox(width: 7),
              Text(
                age,
                style: const TextStyle(color: JackPalette.dim, fontSize: 9),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DeviceFooter extends StatelessWidget {
  const _DeviceFooter({required this.compact});

  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 56,
      padding: EdgeInsets.symmetric(horizontal: compact ? 18 : 16),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: JackPalette.borderSoft)),
      ),
      child: compact
          ? const Center(
              child: Icon(
                Icons.memory_rounded,
                size: 17,
                color: JackPalette.muted,
              ),
            )
          : const Row(
              children: [
                Icon(Icons.memory_rounded, size: 16, color: JackPalette.muted),
                SizedBox(width: 10),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Mac · M1 Pro',
                        style: TextStyle(
                          color: JackPalette.muted,
                          fontSize: 10,
                        ),
                      ),
                      SizedBox(height: 3),
                      Text(
                        'LOCALE · DEMO',
                        style: TextStyle(
                          color: JackPalette.dim,
                          fontSize: 8,
                          letterSpacing: 1.1,
                        ),
                      ),
                    ],
                  ),
                ),
                StatusDot(color: JackPalette.amber, size: 6),
              ],
            ),
    );
  }
}
