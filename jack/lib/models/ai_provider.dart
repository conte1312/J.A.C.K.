class AiProviderException implements Exception {
  const AiProviderException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

enum AiProviderType { online, local }

class AiProviderModel {
  const AiProviderModel({
    required this.id,
    required this.name,
    required this.description,
    required this.isFree,
    this.contextWindow,
    this.maxOutputTokens,
    required this.enabled,
    required this.selected,
    required this.availabilityNote,
  });

  final String id;
  final String name;
  final String description;
  final bool isFree;
  final int? contextWindow;
  final int? maxOutputTokens;
  final bool enabled;
  final bool selected;
  final String availabilityNote;

  factory AiProviderModel.fromJson(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const AiProviderException('Risposta modello AI non valida.');
    }
    final id = value['id'];
    final name = value['name'];
    final description = value['description'];
    final isFree = value['is_free'];
    final contextWindow = value['context_window'];
    final maxOutputTokens = value['max_output_tokens'];
    final enabled = value['enabled'];
    final selected = value['selected'];
    final availability = value['availability_note'];
    if (id is! String ||
        name is! String ||
        description is! String ||
        isFree is! bool ||
        enabled is! bool ||
        selected is! bool ||
        availability is! String) {
      throw const AiProviderException('Risposta modello AI incompleta.');
    }
    return AiProviderModel(
      id: id,
      name: name,
      description: description,
      isFree: isFree,
      contextWindow: contextWindow,
      maxOutputTokens: maxOutputTokens,
      enabled: enabled,
      selected: selected,
      availabilityNote: availability,
    );
  }
}

class AiProviderInfo {
  const AiProviderInfo({
    required this.id,
    required this.name,
    required this.type,
    required this.baseUrl,
    required this.requiresCredential,
    required this.isFreeTierAvailable,
    required this.configured,
    required this.credentialSource,
    required this.available,
    required this.lastError,
    required this.quotaExhausted,
    required this.models,
    required this.selectedProvider,
  });

  final String id;
  final String name;
  final AiProviderType type;
  final String? baseUrl;
  final bool requiresCredential;
  final bool isFreeTierAvailable;
  final bool configured;
  final String? credentialSource;
  final bool available;
  final String? lastError;
  final bool quotaExhausted;
  final List<AiProviderModel> models;
  final bool selectedProvider;

  AiProviderModel? get selectedModel {
    for (final model in models) {
      if (model.selected) return model;
    }
    return null;
  }

  factory AiProviderInfo.fromJson(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const AiProviderException('Risposta provider AI non valida.');
    }
    final id = value['id'];
    final name = value['name'];
    final typeRaw = value['provider_type'];
    final baseUrl = value['base_url'];
    final requiresCredential = value['requires_credential'];
    final isFreeTierAvailable = value['is_free_tier_available'];
    final configured = value['configured'];
    final credentialSource = value['credential_source'];
    final available = value['available'];
    final lastError = value['last_error'];
    final quotaExhausted = value['quota_exhausted'];
    final selectedProvider = value['selected_provider'];
    final rawModels = value['models'];
    if (id is! String ||
        name is! String ||
        requiresCredential is! bool ||
        isFreeTierAvailable is! bool ||
        configured is! bool ||
        available is! bool ||
        quotaExhausted is! bool ||
        selectedProvider is! bool ||
        rawModels is! List) {
      throw const AiProviderException('Risposta provider AI incompleta.');
    }
    final type = switch (typeRaw) {
      'local' => AiProviderType.local,
      _ => AiProviderType.online,
    };
    return AiProviderInfo(
      id: id,
      name: name,
      type: type,
      baseUrl: baseUrl as String?,
      requiresCredential: requiresCredential,
      isFreeTierAvailable: isFreeTierAvailable,
      configured: configured,
      credentialSource: credentialSource as String?,
      available: available,
      lastError: lastError as String?,
      quotaExhausted: quotaExhausted,
      models: (rawModels)
          .map(AiProviderModel.fromJson)
          .toList(growable: false),
      selectedProvider: selectedProvider,
    );
  }
}

