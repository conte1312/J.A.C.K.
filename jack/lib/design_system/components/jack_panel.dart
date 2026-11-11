/// The canonical J.A.C.K. surface: a translucent graphite panel with a thin
/// border, optional header and optional tap interaction.
library;

import 'package:flutter/material.dart';

import '../jack_motion.dart';
import '../tokens.dart';
import 'jack_badges.dart';

/// Reusable panel used by every screen.
class JackPanel extends StatefulWidget {
  const JackPanel({
    super.key,
    required this.child,
    this.eyebrow,
    this.title,
    this.trailing,
    this.padding = const EdgeInsets.all(JackSpacing.l),
    this.onTap,
    this.selected = false,
    this.accent,
    this.radius = JackRadius.m,
    this.elevated = false,
    this.gradient = false,
    this.clip = true,
    this.semanticLabel,
  });

  final Widget child;
  final String? eyebrow;
  final String? title;
  final Widget? trailing;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  final bool selected;
  final Color? accent;
  final double radius;
  final bool elevated;
  final bool gradient;
  final bool clip;
  final String? semanticLabel;

  @override
  State<JackPanel> createState() => _JackPanelState();
}

class _JackPanelState extends State<JackPanel> {
  bool _hovered = false;
  bool _focused = false;

  @override
  Widget build(BuildContext context) {
    final accent = widget.accent ?? JackColors.amber;
    final selected = widget.selected;
    final borderColor = _focused
        ? JackColors.cyan
        : selected
        ? accent.withValues(alpha: 0.55)
        : _hovered && widget.onTap != null
        ? JackColors.borderStrong
        : JackColors.borderSubtle;
    final background = selected
        ? Color.alphaBlend(
            accent.withValues(alpha: 0.07),
            JackColors.surfaceElevated,
          )
        : _hovered && widget.onTap != null
        ? JackColors.surfaceHover
        : JackColors.surfaceElevated;

    final content = Padding(
      padding: widget.padding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          if (widget.eyebrow != null ||
              widget.title != null ||
              widget.trailing != null)
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      if (widget.eyebrow != null) ...<Widget>[
                        JackEyebrow(widget.eyebrow!),
                        const SizedBox(height: JackSpacing.xs),
                      ],
                      if (widget.title != null)
                        Text(widget.title!, style: JackTypography.titleSmall),
                    ],
                  ),
                ),
                if (widget.trailing != null) ...<Widget>[
                  const SizedBox(width: JackSpacing.m),
                  widget.trailing!,
                ],
              ],
            ),
          if (widget.eyebrow != null ||
              widget.title != null ||
              widget.trailing != null)
            const SizedBox(height: JackSpacing.m),
          widget.child,
        ],
      ),
    );

    final decorated = AnimatedContainer(
      duration: JackMotion.fast(context),
      curve: JackCurves.standard,
      decoration: BoxDecoration(
        color: widget.gradient ? null : background,
        gradient: widget.gradient
            ? LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: <Color>[
                  Color.alphaBlend(
                    accent.withValues(alpha: 0.05),
                    JackColors.surfaceCard,
                  ),
                  JackColors.surface,
                ],
              )
            : null,
        borderRadius: BorderRadius.circular(widget.radius),
        border: Border.all(
          color: borderColor,
          width: _focused ? JackBorderWidth.focus : JackBorderWidth.thin,
        ),
        boxShadow: widget.elevated ? [JackShadows.floating] : null,
      ),
      child: widget.clip
          ? ClipRRect(
              borderRadius: BorderRadius.circular(widget.radius),
              child: content,
            )
          : content,
    );

    final interactive = widget.onTap == null
        ? decorated
        : Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: widget.onTap,
              onHover: (value) {
                if (_hovered != value) {
                  setState(() => _hovered = value);
                }
              },
              onFocusChange: (value) {
                if (_focused != value) {
                  setState(() => _focused = value);
                }
              },
              borderRadius: BorderRadius.circular(widget.radius),
              hoverColor: Colors.transparent,
              focusColor: Colors.transparent,
              splashColor: accent.withValues(alpha: 0.06),
              highlightColor: Colors.transparent,
              child: decorated,
            ),
          );

    return Semantics(
      button: widget.onTap != null,
      selected: widget.selected ? true : null,
      label: widget.semanticLabel,
      child: MouseRegion(
        cursor: widget.onTap == null
            ? MouseCursor.defer
            : SystemMouseCursors.click,
        child: interactive,
      ),
    );
  }
}
