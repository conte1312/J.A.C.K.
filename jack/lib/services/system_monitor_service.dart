import '../models/system_monitor.dart';
import 'local_api_client.dart';

abstract interface class SystemMonitorReader implements LocalBackupReader {
  Future<SystemMonitorSnapshot> readSnapshot();

  Future<SecurityPostureSnapshot> readSecurityPosture();
}

abstract interface class LocalBackupReader {
  Future<LocalBackupCatalog> listBackups();

  Future<LocalBackupRecord> createBackup();

  Future<LocalBackupValidation> validateBackup(String filename);
}

class SystemMonitorApiService
    implements SystemMonitorReader, LocalBackupReader {
  SystemMonitorApiService({LocalApiClient? client})
    : _client = client ?? LocalApiClient();

  final LocalApiClient _client;

  @override
  Future<SystemMonitorSnapshot> readSnapshot() async {
    final response = await _client.getJson('/api/v1/system/monitor');
    if (response is! Map<String, dynamic>) {
      throw const FormatException('Diagnostica di sistema non valida.');
    }
    return SystemMonitorSnapshot.fromJson(response);
  }

  @override
  Future<LocalBackupCatalog> listBackups() async {
    final response = await _client.getJson('/api/v1/system/backups');
    if (response is! Map<String, dynamic>) {
      throw const FormatException('Elenco backup non valido.');
    }
    return LocalBackupCatalog.fromJson(response);
  }

  @override
  Future<LocalBackupRecord> createBackup() async {
    final response = await _client.postJson('/api/v1/system/backups', {});
    if (response is! Map<String, dynamic>) {
      throw const FormatException('Risposta backup non valida.');
    }
    return LocalBackupRecord.fromJson(response);
  }

  @override
  Future<LocalBackupValidation> validateBackup(String filename) async {
    final response = await _client.postJson(
      '/api/v1/system/backups/${Uri.encodeComponent(filename)}/validate',
      {},
    );
    if (response is! Map<String, dynamic>) {
      throw const FormatException('Risultato verifica backup non valido.');
    }
    return LocalBackupValidation.fromJson(response);
  }

  @override
  Future<SecurityPostureSnapshot> readSecurityPosture() async {
    final response = await _client.getJson('/api/v1/system/security-status');
    if (response is! Map<String, dynamic>) {
      throw const FormatException('Stato sicurezza non valido.');
    }
    return SecurityPostureSnapshot.fromJson(response);
  }
}
