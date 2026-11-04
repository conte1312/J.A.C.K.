import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'jack_core_graph.dart';
import 'jack_core_motion.dart';
import 'jack_core_palette.dart';
import 'jack_core_projection.dart';
import 'jack_core_state.dart';
import 'jack_core_visual_mapping.dart';

class JackCorePainter extends CustomPainter {
  JackCorePainter({
    required this.graph,
    required this.state,
    required this.profileFrom,
    required this.profileTo,
    required this.toneFrom,
    required this.toneTo,
    required this.transition,
    required this.phase,
    required this.rotationX,
    required this.rotationY,
    required this.zoom,
    required this.intensity,
    required this.reducedMotion,
    required this.selectedNodeId,
    required this.highlightedNodeId,
    required this.orbits,
    required this.baseScale,
  }) : super(repaint: Listenable.merge([phase, transition]));

  final JackCoreGraph graph;
  final JackCognitiveState state;
  final JackCoreMotionProfile profileFrom;
  final JackCoreMotionProfile profileTo;
  final Color toneFrom;
  final Color toneTo;
  final Animation<double> transition;
  final Animation<double> phase;
  final double rotationX;
  final double rotationY;
  final double zoom;
  final JackCoreIntensity intensity;
  final bool reducedMotion;
  final String? selectedNodeId;
  final String? highlightedNodeId;
  final List<JackCoreOrbit> orbits;
  final double baseScale;

  JackCoreMotionProfile get currentProfile => JackCoreMotionProfile.lerp(
    profileFrom.scaled(intensity),
    profileTo.scaled(intensity),
    reducedMotion ? 1 : transition.value,
  );

  Color get currentTone =>
      Color.lerp(toneFrom, toneTo, reducedMotion ? 1 : transition.value)!;

  double get currentPhase => reducedMotion ? 0 : phase.value * math.pi * 2;

  JackCoreProjectionResult project(Size size) {
    final profile = currentProfile;
    final breathing =
        1 + math.sin(currentPhase * 0.82) * profile.breathe * 0.025;
    return JackCoreProjection.projectGraph(
      graph: graph,
      size: size,
      rotationX: rotationX,
      rotationY: rotationY + currentPhase * profile.spin * 8,
      zoom: zoom,
      baseScale: baseScale * breathing,
    );
  }

  @override
  void paint(Canvas canvas, Size size) {
    final profile = currentProfile;
    final phaseValue = currentPhase;
    final tone = currentTone;
    final projection = project(size);
    final center = projection.center;
    final scale = projection.unitScale;
    final jitter = profile.jitter == 0
        ? Offset.zero
        : Offset(
            math.sin(phaseValue * 7.3) * profile.jitter * 1.2,
            math.cos(phaseValue * 5.1) * profile.jitter * 0.8,
          );
    final localNodes = <String, JackCoreProjectedNode>{
      for (final node in projection.nodes) node.node.id: node,
    };
    final screenPositions = <String, Offset>{
      for (final node in projection.nodes)
        node.node.id: _breathePosition(
          node.position + jitter,
          center,
          phaseValue,
          profile,
        ),
    };
    final clusteredPositions = _clusterNodes(
      projection.nodes,
      screenPositions,
      profile.cluster,
    );

    _drawAtmosphere(canvas, center + jitter, scale, tone, profile);
    _drawShells(canvas, center + jitter, scale, phaseValue, profile);
    _drawOrbits(canvas, size, projection, phaseValue, profile, tone, jitter);
    _drawEdges(
      canvas,
      center + jitter,
      graph.edges,
      localNodes,
      clusteredPositions,
      profile,
      tone,
    );
    _drawParticles(canvas, center + jitter, scale, phaseValue, profile, tone);
    _drawNodes(
      canvas,
      projection.nodes,
      clusteredPositions,
      phaseValue,
      profile,
    );
    _drawScan(canvas, center + jitter, scale, phaseValue, profile, tone);
  }

  Offset _breathePosition(
    Offset position,
    Offset center,
    double phaseValue,
    JackCoreMotionProfile profile,
  ) {
    final breath = 1 + math.sin(phaseValue * 0.82) * profile.breathe * 0.025;
    return center + (position - center) * breath;
  }

