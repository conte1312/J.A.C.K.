import 'package:flutter/material.dart';

import '../models/jack_section.dart';
import '../theme/jack_theme.dart';
import 'jack_primitives.dart';

class RightRail extends StatelessWidget {
  const RightRail({required this.onSectionSelected, super.key});

  final ValueChanged<JackSection> onSectionSelected;

  void _showDemoInfo(BuildContext context, String title) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: JackPalette.panel,
        title: Text(title, style: const TextStyle(color: JackPalette.text)),
        content: const Text(
          'Elemento dimostrativo. In questa milestone non è collegato alcun provider o servizio locale.',
          style: TextStyle(color: JackPalette.muted, height: 1.5),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Chiudi'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.only(bottom: 4),
      child: Column(
        children: [
          _MemoryCard(onExplore: () => onSectionSelected(JackSection.memory)),
          const SizedBox(height: 12),
          _ActivitiesCard(
            onOpen: () => onSectionSelected(JackSection.planning),
          ),
          const SizedBox(height: 12),
          _ModelsPanel(onModelTap: (model) => _showDemoInfo(context, model)),
          const SizedBox(height: 12),
          const _SystemStatusCard(),
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
    return JackPanel(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 13),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(child: SectionEyebrow('Memoria')),
              TextButton(
                onPressed: onExplore,
                style: TextButton.styleFrom(
                  foregroundColor: JackPalette.muted,
                  padding: EdgeInsets.zero,
                  minimumSize: const Size(0, 24),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  textStyle: const TextStyle(fontSize: 9),
                ),
                child: const Text('Esplora ↗'),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              const Text(
                '12',
                style: TextStyle(
                  color: JackPalette.text,
                  fontSize: 23,
                  height: 1,
                  fontWeight: FontWeight.w300,
                ),
              ),
              const SizedBox(width: 8),
              const Padding(
                padding: EdgeInsets.only(bottom: 2),
                child: Text(
                  'nodi di esempio',
                  style: TextStyle(color: JackPalette.dim, fontSize: 10),
                ),
              ),
              const Spacer(),
              const DemoBadge(),
            ],
          ),
          const SizedBox(height: 13),
          const _MemoryCategory(
            label: 'Lavoro',
            count: '2',
            color: JackPalette.amber,
          ),
          const _MemoryCategory(
            label: 'Persone',
            count: '2',
            color: JackPalette.cyan,
          ),
          const _MemoryCategory(
            label: 'Tecnica',
            count: '2',
            color: JackPalette.blue,
          ),
          const _MemoryCategory(
            label: 'Eventi',
            count: '2',
            color: JackPalette.lavender,
          ),
          const Padding(
            padding: EdgeInsets.only(top: 7),
            child: Text(
              'Ultima scrittura · dati dimostrativi',
              style: TextStyle(color: JackPalette.dim, fontSize: 8),
            ),
          ),
        ],
      ),
    );
  }
}

class _MemoryCategory extends StatelessWidget {
  const _MemoryCategory({
    required this.label,
    required this.count,
    required this.color,
  });

  final String label;
  final String count;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          StatusDot(color: color, size: 5),
          const SizedBox(width: 8),
          SizedBox(
            width: 57,
            child: Text(
              label,
              style: const TextStyle(color: JackPalette.muted, fontSize: 10),
            ),
          ),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: 0.92,
                minHeight: 3,
                backgroundColor: JackPalette.border,
                color: color,
              ),
            ),
          ),
          SizedBox(
            width: 20,
            child: Text(
              count,
              textAlign: TextAlign.end,
              style: const TextStyle(color: JackPalette.dim, fontSize: 9),
            ),
          ),
        ],
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
  const _ModelsPanel({required this.onModelTap});

  final ValueChanged<String> onModelTap;

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
            name: 'Base 1',
            provider: 'Base44 · demo',
            onTap: () => onModelTap('Base 1 · Base44'),
            primary: true,
          ),
          _ModelRow(
            name: 'Gemini 3 Flash',
            provider: 'Google · demo',
            onTap: () => onModelTap('Gemini 3 Flash'),
          ),
          _ModelRow(
            name: 'Claude Sonnet 4.6',
            provider: 'Anthropic · demo',
            onTap: () => onModelTap('Claude Sonnet 4.6'),
          ),
          const SizedBox(height: 4),
          SizedBox(
            width: double.infinity,
            height: 34,
            child: OutlinedButton.icon(
              key: const ValueKey('add-model'),
              onPressed: () => onModelTap('Aggiungi modello'),
              icon: const Icon(Icons.add_rounded, size: 13),
              label: const Text('Aggiungi modello'),
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
                Text(
                  'Routing automatico non attivo',
                  style: TextStyle(color: JackPalette.dim, fontSize: 8),
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
    this.primary = false,
  });

  final String name;
  final String provider;
  final VoidCallback onTap;
  final bool primary;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        height: 41,
        padding: const EdgeInsets.symmetric(horizontal: 8),
        decoration: BoxDecoration(
          color: primary
              ? JackPalette.amber.withValues(alpha: 0.07)
              : Colors.transparent,
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
                    style: TextStyle(
                      color: primary ? JackPalette.text : JackPalette.muted,
                      fontSize: 10,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    provider,
                    style: const TextStyle(color: JackPalette.dim, fontSize: 8),
                  ),
                ],
              ),
            ),
            if (primary)
              const DemoBadge(label: 'ESEMPIO')
            else
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
  const _SystemStatusCard();

  @override
  Widget build(BuildContext context) {
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
                  painter: _DemoRingPainter(),
                  child: const Center(
                    child: Text(
                      'DEMO',
                      style: TextStyle(color: JackPalette.text, fontSize: 8),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 13),
              const Expanded(
                child: Column(
                  children: [
                    _SystemRow(label: 'J.A.C.K.', value: 'UI dimostrativa'),
                    _SystemRow(label: 'Mac', value: 'Locale'),
                    _SystemRow(label: 'Moduli', value: '0/4 collegati'),
                    _SystemRow(label: 'Modelli', value: '3 esempi'),
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
  const _SystemRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          const StatusDot(color: JackPalette.amber, size: 4),
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
              value,
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
        ..color = JackPalette.green.withValues(alpha: 0.82),
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
  bool shouldRepaint(covariant _DemoRingPainter oldDelegate) => false;
}

const mathPi = 3.141592653589793;
