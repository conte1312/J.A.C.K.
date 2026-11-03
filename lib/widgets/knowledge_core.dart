import 'dart:math' as math;

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';

import '../theme/jack_theme.dart';

class KnowledgeCore extends StatefulWidget {
  const KnowledgeCore({super.key});

  @override
  State<KnowledgeCore> createState() => _KnowledgeCoreState();
}

class _KnowledgeCoreState extends State<KnowledgeCore>
    with SingleTickerProviderStateMixin {
  late final AnimationController _motion;
  double _dragRotation = 0;
  double _zoom = 1;

  @override
  void initState() {
    super.initState();
    _motion = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 72),
    )..repeat();
  }

  @override
  void dispose() {
    _motion.dispose();
    super.dispose();
  }

  void _handlePointerSignal(PointerSignalEvent event) {
    if (event is PointerScrollEvent) {
      setState(() {
        _zoom = (_zoom - event.scrollDelta.dy * 0.0007).clamp(0.82, 1.24);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Knowledge Core dimostrativo con orbite e nodi',
      child: Listener(
        onPointerSignal: _handlePointerSignal,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onPanUpdate: (details) {
            setState(() {
              _dragRotation += details.delta.dx * 0.008;
            });
          },
          child: AnimatedBuilder(
            animation: _motion,
            builder: (context, child) {
              return CustomPaint(
                painter: _KnowledgeCorePainter(
                  rotation: _motion.value * math.pi * 2 + _dragRotation,
                  zoom: _zoom,
                ),
                child: child,
              );
            },
            child: const SizedBox.expand(),
          ),
        ),
      ),
    );
  }
}

class _KnowledgeCorePainter extends CustomPainter {
  const _KnowledgeCorePainter({required this.rotation, required this.zoom});

