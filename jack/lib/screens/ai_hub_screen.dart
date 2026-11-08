import 'dart:async';

import 'package:flutter/material.dart';

import '../models/ai_provider.dart';
import '../services/ai_provider_service.dart';
import '../theme/jack_theme.dart';
import '../widgets/ai_hub_provider_panel.dart';
import '../widgets/jack_primitives.dart';

class AiHubScreen extends StatefulWidget {
  const AiHubScreen({
    required this.onReturn,
    this.providerGateway,
    super.key,
  });

  final VoidCallback onReturn;
  final AiProviderGateway? providerGateway;

  @override
  State<AiHubScreen> createState() => _AiHubScreenState();
}

class _AiHubScreenState extends State<AiHubScreen> {
  late final AiProviderGateway _providerGateway;
  AiMultiProviderConfiguration? _configuration;
  String? _loadError;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _providerGateway = widget.providerGateway ?? AiProviderService();
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
      final configuration = await _providerGateway.loadProviderConfiguration();
      if (!mounted) return;
      setState(() {
        _configuration = configuration;
        _loading = false;
      });
    } on AiProviderException catch (error) {
      if (!mounted) return;
      setState(() {
        _loadError = error.message;
        _loading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() {
        _loadError =
            'Errore inatteso durante la lettura della configurazione AI.';
        _loading = false;
      });
    }
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
            )
          : _buildContent(_configuration!),
    );
  }

  Widget _buildContent(AiMultiProviderConfiguration configuration) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(24, 22, 24, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _PageHeader(onReturn: widget.onReturn),
          const SizedBox(height: 15),
          AiHubProviderPanel(gateway: _providerGateway),
          const SizedBox(height: 15),
          Container(
            key: const ValueKey('ai-hub-provider-notice'),
            padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 11),
            decoration: BoxDecoration(
              color: JackPalette.cyan.withValues(alpha: 0.055),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: JackPalette.cyan.withValues(alpha: 0.18),
              ),
            ),
            child: const Row(
              children: [
                Icon(
                  Icons.info_outline_rounded,
                  color: JackPalette.cyan,
                  size: 15,
                ),
                SizedBox(width: 9),
                Expanded(
                  child: Text(
                    'Il pannello sopra legge lo stato reale dei provider AI dal backend (NVIDIA, Gemini, Groq, OpenRouter, Ollama). Le chiavi API sono salvate nel Keychain macOS; l’app Flutter non le memorizza.',
                    style: TextStyle(
                      color: JackPalette.muted,
                      fontSize: 9,
                      height: 1.5,
                    ),
                  ),
                ),
                SizedBox(width: 8),
                DemoBadge(label: 'SOLO PROVIDER GRATUITI'),
              ],
            ),
          ),
          const SizedBox(height: 24),
          const _ProviderOrderNotice(),
        ],
      ),
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
              SectionEyebrow('Provider AI'),
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
                'Configurazione provider, chiavi API e ordine di routing.',
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

class _ProviderOrderNotice extends StatelessWidget {
  const _ProviderOrderNotice();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionEyebrow('ORDINE DI ROUTING'),
        const SizedBox(height: 6),
        Text(
          'I provider vengono contattati in ordine per ogni richiesta. Il primo provider gratuito e disponibile gestisce la chat. L’ordine può essere modificato dall’AI Hub.',
          style: TextStyle(
            color: JackPalette.muted,
            fontSize: 9,
            height: 1.5,
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
  });

  final String message;
  final VoidCallback onRetry;

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
                'Configurazione AI non disponibile',
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
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
