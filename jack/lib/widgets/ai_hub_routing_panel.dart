import 'package:flutter/material.dart';

import '../models/ai_hub_configuration.dart';
import '../theme/jack_theme.dart';
import 'jack_primitives.dart';

class AiHubRoutingPanel extends StatelessWidget {
  const AiHubRoutingPanel({
    required this.configuration,
    required this.onRouteChanged,
    required this.enabled,
    super.key,
  });

  final AiHubConfiguration configuration;
  final ValueChanged<({AiHubTaskCategory category, String modelId})>
  onRouteChanged;
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
              const Expanded(child: SectionEyebrow('Routing automatico')),
              const DemoBadge(label: 'SIMULATO'),
            ],
          ),
          const SizedBox(height: 6),
          const Text(
            'Associa una categoria a un modello. L’instradamento resta un esempio e non invia richieste.',
            style: TextStyle(color: JackPalette.dim, fontSize: 9, height: 1.5),
          ),
          const SizedBox(height: 12),
          for (final category in AiHubTaskCategory.values) ...[
            _RouteSelector(
              category: category,
              modelId: configuration.routes[category]!,
              models: configuration.models,
              enabled: enabled,
              onChanged: (modelId) =>
                  onRouteChanged((category: category, modelId: modelId)),
            ),
            if (category != AiHubTaskCategory.values.last)
              const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }
}

class _RouteSelector extends StatelessWidget {
  const _RouteSelector({
    required this.category,
    required this.modelId,
    required this.models,
    required this.enabled,
    required this.onChanged,
  });

  final AiHubTaskCategory category;
  final String modelId;
  final List<DemoAiModel> models;
  final bool enabled;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final model = models.firstWhere((item) => item.id == modelId);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          category.label,
          style: const TextStyle(color: JackPalette.muted, fontSize: 9),
        ),
        const SizedBox(height: 5),
        DropdownButtonFormField<String>(
          key: ValueKey('routing-select-${category.name}'),
          initialValue: modelId,
          isExpanded: true,
          iconEnabledColor: JackPalette.amber,
          dropdownColor: JackPalette.panelRaised,
          decoration: InputDecoration(
            isDense: true,
            filled: true,
            fillColor: JackPalette.panelRaised.withValues(alpha: 0.6),
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 10,
              vertical: 10,
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: JackPalette.borderSoft),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: JackPalette.amberSoft),
            ),
          ),
          style: const TextStyle(color: JackPalette.text, fontSize: 10),
          items: [
            for (final item in models)
              DropdownMenuItem(
                key: ValueKey('routing-choice-${category.name}-${item.id}'),
                value: item.id,
                child: Text(
                  '${item.name} · ${item.provider.label}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
          ],
          onChanged: enabled
              ? (value) {
                  if (value != null) onChanged(value);
                }
              : null,
          selectedItemBuilder: (context) => [
            for (final item in models)
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  '${item.name} · ${item.provider.label}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
          ],
        ),
        const SizedBox(height: 3),
        Text(
          '${model.provider.label} · demo, non collegato',
          style: const TextStyle(color: JackPalette.dim, fontSize: 8),
        ),
      ],
    );
  }
}

class AiHubDemoCostsNote extends StatelessWidget {
  const AiHubDemoCostsNote({super.key});

  @override
  Widget build(BuildContext context) {
    return JackPanel(
      padding: const EdgeInsets.all(15),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: SectionEyebrow('Costi e limiti')),
              DemoBadge(label: 'DATI DI ESEMPIO'),
            ],
          ),
          SizedBox(height: 8),
          Text(
            'Valori illustrativi in crediti e unità demo. Non rappresentano prezzi reali, quote API o disponibilità gratuite.',
            style: TextStyle(
              color: JackPalette.muted,
              fontSize: 9,
              height: 1.55,
            ),
          ),
        ],
      ),
    );
  }
}
