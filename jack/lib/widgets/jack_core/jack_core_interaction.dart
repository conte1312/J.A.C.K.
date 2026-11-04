import 'dart:math' as math;

import 'package:flutter/gestures.dart';

import 'jack_core_projection.dart';
import 'jack_core_visual_mapping.dart';

class JackCoreInteraction {
  static const clickMovementLimit = 6.0;
  static const minZoom = 0.82;
  static const maxZoom = 1.24;

  double rotationX = 0;
  double rotationY = 0;
  double zoom = 1;

  int? _activePointer;
  Offset? _pointerStart;
  Offset? _lastPosition;
  double _travelled = 0;
  bool _dragging = false;

  bool begin(PointerDownEvent event) {
    if (_activePointer != null || (event.buttons & kPrimaryMouseButton) == 0) {
      return false;
    }
    _activePointer = event.pointer;
    _pointerStart = event.localPosition;
    _lastPosition = event.localPosition;
    _travelled = 0;
    _dragging = false;
    return true;
  }

  bool move(PointerMoveEvent event) {
    if (event.pointer != _activePointer) return false;
    final start = _pointerStart;
    final previous = _lastPosition;
    if (start == null || previous == null) return false;

    _travelled = math.max(_travelled, (event.localPosition - start).distance);
    _lastPosition = event.localPosition;
    if (_travelled >= clickMovementLimit) _dragging = true;
    if (!_dragging) return false;

    final delta = event.localPosition - previous;
    rotationY += delta.dx * 0.008;
    rotationX = (rotationX + delta.dy * 0.008).clamp(-math.pi / 2, math.pi / 2);
    return true;
  }

  Offset? end(PointerUpEvent event) {
    if (event.pointer != _activePointer) return null;
    final tap = !_dragging && _travelled < clickMovementLimit
        ? event.localPosition
        : null;
    _clearPointer();
    return tap;
  }

  void cancel(PointerCancelEvent event) {
    if (event.pointer == _activePointer) _clearPointer();
  }

  void zoomBy(double scrollDeltaY) {
    zoom = (zoom - scrollDeltaY * 0.0007).clamp(minZoom, maxZoom).toDouble();
  }

  String? pickNode(Offset point, List<JackCoreProjectedNode> nodes) {
    JackCoreProjectedNode? closest;
    var closestDistance = double.infinity;
    for (final projected in nodes) {
      final visual = JackCoreVisualMapping.forNode(projected.node);
      final hitRadius = math.max(
        10.0,
        visual.radius * projected.perspectiveScale * 3.2,
      );
      final distance = (projected.position - point).distance;
      if (distance <= hitRadius && distance < closestDistance) {
        closest = projected;
        closestDistance = distance;
      }
    }
    return closest?.node.id;
  }

  void _clearPointer() {
    _activePointer = null;
    _pointerStart = null;
    _lastPosition = null;
    _travelled = 0;
    _dragging = false;
  }
}
