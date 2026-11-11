/// Small status and metadata components shared by all screens.
library;

import 'package:flutter/material.dart';

import '../jack_motion.dart';
import '../jack_tone.dart';
import '../tokens.dart';

/// A compact pill with a tinted background and a thin border.
class JackBadge extends StatelessWidget {
  const JackBadge({
    super.key,
    required this.label,
    this.tone = JackTone.neutral,
    this.icon,
    this.dense = false,
    this.uppercase = false,
  });

  final String label;
  final JackTone tone;
  final IconData? icon;
  final bool dense;
  final bool uppercase;

  @override
  Widget build(BuildContext context) {
    final color = tone.color;
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: dense ? JackSpacing.s : JackSpacing.m,
        vertical: dense ? 2 : 4,
      ),
      decoration: BoxDecoration(
        color: tone.background,
        borderRadius: BorderRadius.circular(JackRadius.full),
        border: Border.all(color: tone.border, width: JackBorderWidth.thin),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (icon != null) ...<Widget>[
            Icon(icon, size: dense ? 10 : 12, color: color),
            const SizedBox(width: JackSpacing.xs),
          ],
          Text(
            uppercase ? label.toUpperCase() : label,
            style: (dense ? JackTypography.micro : JackTypography.caption)
                .copyWith(
                  color: color,
                  fontWeight: FontWeight.w600,
                  letterSpacing: uppercase ? 0.8 : 0.1,
                ),
          ),
        ],
      ),
    );
  }
}

/// Explicit label for demonstration-only content.
class JackDemoBadge extends StatelessWidget {
  const JackDemoBadge({super.key, this.dense = true});

  final bool dense;

  @override
  Widget build(BuildContext context) {
    return JackBadge(
      label: 'Demo',
      tone: JackTone.amber,
      icon: JackIcons.demo,
      dense: dense,
      uppercase: true,
    );
  }
}

/// Badge that points to the milestone in which a capability becomes real.
class JackMilestoneBadge extends StatelessWidget {
  const JackMilestoneBadge({
    super.key,
    required this.milestone,
    this.tone = JackTone.cyan,
    this.prefix = 'Disponibile in',
  });

  final String milestone;
  final JackTone tone;
  final String prefix;

  @override
  Widget build(BuildContext context) {
    return JackBadge(
      label: '$prefix $milestone',
      tone: tone,
      icon: JackIcons.schedule,
      dense: true,
    );
  }
}

/// Small metadata tag (keywords, capabilities, tags).
class JackTag extends StatelessWidget {
  const JackTag({super.key, required this.label, this.icon});

  final String label;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: JackSpacing.s,
        vertical: 3,
      ),
      decoration: BoxDecoration(
        color: JackColors.surface,
        borderRadius: BorderRadius.circular(JackRadius.xs),
        border: Border.all(
          color: JackColors.borderSubtle,
          width: JackBorderWidth.thin,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (icon != null) ...<Widget>[
            Icon(icon, size: 11, color: JackColors.textMuted),
            const SizedBox(width: JackSpacing.xs),
          ],
          Text(
            label,
            style: JackTypography.micro.copyWith(color: JackColors.textMuted),
          ),
        ],
      ),
    );
  }
}

/// Dot + label status indicator.
class JackStatusIndicator extends StatelessWidget {
  const JackStatusIndicator({
    super.key,
    required this.status,
    this.label,
    this.showLabel = true,
    this.dotSize = 7,
  });

  final JackStatus status;
  final String? label;
  final bool showLabel;
  final double dotSize;

  @override
  Widget build(BuildContext context) {
    final tone = status.tone;
    final text = label ?? status.defaultLabel;
    return Semantics(
      label: text,
      readOnly: true,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          AnimatedContainer(
            duration: JackMotion.normal(context),
            width: dotSize,
            height: dotSize,
            decoration: BoxDecoration(
              color: tone.color,
              shape: BoxShape.circle,
              boxShadow: <BoxShadow>[
                BoxShadow(
                  color: tone.color.withValues(alpha: 0.35),
                  blurRadius: 6,
                  spreadRadius: 1,
                ),
              ],
            ),
          ),
          if (showLabel) ...<Widget>[
            const SizedBox(width: JackSpacing.s),
            Text(
              text,
              style: JackTypography.caption.copyWith(
                color: tone.color,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Pill version of [JackStatusIndicator].
class JackStatusPill extends StatelessWidget {
  const JackStatusPill({
    super.key,
    required this.status,
    this.label,
    this.dense = false,
  });

  final JackStatus status;
  final String? label;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final tone = status.tone;
    final text = label ?? status.defaultLabel;
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: dense ? JackSpacing.s : JackSpacing.m,
        vertical: dense ? 3 : 5,
      ),
      decoration: BoxDecoration(
        color: tone.background,
        borderRadius: BorderRadius.circular(JackRadius.full),
        border: Border.all(color: tone.border, width: JackBorderWidth.thin),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: tone.color,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: JackSpacing.xs + 1),
          Text(
            text,
            style: (dense ? JackTypography.micro : JackTypography.caption)
                .copyWith(color: tone.color, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}

/// Uppercase section eyebrow.
class JackEyebrow extends StatelessWidget {
  const JackEyebrow(this.text, {super.key, this.color});

  final String text;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Text(
      text.toUpperCase(),
      style: JackTypography.eyebrow.copyWith(color: color),
    );
  }
}
