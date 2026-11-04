import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../models/jack_section.dart';
import '../services/backend_status_service.dart';
import '../theme/jack_theme.dart';
import 'backend_status_indicator.dart';
import 'jack_primitives.dart';
import 'jack_core/jack_core_demo_data.dart';
import 'jack_core/jack_core_graph.dart';
import 'jack_core/jack_core_preview_panel.dart';

class RightRail extends StatelessWidget {
  const RightRail({
    required this.backendState,
    required this.backendVersion,
    required this.onSectionSelected,
    this.selectedCoreNode,
    this.onClearCoreNodeSelection,
    this.showCorePreview = false,
    super.key,
  });

  final BackendConnectionState backendState;
  final String? backendVersion;
  final ValueChanged<JackSection> onSectionSelected;
  final ValueListenable<JackCoreNode?>? selectedCoreNode;
  final VoidCallback? onClearCoreNodeSelection;
  final bool showCorePreview;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.only(bottom: 4),
      child: Column(
        children: [
          if (showCorePreview && selectedCoreNode != null) ...[
            ValueListenableBuilder<JackCoreNode?>(
              valueListenable: selectedCoreNode!,
              builder: (context, node, child) => JackCorePreviewPanel(
                graph: jackCoreDemoGraph,
                node: node,
                onOpenInGraph: () => onSectionSelected(JackSection.exploration),
                onClearSelection: onClearCoreNodeSelection,
              ),
            ),
            const SizedBox(height: 12),
          ],
          _MemoryCard(onExplore: () => onSectionSelected(JackSection.memory)),
          const SizedBox(height: 12),
          _ActivitiesCard(
            onOpen: () => onSectionSelected(JackSection.planning),
          ),
          const SizedBox(height: 12),
          _ModelsPanel(onOpen: () => onSectionSelected(JackSection.modules)),
          const SizedBox(height: 12),
          _SystemStatusCard(
            backendState: backendState,
            backendVersion: backendVersion,
          ),
        ],
      ),
    );
  }
}

class _MemoryCard extends StatelessWidget {
  const _MemoryCard({required this.onExplore});

