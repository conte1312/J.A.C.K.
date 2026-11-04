import 'dart:math' as math;

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';

import 'jack_core_graph.dart';
import 'jack_core_interaction.dart';
import 'jack_core_motion.dart';
import 'jack_core_painter.dart';
import 'jack_core_projection.dart';
import 'jack_core_state.dart';

class JackCore extends StatefulWidget {
  const JackCore({
    required this.graph,
    this.cognitiveState = JackCognitiveState.idle,
    this.intensity = JackCoreIntensity.medium,
    this.reducedMotion,
    this.selectedNodeId,
    this.highlightedNodeId,
    this.onNodeSelected,
    this.orbits = jackCoreDefaultOrbits,
    this.baseScale = 0.36,
    super.key,
  });

  final JackCoreGraph graph;
  final JackCognitiveState cognitiveState;
  final JackCoreIntensity intensity;

  /// When null, follows Flutter's `MediaQuery.disableAnimations` preference.
  final bool? reducedMotion;

  final String? selectedNodeId;
  final String? highlightedNodeId;
  final ValueChanged<JackCoreNode>? onNodeSelected;
  final List<JackCoreOrbit> orbits;

  /// Blueprint §8 default. The renderer clamps the scene to its viewport.
  final double baseScale;

  @override
  State<JackCore> createState() => _JackCoreState();
}

class _JackCoreState extends State<JackCore> with TickerProviderStateMixin {
  late final AnimationController _phaseController;
  late final AnimationController _transitionController;
  final JackCoreInteraction _interaction = JackCoreInteraction();

  late JackCognitiveState _fromState;
  bool _reducedMotion = false;
  String? _internalSelectedNodeId;
  Size _viewportSize = Size.zero;

  @override
  void initState() {
    super.initState();
    _fromState = widget.cognitiveState;
    _phaseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 60),
    )..repeat();
    _transitionController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 520),
      value: 1,
    );
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _syncReducedMotion();
  }

  @override
  void didUpdateWidget(covariant JackCore oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.selectedNodeId != widget.selectedNodeId) {
      _internalSelectedNodeId = widget.selectedNodeId;
    }
    if (oldWidget.cognitiveState != widget.cognitiveState) {
      _fromState = oldWidget.cognitiveState;
      if (_reducedMotion) {
        _transitionController.value = 1;
      } else {
        _transitionController.forward(from: 0);
      }
    }
    if (oldWidget.reducedMotion != widget.reducedMotion) {
      _syncReducedMotion();
    }
  }

  void _syncReducedMotion() {
    final requested =
        widget.reducedMotion ?? MediaQuery.of(context).disableAnimations;
    if (requested == _reducedMotion) return;
    _reducedMotion = requested;
    if (requested) {
      _phaseController.stop();
      _transitionController.value = 1;
    } else {
      _phaseController.repeat();
    }
  }

  @override
  void dispose() {
    _phaseController.dispose();
    _transitionController.dispose();
    super.dispose();
  }

  JackCoreMotionProfile _profileAtCurrentTransition() =>
      JackCoreMotionProfile.lerp(
        JackCoreMotionProfile.forState(_fromState),
        JackCoreMotionProfile.forState(widget.cognitiveState),
        _reducedMotion ? 1 : _transitionController.value,
      );

  JackCoreProjectionResult _project(Size size) {
    final profile = _profileAtCurrentTransition().scaled(widget.intensity);
    final phase = _reducedMotion
        ? 0
        : _phaseController.value * 6.283185307179586;
    final breathing = 1 + math.sin(phase * 0.82) * profile.breathe * 0.025;
    return JackCoreProjection.projectGraph(
      graph: widget.graph,
      size: size,
      rotationX: _interaction.rotationX,
      rotationY: _interaction.rotationY + phase * profile.spin * 8,
      zoom: _interaction.zoom,
      baseScale: widget.baseScale * breathing,
    );
  }

  void _handlePointerDown(PointerDownEvent event) {
    _interaction.begin(event);
  }

  void _handlePointerMove(PointerMoveEvent event) {
    if (_interaction.move(event)) setState(() {});
  }

  void _handlePointerUp(PointerUpEvent event) {
    final tapPosition = _interaction.end(event);
    if (tapPosition == null || _viewportSize.isEmpty) return;
    final nodeId = _interaction.pickNode(
      tapPosition,
      _project(_viewportSize).nodes,
    );
    if (nodeId == null) return;
    final node = widget.graph.nodes.firstWhere(
      (candidate) => candidate.id == nodeId,
    );
    setState(() => _internalSelectedNodeId = nodeId);
    widget.onNodeSelected?.call(node);
  }

  void _handlePointerSignal(PointerSignalEvent event) {
    if (event is! PointerScrollEvent) return;
    _interaction.zoomBy(event.scrollDelta.dy);
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final selectedNodeId = widget.selectedNodeId ?? _internalSelectedNodeId;
    final demo = widget.graph.origin == JackCoreGraphOrigin.demo;
    final label = demo ? 'Dataset dimostrativo' : 'Dati del nucleo';
    JackCoreNode? selectedNode;
    for (final node in widget.graph.nodes) {
      if (node.id == selectedNodeId) {
        selectedNode = node;
        break;
      }
    }
    final selectionValue = selectedNode == null
        ? null
        : '${selectedNode.title} · categoria ${selectedNode.category.name} · '
              '${selectedNode.source} · ${selectedNode.verification.name}';

    return LayoutBuilder(
      builder: (context, constraints) {
        final largest = constraints.biggest;
        final size = Size(
          largest.width.isFinite ? largest.width : 300,
          largest.height.isFinite ? largest.height : 300,
        );
        _viewportSize = size;

        final painter = JackCorePainter(
          graph: widget.graph,
          state: widget.cognitiveState,
          profileFrom: JackCoreMotionProfile.forState(_fromState),
          profileTo: JackCoreMotionProfile.forState(widget.cognitiveState),
          toneFrom: _fromState.tone,
          toneTo: widget.cognitiveState.tone,
          transition: _transitionController,
          phase: _phaseController,
          rotationX: _interaction.rotationX,
          rotationY: _interaction.rotationY,
          zoom: _interaction.zoom,
          intensity: widget.intensity,
          reducedMotion: _reducedMotion,
          selectedNodeId: selectedNodeId,
          highlightedNodeId: widget.highlightedNodeId,
          orbits: widget.orbits,
          baseScale: widget.baseScale,
        );

        return Semantics(
          label: 'Nucleo di J.A.C.K. · $label · ${widget.cognitiveState.label}',
          value: selectionValue,
          hint: 'Trascina per ruotare, scorri per lo zoom, fai clic su un nodo per selezionarlo.',
          child: MouseRegion(
            cursor: SystemMouseCursors.grab,
            child: Listener(
              key: const ValueKey('jack-core-interaction-layer'),
              behavior: HitTestBehavior.opaque,
              onPointerDown: _handlePointerDown,
              onPointerMove: _handlePointerMove,
              onPointerUp: _handlePointerUp,
              onPointerCancel: _interaction.cancel,
              onPointerSignal: _handlePointerSignal,
              child: RepaintBoundary(
                key: const ValueKey('jack-core-render-boundary'),
                child: CustomPaint(
                  key: const ValueKey('jack-core-painter'),
                  painter: painter,
                  child: const SizedBox.expand(),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}
