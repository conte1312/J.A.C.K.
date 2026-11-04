import 'package:flutter/material.dart';

import 'jack_core_graph.dart';
import 'jack_core_palette.dart';

class JackCoreNodeVisual {
  const JackCoreNodeVisual({
    required this.color,
    required this.verificationColor,
    required this.radius,
    required this.opacity,
  });

  final Color color;
  final Color verificationColor;
  final double radius;
  final double opacity;
}

abstract final class JackCoreVisualMapping {
  static JackCoreNodeVisual forNode(JackCoreNode node) {
    final color = switch (node.sourceType) {
      JackCoreSourceType.saved => JackCorePalette.saved,
      JackCoreSourceType.retrieved => JackCorePalette.retrieved,
      JackCoreSourceType.inference => JackCorePalette.inferred,
    };
    final verificationColor = switch (node.verification) {
      JackCoreVerification.verified => JackCorePalette.saved,
      JackCoreVerification.toVerify => JackCorePalette.amberSoft,
      JackCoreVerification.inferred => JackCorePalette.inferred,
    };
    return JackCoreNodeVisual(
      color: color,
      verificationColor: verificationColor,
      radius: 2.35 + (node.importance - 1) * 0.55,
      opacity: node.excluded ? 0.24 : 1.0,
    );
  }
}
