import 'dart:math' as math;

import 'package:flutter/widgets.dart';

import 'jack_core_graph.dart';

class JackCorePoint3 {
  const JackCorePoint3(this.x, this.y, this.z);

  final double x;
  final double y;
  final double z;

  JackCorePoint3 scale(double value) =>
      JackCorePoint3(x * value, y * value, z * value);

  JackCorePoint3 operator +(JackCorePoint3 other) =>
      JackCorePoint3(x + other.x, y + other.y, z + other.z);
}

class JackCoreProjectedNode {
  const JackCoreProjectedNode({
    required this.node,
    required this.position,
    required this.depth,
    required this.perspectiveScale,
  });

  final JackCoreNode node;
  final Offset position;
  final double depth;
  final double perspectiveScale;
}

class JackCoreProjectedPoint {
  const JackCoreProjectedPoint({
    required this.position,
    required this.depth,
    required this.perspectiveScale,
  });

  final Offset position;
  final double depth;
  final double perspectiveScale;
}

class JackCoreProjectionResult {
  const JackCoreProjectionResult({
    required this.center,
    required this.unitScale,
    required this.nodes,
  });

  final Offset center;
  final double unitScale;
  final List<JackCoreProjectedNode> nodes;
}

abstract final class JackCoreProjection {
  static const interiorShellRadius = 0.62;
  static const cameraDistance = 5.6;
  static const maximumOrbitRadius = 1.52;
  static final goldenAngle = math.pi * (3 - math.sqrt(5));

  static JackCoreProjectionResult projectGraph({
    required JackCoreGraph graph,
    required Size size,
    required double rotationX,
    required double rotationY,
    required double zoom,
    required double baseScale,
  }) {
    final minDimension = math.min(size.width, size.height);
    final desiredScale = minDimension * baseScale;
    final maximumPerspective =
        cameraDistance / (cameraDistance - maximumOrbitRadius);
    final fitScale =
        (minDimension * 0.44) / (maximumOrbitRadius * maximumPerspective);
    final unitScale = math.min(desiredScale, fitScale) * zoom;
    final center = Offset(size.width / 2, size.height / 2);
    final positions = _layoutNodes(graph.nodes);
    final projected = <JackCoreProjectedNode>[];

    for (final node in graph.nodes) {
      final point = _rotate(
        positions[node.id]!,
        rotationX: rotationX,
        rotationY: rotationY,
      );
      final perspective = cameraDistance / (cameraDistance - point.z);
      projected.add(
        JackCoreProjectedNode(
          node: node,
          position: Offset(
            center.dx + point.x * unitScale * perspective,
            center.dy + point.y * unitScale * perspective,
          ),
          depth: point.z,
          perspectiveScale: perspective,
        ),
      );
    }

    projected.sort((a, b) => a.depth.compareTo(b.depth));
    return JackCoreProjectionResult(
      center: center,
      unitScale: unitScale,
      nodes: List.unmodifiable(projected),
    );
  }

  static Offset projectPoint({
    required JackCorePoint3 point,
    required Size size,
    required double rotationX,
    required double rotationY,
    required double unitScale,
  }) => projectPointDetailed(
    point: point,
    size: size,
    rotationX: rotationX,
    rotationY: rotationY,
    unitScale: unitScale,
  ).position;

  static JackCoreProjectedPoint projectPointDetailed({
    required JackCorePoint3 point,
    required Size size,
    required double rotationX,
    required double rotationY,
    required double unitScale,
  }) {
    final rotated = _rotate(point, rotationX: rotationX, rotationY: rotationY);
    final perspective = cameraDistance / (cameraDistance - rotated.z);
    return JackCoreProjectedPoint(
      position: Offset(
        size.width / 2 + rotated.x * unitScale * perspective,
        size.height / 2 + rotated.y * unitScale * perspective,
      ),
      depth: rotated.z,
      perspectiveScale: perspective,
    );
  }

  static Map<String, JackCorePoint3> _layoutNodes(List<JackCoreNode> nodes) {
    final sorted = [...nodes]..sort((a, b) => a.id.compareTo(b.id));
    final byShell = <JackCoreShell, List<JackCoreNode>>{
      for (final shell in JackCoreShell.values)
        shell: sorted.where((node) => node.shell == shell).toList(),
    };
    final positions = <String, JackCorePoint3>{};

    for (final shell in JackCoreShell.values) {
      final shellNodes = byShell[shell]!;
      final shellScale = shell == JackCoreShell.surface
          ? 1.0
          : interiorShellRadius;
      for (var index = 0; index < shellNodes.length; index++) {
        final z = 1 - 2 * (index + 0.5) / shellNodes.length;
        final horizontalRadius = math.sqrt(math.max(0, 1 - z * z));
        final phase =
            index * goldenAngle +
            (shell == JackCoreShell.interior ? 0.41 : 0.0);
        positions[shellNodes[index].id] = JackCorePoint3(
          math.cos(phase) * horizontalRadius * shellScale,
          math.sin(phase) * horizontalRadius * shellScale,
          z * shellScale,
        );
      }
    }
    return positions;
  }

  static JackCorePoint3 _rotate(
    JackCorePoint3 point, {
    required double rotationX,
    required double rotationY,
  }) {
    final cosY = math.cos(rotationY);
    final sinY = math.sin(rotationY);
    final afterY = JackCorePoint3(
      point.x * cosY + point.z * sinY,
      point.y,
      -point.x * sinY + point.z * cosY,
    );
    final cosX = math.cos(rotationX);
    final sinX = math.sin(rotationX);
    return JackCorePoint3(
      afterY.x,
      afterY.y * cosX - afterY.z * sinX,
      afterY.y * sinX + afterY.z * cosX,
    );
  }
}