  Map<String, Offset> _clusterNodes(
    List<JackCoreProjectedNode> nodes,
    Map<String, Offset> positions,
    double cluster,
  ) {
    if (cluster <= 0 || graph.edges.isEmpty) return positions;
    final neighbours = <String, List<String>>{};
    for (final edge in graph.edges) {
      neighbours.putIfAbsent(edge.fromId, () => []).add(edge.toId);
      neighbours.putIfAbsent(edge.toId, () => []).add(edge.fromId);
    }
    final clustered = <String, Offset>{};
    for (final projected in nodes) {
      final position = positions[projected.node.id]!;
      final linked = neighbours[projected.node.id];
      if (linked == null || linked.isEmpty) {
        clustered[projected.node.id] = position;
        continue;
      }
      var linkedCenter = Offset.zero;
      for (final id in linked) {
        linkedCenter += positions[id]!;
      }
      linkedCenter = linkedCenter / linked.length.toDouble();
      clustered[projected.node.id] = Offset.lerp(
        position,
        linkedCenter,
        cluster * 0.045,
      )!;
    }
    return clustered;
  }

  void _drawAtmosphere(
    Canvas canvas,
    Offset center,
    double scale,
    Color tone,
    JackCoreMotionProfile profile,
  ) {
    final radius = scale * 1.48;
    final strength = (0.018 + profile.glow * 0.075).clamp(0.0, 0.12);
    final paint = Paint()
      ..shader = RadialGradient(
        colors: [
          tone.withValues(alpha: strength),
          JackCorePalette.amberDeep.withValues(alpha: strength * 0.48),
          JackCorePalette.abyss.withValues(alpha: 0.018),
          Colors.transparent,
        ],
        stops: const [0.0, 0.38, 0.72, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: radius));
    canvas.drawCircle(center, radius, paint);
  }

  void _drawShells(
    Canvas canvas,
    Offset center,
    double scale,
    double phaseValue,
    JackCoreMotionProfile profile,
  ) {
    final breath = 1 + math.sin(phaseValue * 0.82) * profile.breathe * 0.025;
    final surfaceRadius = scale * breath;
    final interiorRadius =
        surfaceRadius * JackCoreProjection.interiorShellRadius;
    final shellFill = Paint()
      ..shader = RadialGradient(
        center: const Alignment(-0.28, -0.3),
        colors: [
          JackCorePalette.amberSoft.withValues(
            alpha: 0.055 + profile.glow * 0.025,
          ),
          JackCorePalette.amberDeep.withValues(alpha: 0.032),
          JackCorePalette.abyss.withValues(alpha: 0.045),
          Colors.transparent,
        ],
        stops: const [0.0, 0.42, 0.82, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: surfaceRadius));
    canvas.drawCircle(center, surfaceRadius, shellFill);

    canvas.drawCircle(
      center,
      surfaceRadius,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.8
        ..color = JackCorePalette.amberSoft.withValues(alpha: 0.22),
    );
    canvas.drawCircle(
      center,
      interiorRadius,
      Paint()
        ..style = PaintingStyle.fill
        ..shader = RadialGradient(
          colors: [
            JackCorePalette.glacier.withValues(alpha: 0.026),
            JackCorePalette.abyss.withValues(alpha: 0.028),
            Colors.transparent,
          ],
        ).createShader(Rect.fromCircle(center: center, radius: interiorRadius)),
    );
    canvas.drawCircle(
      center,
      interiorRadius,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 0.65
        ..color = JackCorePalette.glacier.withValues(alpha: 0.13),
    );
  }

