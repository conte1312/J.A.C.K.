import 'package:flutter/material.dart';

import '../models/ai_provider.dart';
import '../services/ai_provider_service.dart';
import '../theme/jack_theme.dart';
import 'jack_primitives.dart';

class AiHubProviderPanel extends StatefulWidget {
  const AiHubProviderPanel({required this.gateway, super.key});

  final AiProviderGateway gateway;

  @override
  State<AiHubProviderPanel> createState() => _AiHubProviderPanelState();
}

class _AiHubProviderPanelState extends State<AiHubProviderPanel> {
  AiMultiProviderConfiguration? _configuration;
  String? _error;
  bool _loading = true;
  bool _working = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final configuration = await widget.gateway.loadProviderConfiguration();
      if (!mounted) return;
      setState(() {
        _configuration = configuration;
        _loading = false;
      });
    } on AiProviderException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() {
        _error = 'Non riesco a leggere la configurazione AI dal backend.';
        _loading = false;
      });
    }
  }

  Future<void> _run(
    Future<AiMultiProviderConfiguration> Function() action, {
    String? successMessage,
  }) async {
    if (_working) return;
    setState(() {
      _working = true;
      _error = null;
    });
    try {
      final configuration = await action();
      if (!mounted) return;
      setState(() => _configuration = configuration);
      if (successMessage != null) _showMessage(successMessage);
    } on AiProviderException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } on Exception {
      if (mounted) {
        setState(() => _error = 'Operazione AI Hub non completata. Riprova.');
      }
    } finally {
      if (mounted) setState(() => _working = false);
    }
  }

  Future<void> _saveApiKey(String providerId) async {
    final key = await showDialog<String>(
      context: context,
      builder: (context) => _ApiKeyDialog(providerId: providerId),
    );
    if (key == null || key.trim().isEmpty || !mounted) return;
    await _run(
      () => widget.gateway.saveProviderApiKey(providerId, key.trim()),
      successMessage: 'Chiave salvata nel Keychain macOS.',
    );
  }

  Future<void> _removeApiKey(String providerId) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: JackPalette.panel,
        title: const Text(
          'Rimuovere la chiave?',
          style: TextStyle(color: JackPalette.text),
        ),
        content: Text(
          'La credenziale salvata nel Keychain macOS verrà rimossa.',
          style: TextStyle(color: JackPalette.muted, height: 1.45),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Annulla'),
          ),
          FilledButton(
            key: ValueKey('remove-key-confirm-$providerId'),
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Rimuovi'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    await _run(
      () => widget.gateway.removeProviderApiKey(providerId),
      successMessage: 'Chiave rimossa dal Keychain macOS.',
    );
  }

  Future<void> _testConnection(String providerId, String? modelId) async {
    if (modelId == null || !mounted) return;
    await _run(
      () => widget.gateway.testProviderConnection(providerId, modelId),
      successMessage: 'Connessione verificata.',
    );
  }

  Future<void> _setProviderEnabled(String providerId, bool enabled) async {
    await _run(
      () => widget.gateway.setProviderEnabled(providerId, enabled),
    );
  }

  Future<void> _selectProviderAndModel(
    String providerId,
    String? modelId,
  ) async {
    await _run(
      () => widget.gateway.selectProviderAndModel(providerId, modelId),
    );
  }

  void _showMessage(String value) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(value)));
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const ValueKey('ai-provider-live-panel'),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF17191C),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: JackPalette.border),
      ),
      child: _loading
          ? const SizedBox(
              height: 94,
              child: Center(
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: JackPalette.amber,
                ),
              ),
            )
          : _error != null && _configuration == null
          ? _OfflineState(message: _error!, onRetry: _load)
          : _buildProviders(_configuration!),
    );
  }

  Widget _buildProviders(AiMultiProviderConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: JackPalette.amber.withValues(alpha: 0.08),
                shape: BoxShape.circle,
                border: Border.all(
                  color: JackPalette.amber.withValues(alpha: 0.2),
                ),
              ),
              child: const Icon(
                Icons.hub_outlined,
                color: JackPalette.amber,
                size: 17,
              ),
            ),
            const SizedBox(width: 11),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SectionEyebrow('Provider AI'),
                  SizedBox(height: 4),
                  Text(
                    'Gestione provider e modelli',
                    style: TextStyle(color: JackPalette.text, fontSize: 15),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        _buildProviderOrder(config),
        const SizedBox(height: 14),
        for (final provider in config.providers) ...[
          _ProviderCard(
            provider: provider,
            isSelected: config.selectedProviderId == provider.id,
            busy: _working,
            onConfigureKey: () => _saveApiKey(provider.id),
            onRemoveKey: () => _removeApiKey(provider.id),
            onTestConnection: () =>
                _testConnection(provider.id, provider.selectedModel?.id),
            onEnabledChanged: (enabled) =>
                _setProviderEnabled(provider.id, enabled),
            onSelect: (modelId) =>
                _selectProviderAndModel(provider.id, modelId),
          ),
          const SizedBox(height: 10),
        ],
        if (_error != null) ...[
          const SizedBox(height: 10),
          _InlineError(message: _error!),
        ],
        if (_working) ...[
          const SizedBox(height: 10),
          const LinearProgressIndicator(
            minHeight: 2,
            color: JackPalette.amber,
            backgroundColor: JackPalette.border,
          ),
        ],
      ],
    );
  }

  Widget _buildProviderOrder(AiMultiProviderConfiguration config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 6),
        const Text(
          'I provider vengono provati in ordine. Il primo disponibile e gratuito gestisce la chat.',
          style: TextStyle(color: JackPalette.muted, fontSize: 9, height: 1.45),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            for (final id in config.providerOrder)
              _OrderChip(
                id: id,
                name: _providerDisplayName(config, id),
                isEnabled: config.enabledProviders.contains(id),
                isFirst: id == config.providerOrder.first,
              ),
          ],
        ),
      ],
    );
  }

  String _providerDisplayName(
    AiMultiProviderConfiguration config,
    String id,
  ) {
    for (final p in config.providers) {
      if (p.id == id) return p.name;
    }
    return id;
  }
}

