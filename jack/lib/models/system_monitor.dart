class SystemMonitorSnapshot {
  const SystemMonitorSnapshot({
    required this.checkedAt,
    required this.backend,
    required this.disk,
    required this.databases,
  });

  final DateTime checkedAt;
  final BackendProcessSnapshot backend;
  final DiskSnapshot disk;
  final List<DatabaseHealthSnapshot> databases;

  factory SystemMonitorSnapshot.fromJson(Map<String, dynamic> json) =>
      SystemMonitorSnapshot(
        checkedAt: DateTime.parse(json['checked_at'] as String),
        backend: BackendProcessSnapshot.fromJson(
          json['backend'] as Map<String, dynamic>,
        ),
        disk: DiskSnapshot.fromJson(json['disk'] as Map<String, dynamic>),
        databases: (json['databases'] as List<dynamic>)
            .whereType<Map<String, dynamic>>()
            .map(DatabaseHealthSnapshot.fromJson)
            .toList(growable: false),
      );
}

class BackendProcessSnapshot {
  const BackendProcessSnapshot({
    required this.status,
    required this.processId,
    required this.cpuUserSeconds,
    required this.cpuSystemSeconds,
    required this.peakMemoryBytes,
  });

  final String status;
  final int processId;
  final double cpuUserSeconds;
  final double cpuSystemSeconds;
  final int peakMemoryBytes;

  factory BackendProcessSnapshot.fromJson(Map<String, dynamic> json) =>
      BackendProcessSnapshot(
        status: json['status'] as String,
        processId: json['pid'] as int,
        cpuUserSeconds: (json['cpu_user_seconds'] as num).toDouble(),
        cpuSystemSeconds: (json['cpu_system_seconds'] as num).toDouble(),
        peakMemoryBytes: json['peak_memory_bytes'] as int,
      );
}

class DiskSnapshot {
  const DiskSnapshot({
    required this.totalBytes,
    required this.freeBytes,
    required this.usedBytes,
  });

  final int totalBytes;
  final int freeBytes;
  final int usedBytes;

  factory DiskSnapshot.fromJson(Map<String, dynamic> json) => DiskSnapshot(
    totalBytes: json['total_bytes'] as int,
    freeBytes: json['free_bytes'] as int,
    usedBytes: json['used_bytes'] as int,
  );
}

class DatabaseHealthSnapshot {
  const DatabaseHealthSnapshot({
    required this.name,
    required this.status,
    this.sizeBytes,
    this.schemaVersion,
    this.integrity,
    this.error,
  });

  final String name;
  final String status;
  final int? sizeBytes;
  final int? schemaVersion;
  final bool? integrity;
  final String? error;

  factory DatabaseHealthSnapshot.fromJson(Map<String, dynamic> json) =>
      DatabaseHealthSnapshot(
        name: json['name'] as String,
        status: json['status'] as String,
        sizeBytes: json['size_bytes'] as int?,
        schemaVersion: json['schema_version'] as int?,
        integrity: json['integrity'] as bool?,
        error: json['error'] as String?,
      );
}

class LocalBackupCatalog {
  const LocalBackupCatalog({required this.directory, required this.backups});

  final String directory;
  final List<LocalBackupRecord> backups;

  factory LocalBackupCatalog.fromJson(Map<String, dynamic> json) =>
      LocalBackupCatalog(
        directory: json['directory'] as String,
        backups: (json['backups'] as List<dynamic>)
            .whereType<Map<String, dynamic>>()
            .map(LocalBackupRecord.fromJson)
            .toList(growable: false),
      );
}

class LocalBackupRecord {
  const LocalBackupRecord({
    required this.filename,
    required this.createdAt,
    required this.sizeBytes,
  });

  final String filename;
  final DateTime createdAt;
  final int sizeBytes;

  factory LocalBackupRecord.fromJson(Map<String, dynamic> json) =>
      LocalBackupRecord(
        filename: json['filename'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
        sizeBytes: json['size_bytes'] as int,
      );
}

class LocalBackupValidation {
  const LocalBackupValidation({
    required this.filename,
    required this.valid,
    required this.databases,
  });

  final String filename;
  final bool valid;
  final List<LocalBackupDatabaseValidation> databases;

  factory LocalBackupValidation.fromJson(Map<String, dynamic> json) =>
      LocalBackupValidation(
        filename: json['filename'] as String,
        valid: json['valid'] as bool,
        databases: (json['databases'] as List<dynamic>)
            .whereType<Map<String, dynamic>>()
            .map(LocalBackupDatabaseValidation.fromJson)
            .toList(growable: false),
      );
}

class LocalBackupDatabaseValidation {
  const LocalBackupDatabaseValidation({
    required this.name,
    required this.filename,
    required this.schemaVersion,
    required this.integrity,
  });

  final String name;
  final String filename;
  final int schemaVersion;
  final bool integrity;

  factory LocalBackupDatabaseValidation.fromJson(Map<String, dynamic> json) =>
      LocalBackupDatabaseValidation(
        name: json['name'] as String,
        filename: json['filename'] as String,
        schemaVersion: json['schema_version'] as int,
        integrity: json['integrity'] as bool,
      );
}

class SecurityPostureSnapshot {
  const SecurityPostureSnapshot({
    required this.apiBindHost,
    required this.apiScope,
    required this.autonomousExecution,
    required this.externalActionApproval,
    required this.backupEncryption,
    required this.restore,
    required this.informationalOnly,
  });

  final String apiBindHost;
  final String apiScope;
  final String autonomousExecution;
  final String externalActionApproval;
  final String backupEncryption;
  final String restore;
  final bool informationalOnly;

  factory SecurityPostureSnapshot.fromJson(Map<String, dynamic> json) =>
      SecurityPostureSnapshot(
        apiBindHost: json['api_bind_host'] as String,
        apiScope: json['api_scope'] as String,
        autonomousExecution: json['autonomous_execution'] as String,
        externalActionApproval: json['external_action_approval'] as String,
        backupEncryption: json['backup_encryption'] as String,
        restore: json['restore'] as String,
        informationalOnly: json['informational_only'] as bool,
      );
}
