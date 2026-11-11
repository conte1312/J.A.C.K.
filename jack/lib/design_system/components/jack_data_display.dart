/// Small data-display components shared by the screens.
library;

import 'package:flutter/material.dart';

import '../jack_motion.dart';
import '../jack_tone.dart';
import '../tokens.dart';

/// Rounded progress bar that respects reduced motion.
class JackProgressBar extends StatelessWidget {
  const JackProgressBar({
    super.key,
    required this.value,
    this.tone = JackTone.amber,
    this.height = 6,
  });

  final double value;
  final JackTone tone;
  final double height;

  @override
  Widget build(BuildContext context) {
    final clamped = value.clamp(0.0, 1.0).toDouble();
    return ClipRRect(
      borderRadius: BorderRadius.circular(JackRadius.full),
      child: SizedBox(
        height: height,
        child: Stack(
          fit: StackFit.expand,
          children: <Widget>[
            Container(color: JackColors.borderSubtle),
            TweenAnimationBuilder<double>(
              tween: Tween<double>(begin: 0, end: clamped),
              duration: JackMotion.normal(context),
              curve: JackCurves.standard,
              builder: (context, animated, _) {
                return FractionallySizedBox(
                  alignment: Alignment.centerLeft,
                  widthFactor: animated,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      color: tone.color,
                      borderRadius: BorderRadius.circular(JackRadius.full),
                    ),
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

/// Circular initials avatar.
class JackAvatar extends StatelessWidget {
  const JackAvatar({
    super.key,
    required this.initials,
    this.size = JackSizes.avatarMedium,
    this.tone = JackTone.amber,
  });

  final String initials;
  final double size;
  final JackTone tone;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            tone.color.withValues(alpha: 0.26),
            tone.color.withValues(alpha: 0.1),
          ],
        ),
        border: Border.all(color: tone.border, width: JackBorderWidth.thin),
      ),
      child: Text(
        initials.toUpperCase(),
        style: JackTypography.label.copyWith(
          color: tone.color,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.4,
          fontSize: size <= JackSizes.avatarSmall ? 10 : 12,
        ),
      ),
    );
  }
}

/// Label/value row used in metadata sections.
class JackMetaRow extends StatelessWidget {
  const JackMetaRow({
    super.key,
    required this.label,
    required this.value,
    this.mono = false,
    this.valueColor,
  });

  final String label;
  final String value;
  final bool mono;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SizedBox(
            width: 116,
            child: Text(label, style: JackTypography.caption),
          ),
          const SizedBox(width: JackSpacing.s),
          Expanded(
            child: Text(
              value,
              style: (mono ? JackTypography.mono : JackTypography.bodySecondary)
                  .copyWith(
                    color: valueColor ?? JackColors.textSecondary,
                    fontSize: mono ? 11.5 : null,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Small metric card.
class JackStatCard extends StatelessWidget {
  const JackStatCard({
    super.key,
    required this.label,
    required this.value,
    this.icon,
    this.tone = JackTone.amber,
    this.caption,
  });

  final String label;
  final String value;
  final IconData? icon;
  final JackTone tone;
  final String? caption;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(JackSpacing.m),
      decoration: BoxDecoration(
        color: JackColors.surfaceElevated,
        borderRadius: BorderRadius.circular(JackRadius.s),
        border: Border.all(
          color: JackColors.borderSubtle,
          width: JackBorderWidth.thin,
        ),
      ),
      child: Row(
        children: <Widget>[
          if (icon != null) ...<Widget>[
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: tone.background,
                borderRadius: BorderRadius.circular(JackRadius.s),
                border: Border.all(
                  color: tone.border,
                  width: JackBorderWidth.thin,
                ),
              ),
              child: Icon(icon, size: 15, color: tone.color),
            ),
            const SizedBox(width: JackSpacing.m),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Text(
                  value,
                  style: JackTypography.title.copyWith(
                    fontSize: 19,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  label.toUpperCase(),
                  style: JackTypography.micro.copyWith(
                    color: JackColors.textMuted,
                    letterSpacing: 0.8,
                  ),
                ),
                if (caption != null)
                  Text(caption!, style: JackTypography.micro),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Thin section divider with consistent spacing.
class JackDivider extends StatelessWidget {
  const JackDivider({super.key, this.spacing = JackSpacing.l});

  final double spacing;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: spacing),
      child: const Divider(),
    );
  }
}