  final double rotation;
  final double zoom;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) * 0.275 * zoom;
    final sphere = Rect.fromCircle(center: center, radius: radius);

    final atmosphere = Paint()
      ..shader = RadialGradient(
        colors: [
          JackPalette.amber.withValues(alpha: 0.11),
          const Color(0xFF5F361D).withValues(alpha: 0.12),
          JackPalette.canvas.withValues(alpha: 0),
        ],
        stops: const [0.0, 0.46, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: radius * 1.75));
    canvas.drawCircle(center, radius * 1.75, atmosphere);

    _drawOrbit(
      canvas,
      center,
      radius * 1.57,
      radius * 1.98,
      -0.31 + rotation * 0.035,
      JackPalette.amber,
      0.8,
    );
    _drawOrbit(
      canvas,
      center,
      radius * 1.2,
      radius * 2.35,
      0.39 - rotation * 0.025,
      JackPalette.amberSoft,
      0.7,
    );
    _drawOrbit(
      canvas,
      center,
      radius * 1.92,
      radius * 0.92,
      -0.69 + rotation * 0.018,
      JackPalette.amber,
      0.65,
    );

    final spherePaint = Paint()
      ..shader = RadialGradient(
        center: const Alignment(-0.28, -0.3),
        radius: 1.15,
        colors: [
          const Color(0xFF56331F).withValues(alpha: 0.58),
          const Color(0xFF302219).withValues(alpha: 0.52),
          const Color(0xFF171819).withValues(alpha: 0.84),
        ],
        stops: const [0.0, 0.48, 1.0],
      ).createShader(sphere);
    canvas.drawCircle(center, radius, spherePaint);

    final rim = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.8
      ..color = JackPalette.amberSoft.withValues(alpha: 0.25);
    canvas.drawCircle(center, radius, rim);

    _drawOrbit(
      canvas,
      center,
      radius * 0.93,
      radius * 0.99,
      -0.37 + rotation * 0.1,
      JackPalette.amberSoft,
      0.65,
    );
    _drawOrbit(
      canvas,
      center,
      radius * 0.77,
      radius * 1.01,
      0.82 - rotation * 0.08,
      JackPalette.amberSoft,
      0.55,
    );

    final axisPaint = Paint()
      ..color = JackPalette.amber.withValues(alpha: 0.54)
      ..strokeWidth = 1;
    final axisAngle = -0.31 + rotation * 0.025;
    final axisStart = _rotate(Offset(-radius * 1.2, radius * 0.4), axisAngle);
    final axisEnd = _rotate(Offset(radius * 1.2, -radius * 0.4), axisAngle);
    canvas.drawLine(center + axisStart, center + axisEnd, axisPaint);

    _drawParticles(canvas, center, radius);
    _drawNodes(canvas, center, radius);
  }

  void _drawOrbit(
    Canvas canvas,
    Offset center,
    double widthRadius,
    double heightRadius,
    double angle,
    Color color,
    double strokeWidth,
  ) {
    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(angle);
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset.zero,
        width: widthRadius * 2,
        height: heightRadius * 2,
      ),
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth
        ..color = color.withValues(alpha: 0.24),
    );
    canvas.restore();
  }

  void _drawParticles(Canvas canvas, Offset center, double radius) {
    for (var i = 0; i < 54; i++) {
      final phase = i * 2.399 + rotation * 0.08;
      final spread = 1.02 + ((i * 29) % 100) / 100 * 0.75;
      final position =
          center +
          Offset(
            math.cos(phase) * radius * spread,
            math.sin(phase) * radius * spread * 1.38,
          );
      final opacity = 0.1 + ((i * 13) % 7) / 28;
      canvas.drawCircle(
        position,
        i % 9 == 0 ? 1.45 : 0.9,
        Paint()..color = JackPalette.amber.withValues(alpha: opacity),
      );
    }
  }

  void _drawNodes(Canvas canvas, Offset center, double radius) {
    const nodes = <_CoreNode>[
      _CoreNode(-0.78, 0.02, JackPalette.cyan, 3.7),
      _CoreNode(0.43, -0.62, Color(0xFFFFE8C6), 4.2),
      _CoreNode(0.59, -0.69, JackPalette.amber, 3.8),
      _CoreNode(0.76, -0.77, JackPalette.cyan, 3.5),
      _CoreNode(0.87, -0.43, Color(0xFFD7E6F4), 3.1),
      _CoreNode(0.69, -0.28, Color(0xFFE9DCCB), 3.1),
      _CoreNode(0.0, 0.69, JackPalette.amber, 2.5),
      _CoreNode(0.52, 1.13, JackPalette.cyan, 3.1),
      _CoreNode(0.31, 0.92, Color(0xFFFFE6BD), 2.9),
      _CoreNode(-0.12, 0.37, Color(0xFFFFE5B7), 2.0),
      _CoreNode(0.16, -0.82, Color(0xFFD9E5F2), 2.6),
    ];

    final rotationAngle = rotation * 0.12;
    for (final node in nodes) {
      final unrotated = Offset(node.x * radius, node.y * radius);
      final position = center + _rotate(unrotated, rotationAngle);
      canvas.drawCircle(
        position,
        node.size * 3.6,
        Paint()
          ..shader =
              RadialGradient(
                colors: [
                  node.color.withValues(alpha: 0.34),
                  node.color.withValues(alpha: 0),
                ],
              ).createShader(
                Rect.fromCircle(center: position, radius: node.size * 3.6),
              ),
      );
      canvas.drawCircle(
        position,
        node.size,
        Paint()..color = node.color.withValues(alpha: 0.95),
      );
    }
  }

  Offset _rotate(Offset point, double angle) {
    final cosine = math.cos(angle);
    final sine = math.sin(angle);
    return Offset(
      point.dx * cosine - point.dy * sine,
      point.dx * sine + point.dy * cosine,
    );
  }

  @override
  bool shouldRepaint(covariant _KnowledgeCorePainter oldDelegate) {
    return oldDelegate.rotation != rotation || oldDelegate.zoom != zoom;
  }
}

class _CoreNode {
  const _CoreNode(this.x, this.y, this.color, this.size);

  final double x;
  final double y;
  final Color color;
  final double size;
}
