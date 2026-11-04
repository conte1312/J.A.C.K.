import 'package:flutter/material.dart';

import '../models/ai_hub_configuration.dart';
import '../theme/jack_theme.dart';
import 'jack_primitives.dart';

class DemoModelEditorDialog extends StatefulWidget {
  const DemoModelEditorDialog({this.model, super.key});

  final DemoAiModel? model;

  @override
  State<DemoModelEditorDialog> createState() => _DemoModelEditorDialogState();
}

class _DemoModelEditorDialogState extends State<DemoModelEditorDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _costController;
  late final TextEditingController _quotaController;
  late DemoAiProvider _provider;
  late final Set<AiHubTaskCategory> _capabilities;
  bool _showCapabilityError = false;

  @override
  void initState() {
    super.initState();
    final model = widget.model;
    _nameController = TextEditingController(text: model?.name ?? '');
    _costController = TextEditingController(
      text: model?.demoCostLabel ?? 'dato illustrativo · demo',
    );
    _quotaController = TextEditingController(
      text: model?.demoQuotaLabel ?? 'quota di esempio · demo',
    );
    _provider = model?.provider ?? DemoAiProvider.openAi;
    _capabilities = model == null
        ? {AiHubTaskCategory.conversation}
        : {...model.capabilities};
  }

  @override
  void dispose() {
    _nameController.dispose();
    _costController.dispose();
    _quotaController.dispose();
    super.dispose();
  }

  void _submit() {
    final valid = _formKey.currentState?.validate() ?? false;
    if (_capabilities.isEmpty) {
      setState(() => _showCapabilityError = true);
    }
    if (!valid || _capabilities.isEmpty) return;

    Navigator.of(context).pop(
      DemoAiModel(
        id: widget.model?.id ?? 'demo-${DateTime.now().microsecondsSinceEpoch}',
        name: _nameController.text.trim(),
        provider: _provider,
        capabilities: _capabilities.toList(growable: false),
        demoCostLabel: _costController.text.trim().isEmpty
            ? 'non definito · dato demo'
            : _costController.text.trim(),
        demoQuotaLabel: _quotaController.text.trim().isEmpty
            ? 'non definita · dato demo'
            : _quotaController.text.trim(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final editing = widget.model != null;
    return AlertDialog(
      backgroundColor: JackPalette.panel,
      titlePadding: const EdgeInsets.fromLTRB(22, 20, 22, 6),
      contentPadding: const EdgeInsets.fromLTRB(22, 8, 22, 4),
      title: Row(
        children: [
          Expanded(
            child: Text(
              editing ? 'Modifica modello demo' : 'Aggiungi modello demo',
              style: const TextStyle(color: JackPalette.text, fontSize: 17),
            ),
          ),
          const DemoBadge(label: 'NON COLLEGATO'),
        ],
      ),
      content: SizedBox(
        width: 430,
        child: SingleChildScrollView(
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'Questa voce configura solo la UI locale. Non inserire credenziali.',
                  style: TextStyle(
                    color: JackPalette.dim,
                    fontSize: 9,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 14),
                TextFormField(
                  key: const ValueKey('model-name-field'),
                  controller: _nameController,
                  autofocus: true,
                  decoration: _inputDecoration('Nome modello *'),
                  validator: (value) => value == null || value.trim().isEmpty
                      ? 'Inserisci il nome del modello.'
                      : null,
                ),
                const SizedBox(height: 11),
                DropdownButtonFormField<DemoAiProvider>(
                  key: const ValueKey('model-provider-field'),
                  initialValue: _provider,
                  decoration: _inputDecoration('Provider demo *'),
                  dropdownColor: JackPalette.panelRaised,
                  items: [
                    for (final provider in DemoAiProvider.values)
                      DropdownMenuItem(
                        value: provider,
                        child: Text(provider.label),
                      ),
                  ],
                  onChanged: (value) {
                    if (value != null) setState(() => _provider = value);
                  },
                ),
                const SizedBox(height: 14),
                const SectionEyebrow('Categoria / capacità *'),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 6,
                  runSpacing: 2,
                  children: [
                    for (final capability in AiHubTaskCategory.values)
                      FilterChip(
                        key: ValueKey('capability-${capability.name}'),
                        label: Text(capability.label),
                        selected: _capabilities.contains(capability),
                        onSelected: (selected) {
                          setState(() {
                            if (selected) {
                              _capabilities.add(capability);
                            } else {
                              _capabilities.remove(capability);
                            }
                            _showCapabilityError = false;
                          });
                        },
                        selectedColor: JackPalette.amber.withValues(
                          alpha: 0.16,
                        ),
                        checkmarkColor: JackPalette.amber,
                        side: BorderSide(
                          color: _capabilities.contains(capability)
                              ? JackPalette.amber.withValues(alpha: 0.4)
                              : JackPalette.border,
                        ),
                        labelStyle: TextStyle(
                          color: _capabilities.contains(capability)
                              ? JackPalette.text
                              : JackPalette.muted,
                          fontSize: 9,
                        ),
                      ),
                  ],
                ),
                if (_showCapabilityError)
                  const Padding(
                    padding: EdgeInsets.only(top: 2),
                    child: Text(
                      'Seleziona almeno una capacità.',
                      style: TextStyle(color: Color(0xFFFF8A80), fontSize: 10),
                    ),
                  ),
                const SizedBox(height: 13),
                TextFormField(
                  key: const ValueKey('model-demo-cost-field'),
                  controller: _costController,
                  decoration: _inputDecoration(
                    'Costo · dato demo, facoltativo',
                  ),
                ),
                const SizedBox(height: 10),
                TextFormField(
                  key: const ValueKey('model-demo-quota-field'),
                  controller: _quotaController,
                  decoration: _inputDecoration('Limite o quota · dato demo'),
                ),
              ],
            ),
          ),
        ),
      ),
      actionsPadding: const EdgeInsets.fromLTRB(18, 8, 18, 14),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Annulla'),
        ),
        FilledButton(
          key: const ValueKey('save-demo-model'),
          onPressed: _submit,
          child: Text(editing ? 'Salva modifiche' : 'Aggiungi modello'),
        ),
      ],
    );
  }

  InputDecoration _inputDecoration(String label) => InputDecoration(
    labelText: label,
    labelStyle: const TextStyle(color: JackPalette.muted, fontSize: 10),
    filled: true,
    fillColor: JackPalette.panelRaised.withValues(alpha: 0.65),
    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: JackPalette.borderSoft),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: JackPalette.amberSoft),
    ),
    errorBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: Color(0xFFFF8A80)),
    ),
    focusedErrorBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: Color(0xFFFF8A80)),
    ),
  );
}