class _OrderChip extends StatelessWidget {
  const _OrderChip({
    required this.id,
    required this.name,
    required this.isEnabled,
    required this.isFirst,
    super.key,
  });

  final String id;
  final String name;
  final bool isEnabled;
  final bool isFirst;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: isFirst
            ? JackPalette.amber.withValues(alpha: 0.16)
            : JackPalette.panelRaised.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isFirst
              ? JackPalette.amber.withValues(alpha: 0.4)
              : JackPalette.borderSoft,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (!isFirst) ...[
            const Icon(
              Icons.arrow_right_rounded,
              size: 10,
              color: JackPalette.dim,
            ),
            const SizedBox(width: 4),
          ],
          Text(
            name,
            style: TextStyle(
              color: isEnabled ? JackPalette.text : JackPalette.dim,
              fontSize: 8.5,
              fontWeight: isFirst ? FontWeight.w600 : FontWeight.w400,
            ),
          ),
          if (!isEnabled)
            const Text(
              ' · OFF',
              style: TextStyle(
                color: JackPalette.dim,
                fontSize: 7,
              ),
            ),
        ],
      ),
    );
  }
}

class _ProviderCard extends StatelessWidget {
  const _ProviderCard({
    required this.provider,
    required this.isSelected,
    required this.busy,
    required this.onConfigureKey,
    required this.onRemoveKey,
    required this.onTestConnection,
    required this.onEnabledChanged,
    required this.onSelect,
    super.key,
  });

  final AiProviderInfo provider;
  final bool isSelected;
  final bool busy;
  final VoidCallback onConfigureKey;
  final VoidCallback onRemoveKey;
  final VoidCallback onTestConnection;
  final ValueChanged<bool> onEnabledChanged;
  final ValueChanged<String?> onSelect;

  String get _typeLabel {
    return provider.type == AiProviderType.local ? 'LOCALE' : 'ONLINE';
  }

