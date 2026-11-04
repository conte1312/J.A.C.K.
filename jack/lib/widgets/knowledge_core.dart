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
          child: RepaintBoundary(
            key: const ValueKey('knowledge-core-render-boundary'),
            child: AnimatedBuilder(
              animation: _motion,
              builder: (context, child) {
                final phase = _motion.value * math.pi * 2;
                return CustomPaint(
                  key: const ValueKey('knowledge-core-painter'),
                  painter: _KnowledgeCorePainter(
                    rotation: phase + _dragRotation,
                    phase: phase,
                    zoom: _zoom,
                  ),
                  child: child,
                );
              },
              child: const SizedBox.expand(),
            ),
          ),
        ),
      ),
    );
  }
}

class _KnowledgeCorePainter extends CustomPainter {
  const _KnowledgeCorePainter({
    required this.rotation,
    required this.phase,
    required this.zoom,
  });

  final double rotation;
  final double phase;
  final double zoom;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final breath = math.sin(phase * 9 - math.pi / 2);
    final slowBreath = math.sin(phase * 4 + 0.8);
    final pulse = 1 + breath * 0.018 + slowBreath * 0.004;
    final radius = math.min(size.width, size.height) * 0.275 * zoom * pulse;
    final sphere = Rect.fromCircle(center: center, radius: radius);
    final spherePath = _organicSpherePath(center, radius, phase);

    final atmosphere = Paint()
      ..shader =
          RadialGradient(
            colors: [
              JackPalette.amber.withValues(alpha: 0.11),
              const Color(0xFF5F361D).withValues(alpha: 0.12),
              JackPalette.canvas.withValues(alpha: 0),
            ],
            stops: const [0.0, 0.46, 1.0],
          ).createShader(
            Rect.fromCircle(
              center: center,
              radius: radius * (1.75 + breath * 0.025),
            ),
          );
    canvas.drawCircle(center, radius * (1.75 + breath * 0.025), atmosphere);

    _drawOrbit(
      canvas,
      center,
      radius * 1.57,
      radius * 1.98,
      -0.31 + rotation * 0.2,
      JackPalette.amber,
      0.8,
    );
    _drawOrbit(
      canvas,
      center,
      radius * 1.2,
      radius * 2.35,
      0.39 - rotation * 0.14,
      JackPalette.amberSoft,
      0.7,
    );
    _drawOrbit(
      canvas,
      center,
      radius * 1.92,
      radius * 0.92,
      -0.69 + rotation * 0.1,
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
    canvas.drawPath(spherePath, spherePaint);

    final rim = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 0.8
      ..color = JackPalette.amberSoft.withValues(alpha: 0.25);
    canvas.drawPath(spherePath, rim);

    _drawOrbit(
      canvas,
      center,
      radius * 0.93,
      radius * 0.99,
      -0.37 + rotation * 0.26,
      JackPalette.amberSoft,
      0.65,
    );
    _drawOrbit(
      canvas,
      center,
      radius * 0.77,
      radius * 1.01,
      0.82 - rotation * 0.19,
      JackPalette.amberSoft,
      0.55,
    );

    final axisPaint = Paint()
      ..color = JackPalette.amber.withValues(alpha: 0.54)
      ..strokeWidth = 1;
    final axisAngle = -0.31 + rotation * 0.12;
    final axisStart = _rotate(Offset(-radius * 1.2, radius * 0.4), axisAngle);
    final axisEnd = _rotate(Offset(radius * 1.2, -radius * 0.4), axisAngle);
    canvas.drawLine(center + axisStart, center + axisEnd, axisPaint);

    _drawParticles(canvas, center, radius, phase);
    _drawNodes(canvas, center, radius, phase);
  }

  Path _organicSpherePath(Offset center, double radius, double phase) {
    const segments = 120;
    final path = Path();

    for (var i = 0; i < segments; i++) {
      final angle = i / segments * math.pi * 2;
      final deformation =
          math.sin(angle * 3 + phase * 2.3) * 0.011 +
          math.sin(angle * 5 - phase * 3.1 + 0.7) * 0.006 +
          math.sin(angle * 2 + phase * 1.8) * 0.004;
      final deformedRadius = radius * (1 + deformation);
      final point =
          center +
          Offset(
            math.cos(angle) * deformedRadius,
            math.sin(angle) * deformedRadius,
          );

      if (i == 0) {
        path.moveTo(point.dx, point.dy);
      } else {
        path.lineTo(point.dx, point.dy);
      }
    }

    return path..close();
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

  void _drawParticles(
    Canvas canvas,
    Offset center,
    double radius,
    double phase,
  ) {
    for (var i = 0; i < 54; i++) {
      final particleAngle = i * 2.399 + rotation * 0.58;
      final drift = math.sin(phase * 5.6 + i * 1.4) * 0.014;
      final spread = 1.02 + ((i * 29) % 100) / 100 * 0.75 + drift;
      final position =
          center +
          Offset(
            math.cos(particleAngle) * radius * spread,
            math.sin(particleAngle) * radius * spread * 1.38,
          );
      final shimmer = 0.76 + 0.24 * (math.sin(phase * 7 + i * 1.9) + 1) / 2;
      final opacity = (0.1 + ((i * 13) % 7) / 28) * shimmer;
      canvas.drawCircle(
        position,
        i % 9 == 0 ? 1.45 : 0.9,
        Paint()..color = JackPalette.amber.withValues(alpha: opacity),
      );
    }
  }

  void _drawNodes(Canvas canvas, Offset center, double radius, double phase) {
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

    final rotationAngle = rotation * 0.26;
    for (var index = 0; index < nodes.length; index++) {
      final node = nodes[index];
      final unrotated = Offset(node.x * radius, node.y * radius);
      final drift = Offset(
        math.sin(phase * 6.3 + index * 1.7) * radius * 0.009,
        math.cos(phase * 5.7 + index * 1.3) * radius * 0.008,
      );
      final position = center + _rotate(unrotated, rotationAngle) + drift;
      final pulse = (math.sin(phase * 9 + index * 0.85) + 1) / 2;
      final glowRadius = node.size * 3.6 * (0.94 + pulse * 0.12);
      canvas.drawCircle(
        position,
        glowRadius,
        Paint()
          ..shader = RadialGradient(
            colors: [
              node.color.withValues(alpha: 0.3 + pulse * 0.06),
              node.color.withValues(alpha: 0),
            ],
          ).createShader(Rect.fromCircle(center: position, radius: glowRadius)),
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
    return oldDelegate.rotation != rotation ||
        oldDelegate.phase != phase ||
        oldDelegate.zoom != zoom;
  }
}

class _CoreNode {
  const _CoreNode(this.x, this.y, this.color, this.size);

  final double x;
  final double y;
  final Color color;
  final double size;
}
