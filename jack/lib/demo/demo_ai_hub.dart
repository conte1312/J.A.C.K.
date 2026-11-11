/// Presentation data for the AI Hub screen.
///
/// Providers are real J.A.C.K. targets, but no provider is configured in M2
/// and no request is ever sent. The AI Hub runtime arrives with M5.
library;

import 'package:flutter/material.dart';

import '../design_system/jack_tone.dart';

class DemoAiProvider {
  const DemoAiProvider({
    required this.id,
    required this.name,
    required this.kind,
    required this.description,
    required this.envVar,
    required this.icon,
    required this.tone,
  });

  final String id;
  final String name;
  final String kind;
  final String description;
  final String envVar;
  final IconData icon;
  final JackTone tone;

  bool get isLocal => kind == 'Locale';
}

const List<DemoAiProvider> demoAiProviders = <DemoAiProvider>[
  DemoAiProvider(
    id: 'nvidia',
    name: 'NVIDIA NIM',
    kind: 'Cloud',
    description: 'Catalogo NVIDIA NIM con modelli Nemotron. La selezione dei modelli gratuiti sarà gestita dal Cost Guard.',
    envVar: 'NVIDIA_API_KEY',
    icon: Icons.memory_outlined,
    tone: JackTone.cyan,
  ),
  DemoAiProvider(
    id: 'gemini',
    name: 'Google Gemini',
    kind: 'Cloud',
    description: 'Modelli Gemini tramite Google AI Studio. La chiave sarà custodita nel Keychain macOS.',
    envVar: 'GEMINI_API_KEY',
    icon: Icons.auto_awesome_outlined,
    tone: JackTone.amber,
  ),
  DemoAiProvider(
    id: 'groq',
    name: 'GroqCloud',
    kind: 'Cloud',
    description: 'Inferenza ad alta velocità su modelli open. Provider candidato per risposte rapide e failover.',
    envVar: 'GROQ_API_KEY',
    icon: Icons.bolt_outlined,
    tone: JackTone.success,
  ),
  DemoAiProvider(
    id: 'openrouter',
    name: 'OpenRouter',
    kind: 'Cloud',
    description: 'Gateway multi-modello con catalogo gratuito selezionato. Nessun fallback premium sarà consentito.',
    envVar: 'OPENROUTER_API_KEY',
    icon: Icons.route_outlined,
    tone: JackTone.info,
  ),
  DemoAiProvider(
    id: 'ollama',
    name: 'Ollama',
    kind: 'Locale',
    description: 'Modelli eseguiti interamente su questo Mac, senza inviare dati a servizi esterni.',
    envVar: '',
    icon: Icons.computer_outlined,
    tone: JackTone.neutral,
  ),
];

/// Planned routing rules shown in the Routing tab.
const List<String> demoRoutingRules = <String>[
  'Ordine dei provider definito esplicitamente nell’AI Hub.',
  'Failover automatico solo tra provider abilitati e verificati.',
  'Timeout e numero di tentativi configurabili per provider.',
  'Cost Guard: nessuna richiesta a modelli non gratuiti.',
  'Credenziali lette dal Keychain macOS, mai scritte nei log.',
];
