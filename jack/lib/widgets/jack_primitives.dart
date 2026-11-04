import 'package:flutter/material.dart';

import '../theme/jack_theme.dart';

class JackPanel extends StatelessWidget {
  const JackPanel({
    required this.child,
    this.padding,
    this.radius = 20,
    super.key,
  });

  final Widget child;
  final EdgeInsetsGeometry? padding;
  final double radius;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: JackPalette.panel,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: JackPalette.border),
      ),
      padding: padding,
      child: child,
    );
  }
}

class SectionEyebrow extends StatelessWidget {
  const SectionEyebrow(this.label, {super.key});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Text(
      label.toUpperCase(),
      style: const TextStyle(
        color: JackPalette.dim,
        fontSize: 9,
        letterSpacing: 2,
        fontWeight: FontWeight.w600,
      ),
    );
  }
}

class DemoBadge extends StatelessWidget {
  const DemoBadge({this.label = 'DEMO', super.key});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: JackPalette.amber.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: JackPalette.amber.withValues(alpha: 0.25)),
      ),
      child: Text(
        label,
        style: const TextStyle(
          color: JackPalette.amber,
          fontSize: 8,
          letterSpacing: 1,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class StatusDot extends StatelessWidget {
  const StatusDot({required this.color, this.size = 6, super.key});

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color,
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: 0.36),
            blurRadius: size * 1.8,
          ),
        ],
      ),
    );
  }
}