  void _drawOrbits(
    Canvas canvas,
    Size size,
    JackCoreProjectionResult projection,
    double phaseValue,
    JackCoreMotionProfile profile,
    Color tone,
    Offset jitter,
  ) {
    const segments = 64;
    for (var orbitIndex = 0; orbitIndex < orbits.length; orbitIndex++) {
      final orbit = orbits[orbitIndex];
      final pathPoints = <JackCoreProjectedPoint>[];
      final orbitPhase = phaseValue * profile.spin * orbit.speed * 2.2;
      for (var index = 0; index <= segments; index++) {
        final angle = index / segments * math.pi * 2 + orbitPhase;
        final point = _tiltOrbitPoint(
          JackCorePoint3(
            math.cos(angle) * orbit.radius,
            math.sin(angle) * orbit.radius,
            0,
          ),
          orbit.tiltX,
          orbit.tiltY,
        );
        final projected = JackCoreProjection.projectPointDetailed(
          point: point,
          size: size,
          rotationX: rotationX,
          rotationY: rotationY + phaseValue * profile.spin * 8,
          unitScale: projection.unitScale,
        );
        pathPoints.add(
          JackCoreProjectedPoint(
            position: projected.position + jitter,
            depth: projected.depth,
            perspectiveScale: projected.perspectiveScale,
          ),
        );
      }
      for (var index = 0; index < segments; index++) {
        final start = pathPoints[index];
        final end = pathPoints[index + 1];
        final depthFactor = 0.44 + ((start.depth + end.depth) * 0.5 + 1) * 0.25;
        final alpha =
            orbit.opacity * (0.68 + profile.glow * 0.32) * depthFactor;
        canvas.drawLine(
          start.position,
          end.position,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = orbitIndex == 3 ? 0.65 : 0.8
            ..color = (orbitIndex.isEven ? tone : JackCorePalette.amberSoft)
                .withValues(alpha: alpha.clamp(0.02, 0.48)),
        );
      }
    }
  }

  JackCorePoint3 _tiltOrbitPoint(
    JackCorePoint3 point,
    double tiltX,
    double tiltY,
  ) {
    final y = point.y * math.cos(tiltX);
    final z = point.y * math.sin(tiltX);
    final x2 = point.x * math.cos(tiltY) + z * math.sin(tiltY);
    final z2 = -point.x * math.sin(tiltY) + z * math.cos(tiltY);
    return JackCorePoint3(x2, y, z2);
  }

  void _drawEdges(
    Canvas canvas,
    Offset center,
    List<JackCoreEdge> edges,
    Map<String, JackCoreProjectedNode> projectedNodes,
    Map<String, Offset> screenPositions,
    JackCoreMotionProfile profile,
    Color tone,
  ) {
    for (final edge in edges) {
      final from = projectedNodes[edge.fromId];
      final to = projectedNodes[edge.toId];
      if (from == null || to == null) continue;
      final start = screenPositions[edge.fromId]!;
      final end = screenPositions[edge.toId]!;
      final midpoint = Offset.lerp(start, end, 0.5)!;
      final control = Offset.lerp(center, midpoint, 0.22)!;
      final depth = (from.depth + to.depth) * 0.5;
      final depthOpacity = 0.30 + (depth + 1) * 0.27;
      final strengthOpacity = 0.075 + edge.strength * 0.035;
      final path = Path()
        ..moveTo(start.dx, start.dy)
        ..quadraticBezierTo(control.dx, control.dy, end.dx, end.dy);
      canvas.drawPath(
        path,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeWidth = 0.55 + edge.strength * 0.22
          ..color = tone.withValues(
            alpha:
                (strengthOpacity * depthOpacity * (0.78 + profile.glow * 0.3))
                    .clamp(0.025, 0.23),
          ),
      );
    }
  }

  void _drawParticles(
    Canvas canvas,
    Offset center,
    double scale,
    double phaseValue,
    JackCoreMotionProfile profile,
    Color tone,
  ) {
    const count = 28;
    for (var index = 0; index < count; index++) {
      final angle =
          index * JackCoreProjection.goldenAngle +
          phaseValue * profile.spin * (index.isEven ? 2.0 : -1.4);
      final band = 1.08 + ((index * 31) % 100) / 100 * 0.42;
      final drift =
          math.sin(phaseValue * 2 + index * 1.7) * 0.018 * profile.pulse;
      final point = Offset(
        center.dx + math.cos(angle) * scale * (band + drift),
        center.dy + math.sin(angle) * scale * (band + drift) * 0.82,
      );
      final opacity =
          (0.055 + (index % 4) * 0.018) * (0.75 + profile.glow * 0.35);
      canvas.drawCircle(
        point,
        index % 7 == 0 ? 1.35 : 0.8,
        Paint()..color = tone.withValues(alpha: opacity.clamp(0.02, 0.14)),
      );
    }
  }

