import 'package:flutter/material.dart';

import '../services/backend_status_service.dart';
import '../services/system_monitor_service.dart';
import '../theme/jack_theme.dart';
import '../models/system_monitor.dart';
import '../widgets/jack_primitives.dart';

class SystemStatusScreen extends StatefulWidget {
  const SystemStatusScreen({
    this.backendStatusReader,
    this.systemMonitorReader,
    super.key,
  });

  final BackendStatusReader? backendStatusReader;
  final SystemMonitorReader? systemMonitorReader;

  @override
  State<SystemStatusScreen> createState() => _SystemStatusScreenState();
}

class _SystemStatusScreenState extends State<SystemStatusScreen> {
  BackendSnapshot? _snapshot;
  SystemMonitorSnapshot? _monitorSnapshot;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (!mounted) return;
    setState(() => _loading = true);

    final backend = widget.backendStatusReader ?? BackendStatusService();
    final monitor = widget.systemMonitorReader ?? SystemMonitorApiService();

    try {
      final results = await Future.wait<Object?>([
        backend.check(),
        monitor.readSnapshot(),
      ]);
      if (!mounted) return;
      setState(() {
        _snapshot = results[0] as BackendSnapshot?;
        _monitorSnapshot = results[1] as SystemMonitorSnapshot?;
        _loading = false;
      });
    } on Exception catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: JackPalette.canvas,
      body: SafeArea(
        child: _loading
            ? const Center(
                child: CircularProgressIndicator(color: JackPalette.amber),
              )
            : _error != null
            ? _ErrorState(message: _error!, onRetry: _load)
            : SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SectionEyebrow('Stato del sistema'),
                    const SizedBox(height: 12),
                    Text(
                      'Diagnostica J.A.C.K.',
                      style: TextStyle(
                        color: JackPalette.text,
                        fontSize: 24,
                        fontWeight: FontWeight.w300,
                      ),
                    ),
                    const SizedBox(height: 24),
                    if (_snapshot != null) ...[
                      JackPanel(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Backend',
                              style: TextStyle(
                                color: JackPalette.muted,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                letterSpacing: 1.2,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              _snapshot!.name,
                              style: const TextStyle(
                                color: JackPalette.text,
                                fontSize: 16,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Versione ${_snapshot!.version}',
                              style: TextStyle(
                                color: JackPalette.muted,
                                fontSize: 13,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Wrap(
                              spacing: 12,
                              runSpacing: 8,
                              children: _snapshot!.modules
                                  .map(
                                    (module) => Container(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 10,
                                        vertical: 6,
                                      ),
                                      decoration: BoxDecoration(
                                        color: JackPalette.panelHover,
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(
                                          color: JackPalette.border,
                                        ),
                                      ),
                                      child: Text(
                                        module,
                                        style: const TextStyle(
                                          color: JackPalette.cyan,
                                          fontSize: 12,
                                          fontWeight: FontWeight.w500,
                                        ),
                                      ),
                                    ),
                                  )
                                  .toList(growable: false),
                            ),
                          ],
                        ),
                      ),
                    ],
                    if (_monitorSnapshot != null) ...[
                      const SizedBox(height: 16),
                      JackPanel(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Database',
                              style: TextStyle(
                                color: JackPalette.muted,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                letterSpacing: 1.2,
                              ),
                            ),
                            const SizedBox(height: 8),
                            for (final db in _monitorSnapshot!.databases)
                              _DatabaseRow(db: db),
                          ],
                        ),
                      ),
                    ],
                    const SizedBox(height: 24),
                    FilledButton.icon(
                      onPressed: _load,
                      icon: const Icon(Icons.refresh, size: 16),
                      label: const Text('Aggiorna'),
                    ),
                  ],
                ),
              ),
      ),
    );
  }
}

class _DatabaseRow extends StatelessWidget {
  const _DatabaseRow({required this.db});

  final DatabaseHealthSnapshot db;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  db.name,
                  style: const TextStyle(
                    color: JackPalette.text,
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Stato: ${db.status} · Schema v${db.schemaVersion ?? '?'}',
                  style: TextStyle(
                    color: JackPalette.muted,
                    fontSize: 12,
                  ),
                ),
                if (db.integrity != null)
                  Text(
                    'Integrità: ${db.integrity}',
                    style: TextStyle(
                      color: db.integrity == true
                          ? JackPalette.green
                          : JackPalette.red,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
              ],
            ),
          ),
          StatusDot(
            color: db.status == 'ok'
                ? JackPalette.green
                : JackPalette.red,
            size: 6,
          ),
        ],
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.error_outline, color: JackPalette.red, size: 48),
          const SizedBox(height: 12),
          Text(
            message,
            style: TextStyle(color: JackPalette.text, fontSize: 14),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh, size: 16),
            label: const Text('Riprova'),
          ),
        ],
      ),
    );
  }
}
