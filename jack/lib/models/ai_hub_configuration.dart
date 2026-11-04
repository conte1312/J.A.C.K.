enum DemoAiProvider {
  openAi('OpenAI'),
  anthropic('Anthropic'),
  google('Google'),
  local('Modello locale');

  const DemoAiProvider(this.label);

  final String label;

  static DemoAiProvider fromName(String value) =>
      DemoAiProvider.values.firstWhere((provider) => provider.name == value);
}

enum AiHubTaskCategory {
  conversation('Conversazione generale'),
  coding('Coding'),
  analysis('Analisi e ragionamento'),
  vision('Visione'),
  offline('Locale / offline');

  const AiHubTaskCategory(this.label);

  final String label;

  static AiHubTaskCategory fromName(String value) =>
      AiHubTaskCategory.values.firstWhere((category) => category.name == value);
}

class DemoAiModel {
  const DemoAiModel({
    required this.id,
    required this.name,
    required this.provider,
    required this.capabilities,
    required this.demoCostLabel,
    required this.demoQuotaLabel,
  });

  final String id;
  final String name;
  final DemoAiProvider provider;
  final List<AiHubTaskCategory> capabilities;
  final String demoCostLabel;
  final String demoQuotaLabel;

  DemoAiModel copyWith({
    String? name,
    DemoAiProvider? provider,
    List<AiHubTaskCategory>? capabilities,
    String? demoCostLabel,
    String? demoQuotaLabel,
  }) {
    return DemoAiModel(
      id: id,
      name: name ?? this.name,
      provider: provider ?? this.provider,
      capabilities: capabilities ?? this.capabilities,
      demoCostLabel: demoCostLabel ?? this.demoCostLabel,
      demoQuotaLabel: demoQuotaLabel ?? this.demoQuotaLabel,
    );
  }

  Map<String, Object> toJson() => {
    'id': id,
    'name': name,
    'provider': provider.name,
    'capabilities': capabilities.map((item) => item.name).toList(),
    'demoCostLabel': demoCostLabel,
    'demoQuotaLabel': demoQuotaLabel,
  };

  factory DemoAiModel.fromJson(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Modello demo non valido.');
    }
    final rawCapabilities = value['capabilities'];
    if (rawCapabilities is! List) {
      throw const FormatException('Capacità del modello demo non valide.');
    }

    try {
      return DemoAiModel(
        id: _requiredString(value, 'id'),
        name: _requiredString(value, 'name'),
        provider: DemoAiProvider.fromName(_requiredString(value, 'provider')),
        capabilities: rawCapabilities
            .map((item) => AiHubTaskCategory.fromName(item as String))
            .toList(growable: false),
        demoCostLabel: _requiredString(value, 'demoCostLabel'),
        demoQuotaLabel: _requiredString(value, 'demoQuotaLabel'),
      );
    } on Object catch (error) {
      throw FormatException('Modello demo non valido: $error');
    }
  }
}

class AiHubConfiguration {
  const AiHubConfiguration({
    required this.models,
    required this.defaultModelId,
    required this.routes,
  });

  final List<DemoAiModel> models;
  final String defaultModelId;
  final Map<AiHubTaskCategory, String> routes;

  DemoAiModel? get defaultModel {
    for (final model in models) {
      if (model.id == defaultModelId) return model;
    }
    return null;
  }

  AiHubConfiguration copyWith({
    List<DemoAiModel>? models,
    String? defaultModelId,
    Map<AiHubTaskCategory, String>? routes,
  }) {
    return AiHubConfiguration(
      models: models ?? this.models,
      defaultModelId: defaultModelId ?? this.defaultModelId,
      routes: routes ?? this.routes,
    );
  }

  void validate() {
    if (models.isEmpty) {
      throw const FormatException('Aggiungi almeno un modello demo.');
    }

    final ids = <String>{};
    for (final model in models) {
      if (model.id.trim().isEmpty || !ids.add(model.id)) {
        throw const FormatException(
          'Gli identificativi dei modelli devono essere unici.',
        );
      }
      if (model.name.trim().isEmpty) {
        throw const FormatException('Il nome di ogni modello è obbligatorio.');
      }
      if (model.capabilities.isEmpty) {
        throw const FormatException(
          'Seleziona almeno una capacità per ogni modello.',
        );
      }
    }

    if (!ids.contains(defaultModelId)) {
      throw const FormatException('Il modello predefinito deve esistere.');
    }

    for (final category in AiHubTaskCategory.values) {
      final modelId = routes[category];
      if (modelId == null || !ids.contains(modelId)) {
        throw FormatException('Assegna un modello demo a “${category.label}”.');
      }
    }
  }

