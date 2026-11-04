import 'package:flutter/material.dart';

import '../models/ai_hub_configuration.dart';
import '../theme/jack_theme.dart';
import 'jack_primitives.dart';

class AiHubModelsPanel extends StatelessWidget {
  const AiHubModelsPanel({
    required this.models,
    required this.defaultModelId,
    required this.onAdd,
    required this.onEdit,
    required this.onRemove,
    required this.onSetDefault,
    required this.enabled,
    super.key,
  });

  final List<DemoAiModel> models;
  final String defaultModelId;
  final VoidCallback onAdd;
  final ValueChanged<DemoAiModel> onEdit;
  final ValueChanged<DemoAiModel> onRemove;
  final ValueChanged<DemoAiModel> onSetDefault;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return JackPanel(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(child: SectionEyebrow('Provider e modelli')),
              DemoBadge(label: '${models.length} CONFIGURAZIONI DEMO'),
            ],
          ),
          const SizedBox(height: 5),
          const Text(
            'Ogni voce è una configurazione locale di esempio. I provider sono non collegati.',
            style: TextStyle(color: JackPalette.dim, fontSize: 9, height: 1.45),
          ),
          const SizedBox(height: 14),
          for (final model in models) ...[
            _DemoModelCard(
              model: model,
              isDefault: model.id == defaultModelId,
              enabled: enabled,
              onEdit: () => onEdit(model),
              onRemove: () => onRemove(model),
              onSetDefault: () => onSetDefault(model),
            ),
            const SizedBox(height: 9),
          ],
          OutlinedButton.icon(
            key: const ValueKey('add-ai-model'),
            onPressed: enabled ? onAdd : null,
            icon: const Icon(Icons.add_rounded, size: 15),
            label: const Text('Aggiungi modello demo'),
            style: OutlinedButton.styleFrom(
              foregroundColor: JackPalette.muted,
              side: const BorderSide(color: JackPalette.border),
              minimumSize: const Size.fromHeight(37),
              textStyle: const TextStyle(fontSize: 10),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(11),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DemoModelCard extends StatelessWidget {
  const _DemoModelCard({
    required this.model,
    required this.isDefault,
    required this.enabled,
    required this.onEdit,
    required this.onRemove,
    required this.onSetDefault,
  });

  final DemoAiModel model;
  final bool isDefault;
  final bool enabled;
  final VoidCallback onEdit;
  final VoidCallback onRemove;
  final VoidCallback onSetDefault;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: ValueKey('ai-model-card-${model.id}'),
      padding: const EdgeInsets.fromLTRB(12, 11, 8, 10),
      decoration: BoxDecoration(
        color: isDefault
            ? JackPalette.amber.withValues(alpha: 0.055)
            : JackPalette.panelRaised.withValues(alpha: 0.58),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isDefault
              ? JackPalette.amber.withValues(alpha: 0.25)
              : JackPalette.borderSoft,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.only(top: 5),
                child: StatusDot(
                  color: model.provider == DemoAiProvider.local
                      ? JackPalette.cyan
                      : JackPalette.amber,
                  size: 6,
                ),
              ),
              const SizedBox(width: 9),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      model.name,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: JackPalette.text,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      '${model.provider.label} · provider non collegato',
                      style: const TextStyle(
                        color: JackPalette.muted,
                        fontSize: 9,
                      ),
                    ),
                  ],
                ),
              ),
              if (isDefault) ...[
                const DemoBadge(label: 'PREDEFINITO'),
                const SizedBox(width: 2),
              ] else
                IconButton(
                  key: ValueKey('set-default-model-${model.id}'),
                  tooltip: 'Imposta come predefinito',
                  onPressed: enabled ? onSetDefault : null,
                  visualDensity: VisualDensity.compact,
                  iconSize: 16,
                  color: JackPalette.muted,
                  icon: const Icon(Icons.star_outline_rounded),
                ),
              IconButton(
                key: ValueKey('edit-ai-model-${model.id}'),
                tooltip: 'Modifica modello demo',
                onPressed: enabled ? onEdit : null,
                visualDensity: VisualDensity.compact,
                iconSize: 15,
                color: JackPalette.muted,
                icon: const Icon(Icons.edit_outlined),
              ),
              IconButton(
                key: ValueKey('remove-ai-model-${model.id}'),
                tooltip: 'Rimuovi modello demo',
                onPressed: enabled ? onRemove : null,
                visualDensity: VisualDensity.compact,
                iconSize: 15,
                color: JackPalette.muted,
                icon: const Icon(Icons.close_rounded),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 5,
            runSpacing: 5,
            children: [
              for (final capability in model.capabilities)
                _CapabilityChip(label: capability.label),
            ],
          ),
          const SizedBox(height: 9),
          Row(
            children: [
              Expanded(
                child: _DemoValue(
                  label: 'Costo · DEMO',
                  value: model.demoCostLabel,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _DemoValue(
                  label: 'Limite · DEMO',
                  value: model.demoQuotaLabel,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Row(
            children: [
              Icon(
                Icons.remove_circle_outline_rounded,
                size: 11,
                color: JackPalette.dim,
              ),
              SizedBox(width: 5),
              Text(
                'Solo demo · nessuna richiesta inviata',
                style: TextStyle(color: JackPalette.dim, fontSize: 8),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _CapabilityChip extends StatelessWidget {
  const _CapabilityChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
      decoration: BoxDecoration(
        color: JackPalette.cyan.withValues(alpha: 0.055),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: JackPalette.cyan.withValues(alpha: 0.15)),
      ),
      child: Text(
        label,
        style: const TextStyle(color: JackPalette.cyan, fontSize: 8),
      ),
    );
  }
}

class _DemoValue extends StatelessWidget {
  const _DemoValue({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: JackPalette.amberSoft,
            fontSize: 8,
            letterSpacing: 0.35,
          ),
        ),
        const SizedBox(height: 3),
        Text(
          value,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(color: JackPalette.muted, fontSize: 8),
        ),
      ],
    );
  }
}