class AiRouterConfig {
  const AiRouterConfig({
    required this.providerOrder,
    required this.enabledProviders,
    required this.maxRetriesPerProvider,
    required this.failoverEnabled,
  });

  final List<String> providerOrder;
  final List<String> enabledProviders;
  final int maxRetriesPerProvider;
  final bool failoverEnabled;

  factory AiRouterConfig.fromJson(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const AiProviderException('Risposta configurazione router non valida.');
    }
    final providerOrder = value['provider_order'];
    final enabledProviders = value['enabled_providers'];
    final maxRetries = value['max_retries_per_provider'];
    final failover = value['failover_enabled'];
    if (providerOrder is! List ||
        enabledProviders is! List ||
        maxRetries is! int ||
        failover is! bool) {
      throw const AiProviderException('Configurazione router incompleta.');
    }
    return AiRouterConfig(
      providerOrder: List<String>.from(providerOrder),
      enabledProviders: List<String>.from(enabledProviders),
      maxRetriesPerProvider: maxRetries,
      failoverEnabled: failover,
    );
  }
}

class AiMultiProviderConfiguration {
  const AiMultiProviderConfiguration({
    required this.providers,
    required this.selectedProviderId,
    required this.selectedModelId,
    required this.providerOrder,
    required this.enabledProviders,
    required this.routerConfig,
  });

  final List<AiProviderInfo> providers;
  final String? selectedProviderId;
  final String? selectedModelId;
  final List<String> providerOrder;
  final List<String> enabledProviders;
  final AiRouterConfig routerConfig;

  AiProviderInfo? get selectedProvider {
    for (final provider in providers) {
      if (provider.id == selectedProviderId) return provider;
    }
    return null;
  }

  AiProviderModel? get selectedModel {
    final provider = selectedProvider;
    if (provider == null) return null;
    for (final model in provider.models) {
      if (model.id == selectedModelId) return model;
    }
    return null;
  }

  factory AiMultiProviderConfiguration.fromJson(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const AiProviderException(
        'Il backend non ha restituito la configurazione dei provider.',
      );
    }
    final rawProviders = value['providers'];
    final selectedProviderId = value['selected_provider_id'];
    final selectedModelId = value['selected_model_id'];
    final providerOrder = value['provider_order'];
    final enabledProviders = value['enabled_providers'];
    final rawRouter = value['router_config'];
    if (rawProviders is! List ||
        providerOrder is! List ||
        enabledProviders is! List ||
        rawRouter is! Map) {
      throw const AiProviderException('Configurazione provider incompleta.');
    }
    return AiMultiProviderConfiguration(
      providers: (rawProviders)
          .map(AiProviderInfo.fromJson)
          .toList(growable: false),
      selectedProviderId: selectedProviderId as String?,
      selectedModelId: selectedModelId as String?,
      providerOrder: List<String>.from(providerOrder),
      enabledProviders: List<String>.from(enabledProviders),
      routerConfig: AiRouterConfig.fromJson(rawRouter),
    );
  }
}

class AiChatTurn {
  const AiChatTurn({required this.role, required this.content});

  final String role;
  final String content;

  Map<String, String> toJson() => {'role': role, 'content': content};
}

class AiChatResponse {
  const AiChatResponse({
    required this.providerId,
    required this.modelId,
    required this.content,
  });

  final String providerId;
  final String modelId;
  final String content;

  factory AiChatResponse.fromJson(Object? value) {
    if (value is! Map<String, dynamic> ||
        value['provider_id'] is! String ||
        value['model_id'] is! String ||
        value['content'] is! String) {
      throw const AiProviderException(
        'La risposta del modello non ha il formato previsto.',
      );
    }
    return AiChatResponse(
      providerId: value['provider_id'] as String,
      modelId: value['model_id'] as String,
      content: value['content'] as String,
    );
  }
}