  Map<String, Object> toJson() => {
    'schemaVersion': 1,
    'models': models.map((model) => model.toJson()).toList(),
    'defaultModelId': defaultModelId,
    'routes': {for (final entry in routes.entries) entry.key.name: entry.value},
  };

  factory AiHubConfiguration.fromJson(Object? value) {
    if (value is! Map<String, dynamic> || value['schemaVersion'] != 1) {
      throw const FormatException(
        'Formato della configurazione AI Hub non supportato.',
      );
    }
    final rawModels = value['models'];
    final rawRoutes = value['routes'];
    if (rawModels is! List || rawRoutes is! Map<String, dynamic>) {
      throw const FormatException('Configurazione AI Hub incompleta.');
    }

    try {
      final configuration = AiHubConfiguration(
        models: rawModels.map(DemoAiModel.fromJson).toList(growable: false),
        defaultModelId: _requiredString(value, 'defaultModelId'),
        routes: {
          for (final entry in rawRoutes.entries)
            AiHubTaskCategory.fromName(entry.key): entry.value as String,
        },
      );
      configuration.validate();
      return configuration;
    } on Object catch (error) {
      throw FormatException('Configurazione AI Hub non valida: $error');
    }
  }

  static AiHubConfiguration demoDefaults() {
    const models = [
      DemoAiModel(
        id: 'openai-gpt-4.1',
        name: 'GPT-4.1',
        provider: DemoAiProvider.openAi,
        capabilities: [
          AiHubTaskCategory.conversation,
          AiHubTaskCategory.coding,
          AiHubTaskCategory.analysis,
          AiHubTaskCategory.vision,
        ],
        demoCostLabel: '0,02 crediti demo / 1.000 token',
        demoQuotaLabel: '120 unità demo / giorno',
      ),
      DemoAiModel(
        id: 'anthropic-claude-sonnet',
        name: 'Claude Sonnet · esempio',
        provider: DemoAiProvider.anthropic,
        capabilities: [
          AiHubTaskCategory.conversation,
          AiHubTaskCategory.coding,
          AiHubTaskCategory.analysis,
        ],
        demoCostLabel: '0,03 crediti demo / 1.000 token',
        demoQuotaLabel: '80 unità demo / giorno',
      ),
      DemoAiModel(
        id: 'google-gemini-flash',
        name: 'Gemini Flash · esempio',
        provider: DemoAiProvider.google,
        capabilities: [
          AiHubTaskCategory.conversation,
          AiHubTaskCategory.analysis,
          AiHubTaskCategory.vision,
        ],
        demoCostLabel: '0,01 crediti demo / 1.000 token',
        demoQuotaLabel: '160 unità demo / giorno',
      ),
      DemoAiModel(
        id: 'local-llama',
        name: 'Llama locale · esempio',
        provider: DemoAiProvider.local,
        capabilities: [
          AiHubTaskCategory.conversation,
          AiHubTaskCategory.coding,
          AiHubTaskCategory.analysis,
          AiHubTaskCategory.offline,
        ],
        demoCostLabel: 'non stimato · dato demo',
        demoQuotaLabel: 'sessione locale demo',
      ),
    ];

    final configuration = AiHubConfiguration(
      models: models,
      defaultModelId: 'openai-gpt-4.1',
      routes: const {
        AiHubTaskCategory.conversation: 'openai-gpt-4.1',
        AiHubTaskCategory.coding: 'anthropic-claude-sonnet',
        AiHubTaskCategory.analysis: 'anthropic-claude-sonnet',
        AiHubTaskCategory.vision: 'google-gemini-flash',
        AiHubTaskCategory.offline: 'local-llama',
      },
    );
    configuration.validate();
    return configuration;
  }
}

String _requiredString(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! String || value.trim().isEmpty) {
    throw FormatException('Il campo “$key” è obbligatorio.');
  }
  return value;
}
