import 'dart:async';

import 'package:flutter/material.dart';

import '../models/ai_hub_configuration.dart';
import '../services/ai_hub_demo_repository.dart';
import '../theme/jack_theme.dart';
import '../widgets/ai_hub_models_panel.dart';
import '../widgets/ai_hub_routing_panel.dart';
import '../widgets/demo_model_editor_dialog.dart';
import '../widgets/jack_primitives.dart';

class AiHubScreen extends StatefulWidget {
  const AiHubScreen({required this.onReturn, this.repository, super.key});

  final VoidCallback onReturn;
  final AiHubDemoRepository? repository;

  @override
  State<AiHubScreen> createState() => _AiHubScreenState();
}

class _AiHubScreenState extends State<AiHubScreen> {
  late final AiHubDemoRepository _repository;
  AiHubConfiguration? _configuration;
  String? _loadError;
  bool _loading = true;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _repository = widget.repository ?? AiHubDemoRepository();
    unawaited(_loadConfiguration());
  }

  Future<void> _loadConfiguration() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _loadError = null;
      });
    }
    try {
      final configuration = await _repository.load();
      if (!mounted) return;
      setState(() {
        _configuration = configuration;
        _loading = false;
      });
    } on AiHubStorageException catch (error) {
      if (!mounted) return;
      setState(() {
        _loadError = error.message;
        _loading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() {
        _loadError =
            'Errore inatteso durante la lettura della configurazione demo.';
        _loading = false;
      });
    }
  }

  Future<void> _saveConfiguration(
    AiHubConfiguration next, {
    required String successMessage,
  }) async {
    if (_saving) return;
    setState(() => _saving = true);
    String? errorMessage;
    try {
      await _repository.save(next);
    } on AiHubStorageException catch (error) {
      errorMessage = error.message;
    } on Exception {
      errorMessage = 'Errore durante il salvataggio dei dati demo.';
    }
    if (!mounted) return;
    setState(() {
      _saving = false;
      if (errorMessage == null) _configuration = next;
    });
    _showMessage(errorMessage ?? successMessage, isError: errorMessage != null);
  }

  Future<void> _addModel() async {
    final model = await showDialog<DemoAiModel>(
      context: context,
      builder: (context) => const DemoModelEditorDialog(),
    );
    if (model == null || !mounted) return;
    final configuration = _configuration!;
    await _saveConfiguration(
      configuration.copyWith(models: [...configuration.models, model]),
      successMessage: 'Modello demo aggiunto e salvato in locale.',
    );
  }

  Future<void> _editModel(DemoAiModel existing) async {
    final edited = await showDialog<DemoAiModel>(
      context: context,
      builder: (context) => DemoModelEditorDialog(model: existing),
    );
    if (edited == null || !mounted) return;
    final configuration = _configuration!;
    final models = configuration.models
        .map((model) => model.id == existing.id ? edited : model)
        .toList(growable: false);
    await _saveConfiguration(
      configuration.copyWith(models: models),
      successMessage: 'Modello demo aggiornato.',
    );
  }

  Future<void> _removeModel(DemoAiModel model) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: JackPalette.panel,
        title: const Text(
          'Rimuovere il modello demo?',
          style: TextStyle(color: JackPalette.text),
        ),
        content: Text(
          '“${model.name}” sarà rimosso dalla configurazione locale. Le route che lo usano passeranno al modello predefinito.',
          style: const TextStyle(color: JackPalette.muted, height: 1.5),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Annulla'),
          ),
          FilledButton(
            key: const ValueKey('confirm-remove-model'),
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Rimuovi'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    final configuration = _configuration!;
    if (configuration.models.length == 1) {
      _showMessage(
        'Mantieni almeno un modello demo configurato.',
        isError: true,
      );
      return;
    }
    final models = configuration.models
        .where((item) => item.id != model.id)
        .toList(growable: false);
    final defaultModelId = configuration.defaultModelId == model.id
        ? models.first.id
        : configuration.defaultModelId;
    final routes = {
      for (final entry in configuration.routes.entries)
        entry.key: entry.value == model.id ? defaultModelId : entry.value,
    };
    await _saveConfiguration(
      configuration.copyWith(
        models: models,
        defaultModelId: defaultModelId,
        routes: routes,
      ),
      successMessage: 'Modello demo rimosso.',
    );
  }

  Future<void> _setDefault(DemoAiModel model) async {
    final configuration = _configuration!;
    await _saveConfiguration(
      configuration.copyWith(defaultModelId: model.id),
      successMessage: '${model.name} è il modello predefinito della demo.',
    );
  }

  Future<void> _updateRoute({
    required AiHubTaskCategory category,
    required String modelId,
  }) async {
    final configuration = _configuration!;
    final routes = Map<AiHubTaskCategory, String>.of(configuration.routes)
      ..[category] = modelId;
    await _saveConfiguration(
      configuration.copyWith(routes: routes),
      successMessage: 'Routing demo aggiornato per ${category.label}.',
    );
  }

  Future<void> _restoreDemoData() async {
    await _saveConfiguration(
      AiHubConfiguration.demoDefaults(),
      successMessage: 'Configurazione demo iniziale ripristinata.',
    );
    if (mounted && _configuration != null) {
      setState(() => _loadError = null);
    }
  }

  void _showMessage(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: isError ? const Color(0xFF572D2B) : null,
          duration: const Duration(seconds: 3),
        ),
      );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: JackPalette.panel,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: JackPalette.border),
      ),
      clipBehavior: Clip.antiAlias,
      child: _loading
          ? const Center(
              child: SizedBox(
                width: 26,
                height: 26,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: JackPalette.amber,
                ),
              ),
            )
          : _loadError != null
          ? _ErrorState(
              message: _loadError!,
              onRetry: _loadConfiguration,
              onRestore: _restoreDemoData,
            )
          : _buildContent(_configuration!),
    );
  }

  Widget _buildContent(AiHubConfiguration configuration) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 930;
        final modelPanel = AiHubModelsPanel(
          models: configuration.models,
          defaultModelId: configuration.defaultModelId,
          onAdd: _addModel,
          onEdit: _editModel,
          onRemove: _removeModel,
          onSetDefault: _setDefault,
          enabled: !_saving,
        );
        final routingPanels = Column(
          children: [
            AiHubRoutingPanel(
              configuration: configuration,
              onRouteChanged: (route) => _updateRoute(
                category: route.category,
                modelId: route.modelId,
              ),
              enabled: !_saving,
            ),
            const SizedBox(height: 12),
            const AiHubDemoCostsNote(),
          ],
        );

        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 22, 24, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _PageHeader(onReturn: widget.onReturn),
              const SizedBox(height: 15),
              Container(
                key: const ValueKey('ai-hub-demo-notice'),
                padding: const EdgeInsets.symmetric(
                  horizontal: 13,
                  vertical: 11,
                ),
                decoration: BoxDecoration(
                  color: JackPalette.amber.withValues(alpha: 0.055),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: JackPalette.amber.withValues(alpha: 0.18),
                  ),
                ),
                child: const Row(
                  children: [
                    Icon(
                      Icons.info_outline_rounded,
                      color: JackPalette.amber,
                      size: 15,
                    ),
                    SizedBox(width: 9),
                    Expanded(
                      child: Text(
                        'AI Hub è una configurazione demo locale. Provider e modelli sono non collegati; il backend locale ha uno stato separato.',
                        style: TextStyle(
                          color: JackPalette.muted,
                          fontSize: 9,
                          height: 1.5,
                        ),
                      ),
                    ),
                    SizedBox(width: 8),
                    DemoBadge(label: 'NESSUNA CHIAMATA AI'),
                  ],
                ),
              ),
              const SizedBox(height: 15),
              if (wide)
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 6, child: modelPanel),
                    const SizedBox(width: 14),
                    Expanded(flex: 4, child: routingPanels),
                  ],
                )
              else ...[
                modelPanel,
                const SizedBox(height: 14),
                routingPanels,
              ],
              if (_saving) ...[
                const SizedBox(height: 12),
                const LinearProgressIndicator(
                  minHeight: 2,
                  color: JackPalette.amber,
                  backgroundColor: JackPalette.border,
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _PageHeader extends StatelessWidget {
  const _PageHeader({required this.onReturn});

  final VoidCallback onReturn;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 38,
          height: 38,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: JackPalette.amber.withValues(alpha: 0.08),
            border: Border.all(color: JackPalette.amber.withValues(alpha: 0.2)),
          ),
          child: const Icon(
            Icons.widgets_outlined,
            color: JackPalette.amber,
            size: 18,
          ),
        ),
        const SizedBox(width: 12),
        const Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SectionEyebrow('Moduli / configurazione locale'),
              SizedBox(height: 5),
              Text(
                'AI Hub',
                style: TextStyle(
                  color: JackPalette.text,
                  fontSize: 25,
                  fontWeight: FontWeight.w300,
                  letterSpacing: -0.3,
                ),
              ),
              SizedBox(height: 4),
              Text(
                'Provider, modelli e routing simulati.',
                style: TextStyle(color: JackPalette.muted, fontSize: 10),
              ),
            ],
          ),
        ),
        const SizedBox(width: 8),
        Tooltip(
          message: 'Torna alle conversazioni',
          child: IconButton(
            key: const ValueKey('ai-hub-return'),
            onPressed: onReturn,
            icon: const Icon(Icons.arrow_back_rounded),
            color: JackPalette.muted,
          ),
        ),
      ],
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({
    required this.message,
    required this.onRetry,
    required this.onRestore,
  });

  final String message;
  final VoidCallback onRetry;
  final VoidCallback onRestore;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 470),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.warning_amber_rounded,
                color: JackPalette.amber,
                size: 32,
              ),
              const SizedBox(height: 12),
              const Text(
                'Configurazione demo non disponibile',
                textAlign: TextAlign.center,
                style: TextStyle(color: JackPalette.text, fontSize: 16),
              ),
              const SizedBox(height: 8),
              Text(
                message,
                key: const ValueKey('ai-hub-error'),
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: JackPalette.muted,
                  fontSize: 10,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 18),
              Wrap(
                alignment: WrapAlignment.center,
                spacing: 8,
                runSpacing: 8,
                children: [
                  OutlinedButton.icon(
                    key: const ValueKey('retry-ai-hub-load'),
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh_rounded, size: 14),
                    label: const Text('Riprova'),
                  ),
                  FilledButton.tonalIcon(
                    key: const ValueKey('restore-demo-config'),
                    onPressed: onRestore,
                    icon: const Icon(Icons.restart_alt_rounded, size: 14),
                    label: const Text('Ripristina dati demo'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
