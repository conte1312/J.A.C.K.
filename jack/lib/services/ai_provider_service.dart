import '../models/ai_provider.dart';
import 'local_api_client.dart';

abstract interface class AiProviderGateway {
  Future<AiMultiProviderConfiguration> loadProviderConfiguration();
  Future<AiMultiProviderConfiguration> saveProviderApiKey(
    String providerId,
    String value,
  );
  Future<AiMultiProviderConfiguration> removeProviderApiKey(String providerId);
  Future<AiMultiProviderConfiguration> testProviderConnection(
    String providerId,
    String modelId,
  );
  Future<AiMultiProviderConfiguration> setProviderOrder(List<String> order);
  Future<AiMultiProviderConfiguration> setProviderEnabled(
    String providerId,
    bool enabled,
  );
  Future<AiMultiProviderConfiguration> selectProviderAndModel(
    String providerId,
    String? modelId,
  );
  Future<AiChatResponse> sendChat({
    required String? modelId,
    required List<AiChatTurn> messages,
  });
}

class AiProviderService implements AiProviderGateway {
  AiProviderService({LocalApiClient? apiClient})
    : _apiClient = apiClient ?? LocalApiClient(
        timeout: const Duration(seconds: 60),
      );

  final LocalApiClient _apiClient;

  @override
  Future<AiMultiProviderConfiguration> loadProviderConfiguration() async =>
      AiMultiProviderConfiguration.fromJson(
        await _apiClient.getJson('/api/v1/ai/providers'),
      );

  @override
  Future<AiMultiProviderConfiguration> saveProviderApiKey(
    String providerId,
    String value,
  ) async =>
      AiMultiProviderConfiguration.fromJson(
        await _apiClient.putJson(
          '/api/v1/ai/providers/${Uri.encodeComponent(providerId)}/credentials',
          {'provider_id': providerId, 'api_key': value},
        ),
      );

  @override
  Future<AiMultiProviderConfiguration> removeProviderApiKey(
    String providerId,
  ) async =>
      AiMultiProviderConfiguration.fromJson(
        await _apiClient.deleteJson(
          '/api/v1/ai/providers/${Uri.encodeComponent(providerId)}/credentials',
        ),
      );

  @override
  Future<AiMultiProviderConfiguration> testProviderConnection(
    String providerId,
    String modelId,
  ) async =>
      AiMultiProviderConfiguration.fromJson(
        await _apiClient.postJson(
          '/api/v1/ai/providers/${Uri.encodeComponent(providerId)}/test',
          {'model_id': modelId},
        ),
      );

  @override
  Future<AiMultiProviderConfiguration> setProviderOrder(
    List<String> order,
  ) async =>
      AiMultiProviderConfiguration.fromJson(
        await _apiClient.putJson(
          '/api/v1/ai/provider-order',
          {'provider_order': order},
        ),
      );

  @override
  Future<AiMultiProviderConfiguration> setProviderEnabled(
    String providerId,
    bool enabled,
  ) async =>
      AiMultiProviderConfiguration.fromJson(
        await _apiClient.putJson(
          '/api/v1/ai/providers/${Uri.encodeComponent(providerId)}/enabled',
          {'provider_id': providerId, 'enabled': enabled},
        ),
      );

  @override
  Future<AiMultiProviderConfiguration> selectProviderAndModel(
    String providerId,
    String? modelId,
  ) async =>
      AiMultiProviderConfiguration.fromJson(
        await _apiClient.putJson(
          '/api/v1/ai/selection',
          {'model_id': modelId},
        ),
      );

  @override
  Future<AiChatResponse> sendChat({
    required String? modelId,
    required List<AiChatTurn> messages,
  }) async => AiChatResponse.fromJson(
        await _apiClient.postJson(
          '/api/v1/chat',
          {
            'model_id': modelId,
            'messages': messages.map((message) => message.toJson()).toList(),
          },
        ),
      );
}
