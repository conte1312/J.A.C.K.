import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jack/models/system_monitor.dart';
import 'package:jack/screens/system_monitor_screen.dart';
import 'package:jack/services/system_monitor_service.dart';

void main() {
  testWidgets('shows real local backend, disk, and database health', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SystemMonitorScreen(reader: _MonitorReader(_snapshot)),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Monitor locale'), findsOneWidget);
    expect(find.text('Backend'), findsOneWidget);
    expect(find.text('Disco dati'), findsOneWidget);
    expect(find.text('Database locali'), findsOneWidget);
    expect(find.text('Memoria e conversazioni'), findsOneWidget);
    expect(find.text('Pianificazione'), findsOneWidget);
    await tester.ensureVisible(find.text('Backup locali'));
    await tester.pump();
    expect(find.text('Nessun backup locale disponibile.'), findsOneWidget);
    await tester.ensureVisible(find.text('Stato sicurezza'));
    await tester.pump();
    expect(find.text('Esecuzione autonoma'), findsOneWidget);
    expect(find.text('Non implementata'), findsOneWidget);
    await tester.ensureVisible(find.text('Pianificazione'));
    await tester.pump();
    expect(find.textContaining('schema v2'), findsNWidgets(2));
    expect(find.text('DATI DEMO'), findsNothing);
  });

  testWidgets('surfaces monitor errors and retries', (tester) async {
    final reader = _MonitorReader(_snapshot, failFirst: true);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: SystemMonitorScreen(reader: reader)),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Monitor non disponibile'), findsOneWidget);
    expect(find.text('Backend non raggiungibile'), findsOneWidget);
    await tester.tap(find.text('Riprova'));
    await tester.pumpAndSettle();
    expect(find.text('Database locali'), findsOneWidget);
  });

  testWidgets('confirms backup creation and lists the archive', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SystemMonitorScreen(reader: _MonitorReader(_snapshot)),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Crea backup'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Crea backup'));
    await tester.pumpAndSettle();

    expect(find.textContaining('non è cifrato'), findsOneWidget);
    await tester.tap(find.text('Crea backup').last);
    await tester.pumpAndSettle();

    expect(
      find.text('jack-backup-20261108T120000Z-123456abcdef.zip'),
      findsOneWidget,
    );
  });

  testWidgets('verifies a listed backup and shows SQLite integrity', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SystemMonitorScreen(
            reader: _MonitorReader(_snapshot, includeBackup: true),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.drag(find.byType(ListView), const Offset(0, -700));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Verifica'));
    await tester.pumpAndSettle();

    expect(find.text('Backup verificato'), findsOneWidget);
    expect(find.textContaining('integrità SQLite OK'), findsOneWidget);
  });
}

final _snapshot = SystemMonitorSnapshot(
  checkedAt: DateTime(2026, 11, 8),
  backend: BackendProcessSnapshot(
    status: 'ok',
    processId: 123,
    cpuUserSeconds: 1.5,
    cpuSystemSeconds: 0.3,
    peakMemoryBytes: 16 * 1024 * 1024,
  ),
  disk: DiskSnapshot(
    totalBytes: 100 * 1024 * 1024,
    freeBytes: 60 * 1024 * 1024,
    usedBytes: 40 * 1024 * 1024,
  ),
  databases: [
    DatabaseHealthSnapshot(
      name: 'Memoria e conversazioni',
      status: 'ok',
      sizeBytes: 1024,
      schemaVersion: 2,
      integrity: true,
    ),
    DatabaseHealthSnapshot(
      name: 'Pianificazione',
      status: 'ok',
      sizeBytes: 2048,
      schemaVersion: 2,
      integrity: true,
    ),
  ],
);

class _MonitorReader implements SystemMonitorReader, LocalBackupReader {
  _MonitorReader(
    this.snapshot, {
    this.failFirst = false,
    this.includeBackup = false,
  });

  final SystemMonitorSnapshot? snapshot;
  bool failFirst;
  final bool includeBackup;

  @override
  Future<SystemMonitorSnapshot> readSnapshot() async {
    if (failFirst) {
      failFirst = false;
      throw const FormatException('Backend non raggiungibile');
    }
    return snapshot!;
  }

  @override
  Future<LocalBackupCatalog> listBackups() async => LocalBackupCatalog(
    directory: '/local/backups',
    backups: includeBackup
        ? [
            LocalBackupRecord(
              filename: 'jack-backup-20261108T120000Z-123456abcdef.zip',
              createdAt: DateTime(2026, 11, 8, 12),
              sizeBytes: 512,
            ),
          ]
        : [],
  );

  @override
  Future<LocalBackupRecord> createBackup() async => LocalBackupRecord(
    filename: 'jack-backup-20261108T120000Z-123456abcdef.zip',
    createdAt: DateTime(2026, 11, 8, 12),
    sizeBytes: 512,
  );

  @override
  Future<LocalBackupValidation> validateBackup(String filename) async =>
      LocalBackupValidation(
        filename: filename,
        valid: true,
        databases: const [
          LocalBackupDatabaseValidation(
            name: 'Memoria',
            filename: 'memories.sqlite3',
            schemaVersion: 3,
            integrity: true,
          ),
        ],
      );

  @override
  Future<SecurityPostureSnapshot> readSecurityPosture() async =>
      const SecurityPostureSnapshot(
        apiBindHost: '127.0.0.1',
        apiScope: 'loopback',
        autonomousExecution: 'not_available',
        externalActionApproval: 'not_enforced',
        backupEncryption: 'not_encrypted',
        restore: 'not_available',
        informationalOnly: true,
      );
}
