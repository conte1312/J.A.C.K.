import 'package:flutter/material.dart';

import '../models/memory.dart';
import '../theme/jack_theme.dart';
import 'jack_primitives.dart';

class MemoryEntryCard extends StatelessWidget {
  const MemoryEntryCard({
    required this.memory,
    required this.enabled,
    required this.onEdit,
    required this.onDelete,
    super.key,
  });

  final MemoryRecord memory;
  final bool enabled;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return JackPanel(
      radius: 15,
      padding: const EdgeInsets.fromLTRB(15, 12, 10, 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 31,
            height: 31,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: JackPalette.cyan.withValues(alpha: 0.07),
              border: Border.all(
                color: JackPalette.cyan.withValues(alpha: 0.18),
              ),
            ),
            child: const Icon(
              Icons.bookmark_border_rounded,
              color: JackPalette.cyan,
              size: 15,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 5,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(
                      memory.title,
                      style: const TextStyle(
                        color: JackPalette.text,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    _CategoryBadge(category: memory.category),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  memory.content,
                  maxLines: 4,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: JackPalette.muted,
                    fontSize: 10,
                    height: 1.55,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Aggiornato · ${_formatDate(memory.updatedAt)}',
                  style: const TextStyle(color: JackPalette.dim, fontSize: 8),
                ),
              ],
            ),
          ),
          const SizedBox(width: 5),
          IconButton(
            key: ValueKey('edit-memory-${memory.id}'),
            tooltip: 'Modifica ricordo',
            onPressed: enabled ? onEdit : null,
            visualDensity: VisualDensity.compact,
            iconSize: 16,
            color: JackPalette.muted,
            icon: const Icon(Icons.edit_outlined),
          ),
          IconButton(
            key: ValueKey('delete-memory-${memory.id}'),
            tooltip: 'Elimina ricordo',
            onPressed: enabled ? onDelete : null,
            visualDensity: VisualDensity.compact,
            iconSize: 16,
            color: JackPalette.muted,
            icon: const Icon(Icons.delete_outline_rounded),
          ),
        ],
      ),
    );
  }
}

class _CategoryBadge extends StatelessWidget {
  const _CategoryBadge({required this.category});

  final MemoryCategory category;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: JackPalette.cyan.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: JackPalette.cyan.withValues(alpha: 0.15)),
      ),
      child: Text(
        category.label,
        style: const TextStyle(color: JackPalette.cyan, fontSize: 8),
      ),
    );
  }
}

String _formatDate(DateTime dateTime) {
  final local = dateTime.toLocal();
  final day = local.day.toString().padLeft(2, '0');
  final month = local.month.toString().padLeft(2, '0');
  final hour = local.hour.toString().padLeft(2, '0');
  final minute = local.minute.toString().padLeft(2, '0');
  return '$day/$month/${local.year} · $hour:$minute';
}