  String get _freeTierLabel {
    return provider.isFreeTierAvailable ? 'Piano gratuito' : 'Nessun gratuito';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
      decoration: BoxDecoration(
        color: isSelected
            ? JackPalette.amber.withValues(alpha: 0.08)
            : JackPalette.panelRaised.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isSelected
              ? JackPalette.amber.withValues(alpha: 0.35)
              : JackPalette.borderSoft,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  color: provider.type == AiProviderType.local
                      ? JackPalette.cyan.withValues(alpha: 0.12)
                      : JackPalette.amber.withValues(alpha: 0.12),
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: provider.type == AiProviderType.local
                        ? JackPalette.cyan.withValues(alpha: 0.4)
                        : JackPalette.amber.withValues(alpha: 0.4),
                  ),
                ),
                child: Center(
                  child: Icon(
                    provider.type == AiProviderType.local
                        ? Icons.desktop_mac_rounded
                        : Icons.cloud_rounded,
                    color: provider.type == AiProviderType.local
                        ? JackPalette.cyan
                        : JackPalette.amber,
                    size: 14,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            provider.name,
                            style: TextStyle(
                              color: JackPalette.text,
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                        if (isSelected)
                          const Text(
                            'ATTIVO',
                            style: TextStyle(
                              color: JackPalette.amber,
                              fontSize: 7.5,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 0.6,
                            ),
                          ),
                      ],
                    ),
                    Text(
                      '$_typeLabel · ${provider.requiresCredential ? 'Chiave API' : 'Nessuna chiave'} · $_freeTierLabel',
                      style: TextStyle(
                        color: JackPalette.muted,
                        fontSize: 8,
                      ),
                    ),
                  ],
                ),
              ),
              _StatusPill(
                label: provider.configured ? 'Configurato' : 'Da configurare',
                color: provider.configured
                    ? JackPalette.green
                    : JackPalette.muted,
              ),
            ],
          ),
          const SizedBox(height: 8),
          if (provider.available) ...[
            Row(
              children: [
                StatusDot(color: JackPalette.green, size: 5),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Provider disponibile',
                    style: TextStyle(
                      color: JackPalette.green,
                      fontSize: 8,
                    ),
                  ),
                ),
              ],
            ),
          ] else if (provider.quotaExhausted) ...[
            Row(
              children: [
                StatusDot(color: JackPalette.amber, size: 5),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Quota esaurita',
                    style: TextStyle(
                      color: JackPalette.amber,
                      fontSize: 8,
                    ),
                  ),
                ),
              ],
            ),
          ] else if (provider.lastError != null) ...[
            Row(
              children: [
                StatusDot(color: JackPalette.red, size: 5),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    provider.lastError!,
                    style: TextStyle(
                      color: JackPalette.red,
                      fontSize: 8,
                    ),
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 8),
          if (provider.models.isNotEmpty) ...[
            const Text(
              'Modelli',
              style: TextStyle(
                color: JackPalette.dim,
                fontSize: 8,
                letterSpacing: 0.8,
              ),
            ),
            const SizedBox(height: 6),
            for (final model in provider.models)
              _ProviderModelRow(
                model: model,
                providerId: provider.id,
                busy: busy,
                isSelected: model.selected,
                onSelect: () => onSelect(model.id),
                onEnabledChanged: (enabled) => onEnabledChanged(enabled),
              ),
          ] else
            const Text(
              'Nessun modello disponibile',
              style: TextStyle(
                color: JackPalette.dim,
                fontSize: 8,
                fontStyle: FontStyle.italic,
              ),
            ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              if (provider.requiresCredential) ...[
                OutlinedButton.icon(
                  key: ValueKey('configure-key-${provider.id}'),
                  onPressed: busy ? null : onConfigureKey,
                  icon: const Icon(Icons.key_outlined, size: 13),
                  label: Text(
                    provider.configured
                        ? 'Aggiorna chiave'
                        : 'Configura chiave',
                  ),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: JackPalette.text,
                    minimumSize: const Size.fromHeight(32),
                    textStyle: const TextStyle(fontSize: 9),
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                  ),
                ),
                const SizedBox(width: 6, height: 32),
                if (provider.configured)
                  TextButton.icon(
                    key: ValueKey('remove-key-${provider.id}'),
                    onPressed: busy ? null : onRemoveKey,
                    icon: const Icon(Icons.delete_outline_rounded, size: 13),
                    label: const Text('Rimuovi'),
                    style: TextButton.styleFrom(
                      foregroundColor: JackPalette.dim,
                      minimumSize: const Size.fromHeight(32),
                      textStyle: const TextStyle(fontSize: 9),
                    ),
                  ),
              ],
              if (provider.requiresCredential && provider.configured)
                OutlinedButton.icon(
                  key: ValueKey('test-connection-${provider.id}'),
                  onPressed: busy ? null : onTestConnection,
                  icon: busy
                      ? const SizedBox(
                          width: 12,
                          height: 12,
                          child: CircularProgressIndicator(
                            strokeWidth: 1.5,
                            color: JackPalette.amber,
                          ),
                        )
                      : const Icon(
                          Icons.wifi_tethering_rounded,
                          size: 13,
                        ),
                  label: const Text('Test'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: JackPalette.text,
                    minimumSize: const Size.fromHeight(32),
                    textStyle: const TextStyle(fontSize: 9),
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ProviderModelRow extends StatelessWidget {
  const _ProviderModelRow({
    required this.model,
    required this.providerId,
    required this.busy,
    required this.isSelected,
    required this.onSelect,
    required this.onEnabledChanged,
    super.key,
  });

  final AiProviderModel model;
  final String providerId;
  final bool busy;
  final bool isSelected;
  final VoidCallback onSelect;
  final ValueChanged<bool> onEnabledChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: isSelected
            ? JackPalette.amber.withValues(alpha: 0.12)
            : Colors.transparent,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Radio<String>(
            value: model.id,
            groupValue: isSelected ? model.id : null,
            onChanged: !busy && model.enabled && !isSelected
                ? (_) => onSelect()
                : null,
            activeColor: JackPalette.amber,
            visualDensity: VisualDensity.compact,
          ),
          const SizedBox(width: 4),
          Expanded(
            child: InkWell(
              onTap: !busy && model.enabled && !isSelected ? onSelect : null,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    model.name,
                    style: TextStyle(
                      color: JackPalette.text,
                      fontSize: 9,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 1),
                  Text(
                    model.description,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: JackPalette.muted,
                      fontSize: 7.5,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 6),
          Switch.adaptive(
            value: model.enabled,
            onChanged: busy || isSelected ? null : onEnabledChanged,
            activeTrackColor: JackPalette.amber,
          ),
        ],
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.07),
      borderRadius: BorderRadius.circular(20),
      border: Border.all(color: color.withValues(alpha: 0.19)),
    ),
    child: Text(
      label,
      style: TextStyle(color: color, fontSize: 8, letterSpacing: 0.4),
    ),
  );
}

class _InlineError extends StatelessWidget {
  const _InlineError({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(10),
    decoration: BoxDecoration(
      color: const Color(0xFF572D2B).withValues(alpha: 0.5),
      borderRadius: BorderRadius.circular(10),
      border: Border.all(color: const Color(0xFF8A4743).withValues(alpha: 0.5)),
    ),
    child: Row(
      children: [
        const Icon(Icons.error_outline_rounded, color: JackPalette.red, size: 15),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            message,
            style: const TextStyle(color: JackPalette.text, fontSize: 10),
          ),
        ),
      ],
    ),
  );
}

class _OfflineState extends StatelessWidget {
  const _OfflineState({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Row(
    children: [
      const Icon(Icons.cloud_off_outlined, color: JackPalette.muted, size: 19),
      const SizedBox(width: 10),
      Expanded(
        child: Text(
          message,
          style: const TextStyle(color: JackPalette.muted, fontSize: 10),
        ),
      ),
      TextButton(onPressed: onRetry, child: const Text('Riprova')),
    ],
  );
}

class _ApiKeyDialog extends StatefulWidget {
  const _ApiKeyDialog({required this.providerId, super.key});

  final String providerId;

  @override
  State<_ApiKeyDialog> createState() => _ApiKeyDialogState();
}

class _ApiKeyDialogState extends State<_ApiKeyDialog> {
  final _controller = TextEditingController();
  bool _obscure = true;
  String? _validationMessage;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final providerName = _displayName(widget.providerId);
    return AlertDialog(
      backgroundColor: JackPalette.panel,
      titlePadding: const EdgeInsets.fromLTRB(22, 20, 22, 6),
      contentPadding: const EdgeInsets.fromLTRB(22, 8, 22, 4),
      title: Row(
        children: [
          Expanded(
            child: Text(
              'Configura $providerName',
              style: TextStyle(color: JackPalette.text, fontSize: 16),
            ),
          ),
        ],
      ),
      content: SizedBox(
        width: 410,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Inserisci la chiave API di $providerName. Il backend la salva nel Keychain macOS; l’app Flutter la trasmette solo al backend locale e non la salva.',
              style: TextStyle(color: JackPalette.muted, fontSize: 11, height: 1.5),
            ),
            const SizedBox(height: 14),
            TextField(
              key: const ValueKey('api-key-field'),
              controller: _controller,
              obscureText: _obscure,
              autofocus: true,
              autocorrect: false,
              enableSuggestions: false,
              style: const TextStyle(color: JackPalette.text, fontSize: 12),
              decoration: InputDecoration(
                labelText: '${providerName} API key',
                errorText: _validationMessage,
                suffixIcon: IconButton(
                  tooltip: _obscure ? 'Mostra chiave' : 'Nascondi chiave',
                  onPressed: () => setState(() => _obscure = !_obscure),
                  icon: Icon(
                    _obscure
                        ? Icons.visibility_outlined
                        : Icons.visibility_off_outlined,
                  ),
                ),
              ),
              onSubmitted: (_) => _submit(),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Annulla'),
        ),
        FilledButton(
          key: const ValueKey('save-api-key'),
          onPressed: _submit,
          child: const Text('Salva nel Keychain'),
        ),
      ],
    );
  }

  String _displayName(String providerId) {
    switch (providerId) {
      case 'google':
        return 'Google Gemini';
      case 'groq':
        return 'GroqCloud';
      case 'openrouter':
        return 'OpenRouter';
      case 'ollama':
        return 'Ollama';
      case 'nvidia':
        return 'NVIDIA Nemotron';
      default:
        return providerId;
    }
  }

  void _submit() {
    final value = _controller.text.trim();
    if (value.length < 8) {
      setState(() => _validationMessage = 'Inserisci una chiave API valida.');
      return;
    }
    _controller.clear();
    Navigator.of(context).pop(value);
  }
}
