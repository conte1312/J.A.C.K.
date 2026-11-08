import 'package:flutter/material.dart';

import '../models/system_monitor.dart';
import '../services/local_api_client.dart';
import '../services/system_monitor_service.dart';
import '../theme/jack_theme.dart';
import '../widgets/jack_primitives.dart';

class SystemMonitorScreen extends StatefulWidget {
  const SystemMonitorScreen({required this.reader, super.key});

  final SystemMonitorReader reader;

  @override
  State<SystemMonitorScreen> createState() => _SystemMonitorScreenState();
}

class _SystemMonitorScreenState extends State<SystemMonitorScreen> {
  SystemMonitorSnapshot? _snapshot;
  LocalBackupCatalog? _backupCatalog;
  SecurityPostureSnapshot? _securityPosture;
  String? _error;
  String? _backupError;
  String? _securityError;
  bool _loading = true;
  bool _backupsLoading = true;
  bool _creatingBackup = false;
  String? _validatingBackup;

  @override
  void initState() {
    super.initState();
    _load();
    _loadBackups();
    _loadSecurityPosture();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await widget.reader.readSnapshot();
      if (!mounted) return;
      setState(() {
        _snapshot = result;
        _loading = false;
      });
    } on LocalApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loading = false;
      });
    } on FormatException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() {
        _error = 'Impossibile leggere lo stato del sistema locale.';
        _loading = false;
      });
    }
  }

  Future<void> _loadBackups() async {
    setState(() {
      _backupsLoading = true;
      _backupError = null;
    });
    try {
      final result = await widget.reader.listBackups();
      if (!mounted) return;
      setState(() {
        _backupCatalog = result;
        _backupsLoading = false;
      });
    } on LocalApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _backupError = error.message;
        _backupsLoading = false;
      });
    } on FormatException catch (error) {
      if (!mounted) return;
      setState(() {
        _backupError = error.message;
        _backupsLoading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() {
        _backupError = 'Impossibile leggere i backup locali.';
        _backupsLoading = false;
      });
    }
  }

  Future<void> _loadSecurityPosture() async {
    try {
      final result = await widget.reader.readSecurityPosture();
      if (!mounted) return;
      setState(() {
        _securityPosture = result;
        _securityError = null;
      });
    } on LocalApiException catch (error) {
      if (!mounted) return;
      setState(() => _securityError = error.message);
    } on FormatException catch (error) {
      if (!mounted) return;
      setState(() => _securityError = error.message);
    } on Exception {
      if (!mounted) return;
      setState(() {
        _securityError = 'Impossibile leggere lo stato di sicurezza.';
      });
    }
  }

  Future<void> _createBackup() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Creare un backup locale?'),
        content: const Text(
          'Il backup contiene conversazioni, memoria e pianificazione. '
          'L’archivio ZIP non è cifrato: proteggi l’accesso a questo Mac.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Annulla'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Crea backup'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    setState(() {
      _creatingBackup = true;
      _backupError = null;
    });
    try {
      final backup = await widget.reader.createBackup();
      if (!mounted) return;
      setState(() {
        final backups = [
          backup,
          ...?_backupCatalog?.backups.where(
            (item) => item.filename != backup.filename,
          ),
        ];
        _backupCatalog = LocalBackupCatalog(
          directory: _backupCatalog?.directory ?? '',
          backups: backups,
        );
        _creatingBackup = false;
      });
    } on LocalApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _backupError = error.message;
        _creatingBackup = false;
      });
    } on FormatException catch (error) {
      if (!mounted) return;
      setState(() {
        _backupError = error.message;
        _creatingBackup = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() {
        _backupError = 'Impossibile creare il backup locale.';
        _creatingBackup = false;
      });
    }
  }

  Future<void> _validateBackup(LocalBackupRecord backup) async {
    setState(() {
      _validatingBackup = backup.filename;
      _backupError = null;
    });
    try {
      final validation = await widget.reader.validateBackup(backup.filename);
      if (!mounted) return;
      setState(() => _validatingBackup = null);
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Backup verificato'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(validation.filename),
              const SizedBox(height: 12),
              for (final database in validation.databases)
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    '${database.name}: integrità SQLite OK · schema ${database.schemaVersion}',
                  ),
                ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Chiudi'),
            ),
          ],
        ),
      );
    } on LocalApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _backupError = error.message;
        _validatingBackup = null;
      });
    } on FormatException catch (error) {
      if (!mounted) return;
      setState(() {
        _backupError = error.message;
        _validatingBackup = null;
      });
    } on Exception {
      if (!mounted) return;
      setState(() {
        _backupError = 'Impossibile verificare il backup locale.';
        _validatingBackup = null;
      });
    }
  }

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Row(
        children: [
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SectionEyebrow('Sistema'),
                SizedBox(height: 5),
                Text(
                  'Monitor locale',
                  style: TextStyle(fontSize: 21, fontWeight: FontWeight.w300),
                ),
              ],
            ),
          ),
          IconButton(
            tooltip: 'Aggiorna stato',
            onPressed: _loading || _backupsLoading
                ? null
                : () {
                    _load();
                    _loadBackups();
                    _loadSecurityPosture();
                  },
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      const SizedBox(height: 18),
      if (_loading && _snapshot == null)
        const Expanded(child: Center(child: CircularProgressIndicator()))
      else if (_error != null && _snapshot == null)
        Expanded(
          child: Center(
            child: _MonitorNotice(
              title: 'Monitor non disponibile',
              message: _error!,
              action: TextButton.icon(
                onPressed: _load,
                icon: const Icon(Icons.refresh),
                label: const Text('Riprova'),
              ),
            ),
          ),
        )
      else
        Expanded(
          child: RefreshIndicator(
            onRefresh: _load,
            child: ListView(
              children: [
                if (_error != null)
                  _MonitorNotice(
                    title: 'Aggiornamento non riuscito',
                    message: _error!,
                  ),
                _sectionCard(
                  title: 'Backend',
                  subtitle:
                      'Processo locale · PID ${_snapshot!.backend.processId}',
                  child: Wrap(
                    spacing: 24,
                    runSpacing: 12,
                    children: [
                      _Metric(
                        label: 'STATO',
                        value: _snapshot!.backend.status == 'ok'
                            ? 'Operativo'
                            : _snapshot!.backend.status,
                        color: JackPalette.green,
                      ),
                      _Metric(
                        label: 'MEMORIA MASSIMA',
                        value: _formatBytes(_snapshot!.backend.peakMemoryBytes),
                      ),
                      _Metric(
                        label: 'CPU CUMULATIVA',
                        value:
                            '${(_snapshot!.backend.cpuUserSeconds + _snapshot!.backend.cpuSystemSeconds).toStringAsFixed(1)} s',
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                _sectionCard(
                  title: 'Disco dati',
                  subtitle:
                      '${_formatBytes(_snapshot!.disk.freeBytes)} liberi su ${_formatBytes(_snapshot!.disk.totalBytes)}',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      LinearProgressIndicator(
                        value: _snapshot!.disk.totalBytes == 0
                            ? 0
                            : (_snapshot!.disk.usedBytes /
                                      _snapshot!.disk.totalBytes)
                                  .clamp(0, 1)
                                  .toDouble(),
                        minHeight: 6,
                        color: JackPalette.cyan,
                        backgroundColor: JackPalette.panelRaised,
                      ),
                      const SizedBox(height: 7),
                      Text(
                        '${_formatBytes(_snapshot!.disk.usedBytes)} utilizzati',
                        style: const TextStyle(
                          color: JackPalette.muted,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                _sectionCard(
                  title: 'Database locali',
                  subtitle: 'Controllo integrità SQLite in sola lettura',
                  child: Column(
                    children: [
                      for (final database in _snapshot!.databases)
                        _DatabaseRow(database: database),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                _sectionCard(
                  title: 'Backup locali',
                  subtitle: _backupCatalog?.directory.isNotEmpty == true
                      ? _backupCatalog!.directory
                      : 'Snapshot SQLite locali · archivio non cifrato',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (_backupError != null)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Text(
                            _backupError!,
                            style: const TextStyle(
                              color: JackPalette.red,
                              fontSize: 11,
                            ),
                          ),
                        ),
                      if (_backupsLoading)
                        const LinearProgressIndicator(minHeight: 2)
                      else if (_backupCatalog?.backups.isNotEmpty != true)
                        const Padding(
                          padding: EdgeInsets.only(bottom: 12),
                          child: Text(
                            'Nessun backup locale disponibile.',
                            style: TextStyle(
                              color: JackPalette.muted,
                              fontSize: 11,
                            ),
                          ),
                        )
                      else
                        for (final backup in _backupCatalog!.backups)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: Row(
                              children: [
                                const Icon(
                                  Icons.archive_outlined,
                                  color: JackPalette.cyan,
                                  size: 18,
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(
                                    backup.filename,
                                    style: const TextStyle(fontSize: 11),
                                  ),
                                ),
                                Text(
                                  _formatBytes(backup.sizeBytes),
                                  style: const TextStyle(
                                    color: JackPalette.muted,
                                    fontSize: 10,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                TextButton(
                                  onPressed: _validatingBackup == null
                                      ? () => _validateBackup(backup)
                                      : null,
                                  child: _validatingBackup == backup.filename
                                      ? const SizedBox(
                                          width: 14,
                                          height: 14,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                          ),
                                        )
                                      : const Text('Verifica'),
                                ),
                              ],
                            ),
                          ),
                      Align(
                        alignment: Alignment.centerRight,
                        child: FilledButton.icon(
                          onPressed: _creatingBackup ? null : _createBackup,
                          icon: _creatingBackup
                              ? const SizedBox(
                                  width: 14,
                                  height: 14,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.backup_outlined),
                          label: Text(
                            _creatingBackup ? 'Creazione…' : 'Crea backup',
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                _sectionCard(
                  title: 'Stato sicurezza',
                  subtitle: 'Quadro informativo delle capacità effettivamente disponibili',
                  child: _securityPosture == null
                      ? Text(
                          _securityError ?? 'Caricamento…',
                          style: TextStyle(
                            color: _securityError == null
                                ? JackPalette.muted
                                : JackPalette.red,
                            fontSize: 11,
                          ),
                        )
                      : Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _SecurityStatusRow(
                              label: 'Esposizione API',
                              value:
                                  'Solo loopback (${_securityPosture!.apiBindHost})',
                            ),
                            _SecurityStatusRow(
                              label: 'Esecuzione autonoma',
                              value: 'Non disponibile',
                            ),
                            _SecurityStatusRow(
                              label: 'Approvazione azioni esterne',
                              value: 'Non implementata',
                            ),
                            _SecurityStatusRow(
                              label: 'Cifratura backup',
                              value: 'Non cifrati',
                            ),
                            _SecurityStatusRow(
                              label: 'Ripristino backup',
                              value: 'Non disponibile',
                            ),
                            const SizedBox(height: 8),
                            const Text(
                              'Questa schermata descrive lo stato corrente; '
                              'non applica né verifica autorizzazioni operative.',
                              style: TextStyle(
                                color: JackPalette.amber,
                                fontSize: 10,
                              ),
                            ),
                          ],
                        ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Aggiornato ${_snapshot!.checkedAt.toLocal()} · metriche cumulative del processo, non consumo istantaneo.',
                  style: const TextStyle(color: JackPalette.dim, fontSize: 10),
                ),
                const SizedBox(height: 16),
              ],
            ),
          ),
        ),
    ],
  );

  Widget _sectionCard({
    required String title,
    required String subtitle,
    required Widget child,
  }) => JackPanel(
    padding: const EdgeInsets.all(16),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontSize: 14)),
        const SizedBox(height: 4),
        Text(
          subtitle,
          style: const TextStyle(color: JackPalette.muted, fontSize: 10),
        ),
        const SizedBox(height: 14),
        child,
      ],
    ),
  );

  String _formatBytes(int bytes) {
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    var value = bytes.toDouble();
    var unit = 0;
    while (value >= 1024 && unit < units.length - 1) {
      value /= 1024;
      unit++;
    }
    return '${value.toStringAsFixed(unit == 0 ? 0 : 1)} ${units[unit]}';
  }
}

class _DatabaseRow extends StatelessWidget {
  const _DatabaseRow({required this.database});

  final DatabaseHealthSnapshot database;

  @override
  Widget build(BuildContext context) {
    final statusLabel = switch (database.status) {
      'ok' => 'Integro',
      'missing' => 'Non inizializzato',
      _ => 'Errore',
    };
    final color = switch (database.status) {
      'ok' => JackPalette.green,
      'missing' => JackPalette.amber,
      _ => JackPalette.red,
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Icon(
            database.status == 'ok'
                ? Icons.check_circle_outline
                : database.status == 'missing'
                ? Icons.info_outline
                : Icons.error_outline,
            color: color,
            size: 18,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(database.name),
                const SizedBox(height: 2),
                Text(
                  [
                    statusLabel,
                    if (database.sizeBytes != null)
                      _formatBytes(database.sizeBytes!),
                    if (database.schemaVersion != null)
                      'schema v${database.schemaVersion}',
                  ].join(' · '),
                  style: TextStyle(color: color, fontSize: 10),
                ),
                if (database.error != null)
                  Text(
                    database.error!,
                    style: const TextStyle(
                      color: JackPalette.red,
                      fontSize: 10,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _formatBytes(int bytes) {
    if (bytes < 1024) return '$bytes B';
    final kilobytes = bytes / 1024;
    if (kilobytes < 1024) return '${kilobytes.toStringAsFixed(1)} KB';
    return '${(kilobytes / 1024).toStringAsFixed(1)} MB';
  }
}

class _Metric extends StatelessWidget {
  const _Metric({
    required this.label,
    required this.value,
    this.color = JackPalette.text,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(label, style: const TextStyle(color: JackPalette.dim, fontSize: 9)),
      const SizedBox(height: 3),
      Text(value, style: TextStyle(color: color, fontSize: 13)),
    ],
  );
}

class _SecurityStatusRow extends StatelessWidget {
  const _SecurityStatusRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 9),
    child: Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: const TextStyle(color: JackPalette.muted, fontSize: 11),
          ),
        ),
        Text(value, style: const TextStyle(fontSize: 11)),
      ],
    ),
  );
}

class _MonitorNotice extends StatelessWidget {
  const _MonitorNotice({
    required this.title,
    required this.message,
    this.action,
  });

  final String title;
  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) => JackPanel(
    padding: const EdgeInsets.all(16),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(color: JackPalette.amber)),
        const SizedBox(height: 6),
        Text(message, style: const TextStyle(color: JackPalette.muted)),
        if (action != null) ...[const SizedBox(height: 8), action!],
      ],
    ),
  );
}