  void _drawNodes(
    Canvas canvas,
    List<JackCoreProjectedNode> nodes,
    Map<String, Offset> positions,
    double phaseValue,
    JackCoreMotionProfile profile,
  ) {
    for (final projected in nodes) {
      final node = projected.node;
      final visual = JackCoreVisualMapping.forNode(node);
      final center = positions[node.id]!;
      final depthOpacity = (0.52 + (projected.depth + 1) * 0.23).clamp(
        0.35,
        1.0,
      );
      final opacity = visual.opacity * depthOpacity * (1 - profile.dim * 0.42);
      final pulse =
          1 +
          math.sin(phaseValue * 1.3 + _stablePhaseOffset(node.id)) *
              profile.pulse *
              0.10;
      final radius = visual.radius * projected.perspectiveScale * pulse;
      final highlighted = node.id == highlightedNodeId;
      final selected = node.id == selectedNodeId;
      final glowRadius = radius * (3.4 + profile.glow * 1.2);

      canvas.drawCircle(
        center,
        glowRadius,
        Paint()
          ..shader = RadialGradient(
            colors: [
              visual.color.withValues(
                alpha: opacity * (0.22 + profile.glow * 0.14),
              ),
              visual.color.withValues(alpha: 0),
            ],
          ).createShader(Rect.fromCircle(center: center, radius: glowRadius)),
      );

      if (selected || highlighted) {
        canvas.drawCircle(
          center,
          radius * (selected ? 2.65 : 2.15),
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = selected ? 1.05 : 0.75
            ..color =
                (selected ? JackCorePalette.gold : JackCorePalette.glacier)
                    .withValues(alpha: selected ? 0.82 : 0.62),
        );
      }

      canvas.drawCircle(
        center,
        radius,
        Paint()
          ..color = visual.color.withValues(alpha: opacity.clamp(0.12, 1.0)),
      );
      canvas.drawCircle(
        center,
        radius * 1.42,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 0.55
          ..color = visual.verificationColor.withValues(alpha: opacity * 0.5),
      );
    }
  }

  double _stablePhaseOffset(String id) {
    var hash = 17;
    for (final unit in id.codeUnits) {
      hash = (hash * 31 + unit) & 0x7fffffff;
    }
    return hash * 0.001;
  }

  void _drawScan(
    Canvas canvas,
    Offset center,
    double scale,
    double phaseValue,
    JackCoreMotionProfile profile,
    Color tone,
  ) {
    if (profile.scan <= 0.001) return;
    final scanY = math.sin(phaseValue * 0.5) * scale * 0.62;
    final halfWidth = scale * 0.76;
    canvas.drawLine(
      Offset(center.dx - halfWidth, center.dy + scanY),
      Offset(center.dx + halfWidth, center.dy + scanY),
      Paint()
        ..strokeWidth = 0.7
        ..color = tone.withValues(
          alpha: (profile.scan * 0.18).clamp(0.02, 0.16),
        ),
    );
  }

  @override
  bool shouldRepaint(covariant JackCorePainter oldDelegate) =>
      oldDelegate.graph != graph ||
      oldDelegate.state != state ||
      oldDelegate.profileFrom != profileFrom ||
      oldDelegate.profileTo != profileTo ||
      oldDelegate.toneFrom != toneFrom ||
      oldDelegate.toneTo != toneTo ||
      oldDelegate.transition != transition ||
      oldDelegate.phase != phase ||
      oldDelegate.rotationX != rotationX ||
      oldDelegate.rotationY != rotationY ||
      oldDelegate.zoom != zoom ||
      oldDelegate.intensity != intensity ||
      oldDelegate.reducedMotion != reducedMotion ||
      oldDelegate.selectedNodeId != selectedNodeId ||
      oldDelegate.highlightedNodeId != highlightedNodeId ||
      oldDelegate.orbits != orbits ||
      oldDelegate.baseScale != baseScale;
}
