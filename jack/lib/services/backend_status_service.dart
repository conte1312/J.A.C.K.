import 'local_api_client.dart';

enum BackendConnectionState { loading, connected, disconnected }

class BackendSnapshot {
  const BackendSnapshot({
    required this.name,
    required this.version,
    required this.modules,
  });

  final String name;
  final String version;
  final List<String> modules;
}

abstract interface class BackendStatusReader {
  Future<BackendSnapshot?> check();
}

class BackendStatusService implements BackendStatusReader {
  BackendStatusService({
    Uri? baseUri,
    Duration timeout = const Duration(milliseconds: 1400),
  }) : _apiClient = LocalApiClient(baseUri: baseUri, timeout: timeout);

  final LocalApiClient _apiClient;

  @override
  Future<BackendSnapshot?> check() async {
    try {
      final health = await _apiClient.getJson('/health');
      if (health is! Map<String, dynamic> || health['status'] != 'ok') {
        return null;
      }

      final info = await _apiClient.getJson('/api/v1/info');
      if (info is! Map<String, dynamic> ||
          info['name'] is! String ||
          info['version'] is! String) {
        return null;
      }

      final rawModules = info['modules'];
      final modules = rawModules is List
          ? rawModules.whereType<String>().toList(growable: false)
          : const <String>[];

      return BackendSnapshot(
        name: info['name'] as String,
        version: info['version'] as String,
        modules: modules,
      );
    } on Exception {
      return null;
    }
  }
}