  final VoidCallback onExplore;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onExplore,
      borderRadius: BorderRadius.circular(20),
      child: JackPanel(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Expanded(child: SectionEyebrow('Memoria locale')),
                TextButton(
                  onPressed: onExplore,
                  style: TextButton.styleFrom(
                    foregroundColor: JackPalette.muted,
                    padding: EdgeInsets.zero,
                    minimumSize: const Size(0, 24),
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    textStyle: const TextStyle(fontSize: 9),
                  ),
                  child: const Text('Apri ↗'),
                ),
              ],
            ),
            const SizedBox(height: 7),
            const Text(
              'Ricordi aggiunti da te e salvati su questo Mac.',
              style: TextStyle(
                color: JackPalette.muted,
                fontSize: 10,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 8),
            const Row(
              children: [
                StatusDot(color: JackPalette.cyan, size: 5),
                SizedBox(width: 7),
                Text(
                  'SQLite locale · nessun cloud',
                  style: TextStyle(color: JackPalette.dim, fontSize: 8),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ActivitiesCard extends StatelessWidget {
  const _ActivitiesCard({required this.onOpen});

  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onOpen,
      borderRadius: BorderRadius.circular(20),
      child: JackPanel(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SectionEyebrow('Attività'),
            const SizedBox(height: 15),
            const Text(
              'Nessuna attività pianificata nella demo.',
              style: TextStyle(
                color: JackPalette.muted,
                fontSize: 10,
                height: 1.55,
              ),
            ),
            const SizedBox(height: 3),
            const Text(
              'Apri Pianificazione per la relativa anteprima.',
              style: TextStyle(
                color: JackPalette.dim,
                fontSize: 9,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ModelsPanel extends StatelessWidget {
  const _ModelsPanel({required this.onOpen});

  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(2, 0, 2, 0),
      child: Column(
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(4, 2, 4, 8),
            child: Row(
              children: [
                Expanded(child: SectionEyebrow('Provider / modelli')),
                DemoBadge(label: 'NON COLLEGATI'),
              ],
            ),
          ),
          _ModelRow(
            name: 'GPT-4.1 · esempio',
            provider: 'OpenAI · demo',
            onTap: onOpen,
          ),
          _ModelRow(
            name: 'Claude Sonnet · esempio',
            provider: 'Anthropic · demo',
            onTap: onOpen,
          ),
          _ModelRow(
            name: 'Gemini Flash · esempio',
            provider: 'Google · demo',
            onTap: onOpen,
          ),
          _ModelRow(
            name: 'Llama locale · esempio',
            provider: 'Locale · demo',
            onTap: onOpen,
          ),
          const SizedBox(height: 4),
          SizedBox(
            width: double.infinity,
            height: 34,
            child: OutlinedButton.icon(
              key: const ValueKey('open-ai-hub-from-rail'),
              onPressed: onOpen,
              icon: const Icon(Icons.tune_rounded, size: 13),
              label: const Text('Gestisci in AI Hub'),
              style: OutlinedButton.styleFrom(
                foregroundColor: JackPalette.muted,
                side: BorderSide(
                  color: JackPalette.border.withValues(alpha: 0.85),
                ),
                textStyle: const TextStyle(fontSize: 9),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
            ),
          ),
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: Row(
              children: [
                StatusDot(color: JackPalette.dim, size: 4),
                SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Routing simulato · nessuna richiesta inviata',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(color: JackPalette.dim, fontSize: 8),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ModelRow extends StatelessWidget {
  const _ModelRow({
    required this.name,
    required this.provider,
    required this.onTap,
  });

  final String name;
  final String provider;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        height: 41,
        padding: const EdgeInsets.symmetric(horizontal: 8),
        decoration: BoxDecoration(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          children: [
            const StatusDot(color: JackPalette.amberSoft, size: 5),
            const SizedBox(width: 9),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name,
                    style: TextStyle(color: JackPalette.muted, fontSize: 10),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    provider,
                    style: const TextStyle(color: JackPalette.dim, fontSize: 8),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
              decoration: BoxDecoration(
                border: Border.all(color: JackPalette.border),
                borderRadius: BorderRadius.circular(20),
              ),
              child: const Text(
                'DEMO',
                style: TextStyle(
                  color: JackPalette.dim,
                  fontSize: 7,
                  letterSpacing: 0.6,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SystemStatusCard extends StatelessWidget {
  const _SystemStatusCard({
    required this.backendState,
    required this.backendVersion,
  });

  final BackendConnectionState backendState;
  final String? backendVersion;

  @override
  Widget build(BuildContext context) {
    final backendValue = backendStatusShortText(backendState);
    final backendColor = backendStatusColor(backendState);
    final ringLabel = switch (backendState) {
      BackendConnectionState.loading => '…',
      BackendConnectionState.connected => 'API',
      BackendConnectionState.disconnected => 'OFF',
    };

    return JackPanel(
      padding: const EdgeInsets.fromLTRB(16, 14, 14, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionEyebrow('Stato del sistema'),
          const SizedBox(height: 12),
          Row(
            children: [
              SizedBox(
                width: 62,
                height: 62,
                child: CustomPaint(
                  painter: _DemoRingPainter(color: backendColor),
                  child: Center(
                    child: Text(
                      ringLabel,
                      style: const TextStyle(
                        color: JackPalette.text,
                        fontSize: 8,
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 13),
              Expanded(
                child: Column(
                  children: [
                    const _SystemRow(label: 'J.A.C.K.', value: 'UI demo'),
                    const _SystemRow(label: 'Mac', value: 'Locale'),
                    _SystemRow(
                      label: 'Backend',
                      value: backendValue,
                      dotColor: backendColor,
                      detail: backendVersion == null
                          ? null
                          : 'v$backendVersion',
                    ),
                    const _SystemRow(label: 'Moduli', value: '0 collegati'),
                    const _SystemRow(label: 'Provider', value: '0 collegati'),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SystemRow extends StatelessWidget {
  const _SystemRow({
    required this.label,
    required this.value,
    this.dotColor = JackPalette.amber,
    this.detail,
  });

  final String label;
  final String value;
  final Color dotColor;
  final String? detail;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          StatusDot(color: dotColor, size: 4),
          const SizedBox(width: 7),
          SizedBox(
            width: 56,
            child: Text(
              label,
              style: const TextStyle(color: JackPalette.dim, fontSize: 9),
            ),
          ),
          Expanded(
            child: Text(
              detail == null || detail!.isEmpty ? value : '$value $detail',
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: JackPalette.muted, fontSize: 9),
            ),
          ),
        ],
      ),
    );
  }
}

class _DemoRingPainter extends CustomPainter {
  const _DemoRingPainter({required this.color});

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final rect = Rect.fromCircle(center: center, radius: size.shortestSide / 2);
    canvas.drawArc(
      rect,
      -1.7,
      mathPi * 1.55,
      false,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.5
        ..strokeCap = StrokeCap.round
        ..color = color.withValues(alpha: 0.82),
    );
    canvas.drawCircle(
      center,
      size.shortestSide / 2 - 1.5,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1
        ..color = JackPalette.border,
    );
  }

  @override
  bool shouldRepaint(covariant _DemoRingPainter oldDelegate) =>
      oldDelegate.color != color;
}

const mathPi = 3.141592653589793;
