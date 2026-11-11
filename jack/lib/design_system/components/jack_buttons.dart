/// Interactive controls shared by every screen.
library;

import 'package:flutter/material.dart';

import '../jack_motion.dart';
import '../tokens.dart';

/// Visual variants for [JackButton].
enum JackButtonVariant { primary, secondary, ghost, danger }

/// Size variants for [JackButton].
enum JackButtonSize { small, regular, large }

/// The canonical J.A.C.K. button. All variants support hover, focus,
/// keyboard activation, disabled tooltips and optional icons.
class JackButton extends StatefulWidget {
  const JackButton({
    super.key,
    required this.label,
    this.onPressed,
    this.variant = JackButtonVariant.secondary,
    this.size = JackButtonSize.regular,
    this.icon,
    this.tooltip,
    this.fullWidth = false,
    this.semanticLabel,
  });

  final String label;
  final VoidCallback? onPressed;
  final JackButtonVariant variant;
  final JackButtonSize size;
  final IconData? icon;
  final String? tooltip;
  final bool fullWidth;
  final String? semanticLabel;

  bool get _enabled => onPressed != null;

  @override
  State<JackButton> createState() => _JackButtonState();
}

class _JackButtonState extends State<JackButton> {
  bool _hovered = false;
  bool _focused = false;

  double get _height => switch (widget.size) {
    JackButtonSize.small => 30,
    JackButtonSize.regular => JackSizes.buttonHeight,
    JackButtonSize.large => JackSizes.buttonHeightLarge,
  };

  double get _horizontalPadding => switch (widget.size) {
    JackButtonSize.small => JackSpacing.m,
    JackButtonSize.regular => JackSpacing.l,
    JackButtonSize.large => JackSpacing.xl,
  };

  double get _iconSize => switch (widget.size) {
    JackButtonSize.small => 14,
    JackButtonSize.regular => 16,
    JackButtonSize.large => 17,
  };

  TextStyle get _textStyle {
    final base = switch (widget.size) {
      JackButtonSize.small => JackTypography.micro,
      JackButtonSize.regular => JackTypography.label,
      JackButtonSize.large => JackTypography.label.copyWith(fontSize: 12.5),
    };
    return base;
  }

  ({Color background, Color foreground, Color border}) get _colors {
    if (!widget._enabled) {
      return (
        background: widget.variant == JackButtonVariant.ghost
            ? Colors.transparent
            : JackColors.surface,
        foreground: JackColors.textDisabled,
        border: JackColors.borderSubtle,
      );
    }
    switch (widget.variant) {
      case JackButtonVariant.primary:
        return (
          background: _hovered || _focused
              ? JackColors.amberBright
              : JackColors.amber,
          foreground: JackColors.backgroundDeep,
          border: Colors.transparent,
        );
      case JackButtonVariant.secondary:
        return (
          background: _hovered || _focused
              ? JackColors.surfaceHover
              : JackColors.surfaceElevated,
          foreground: JackColors.textPrimary,
          border: _focused ? JackColors.cyan : JackColors.border,
        );
      case JackButtonVariant.ghost:
        return (
          background: _hovered || _focused
              ? JackColors.highlight
              : Colors.transparent,
          foreground: _hovered || _focused
              ? JackColors.textPrimary
              : JackColors.textSecondary,
          border: Colors.transparent,
        );
      case JackButtonVariant.danger:
        return (
          background: JackColors.error.withValues(
            alpha: _hovered || _focused ? 0.18 : 0.1,
          ),
          foreground: JackColors.error,
          border: JackColors.error.withValues(alpha: 0.35),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = _colors;
    final content = AnimatedContainer(
      duration: JackMotion.fast(context),
      curve: JackCurves.standard,
      height: _height,
      width: widget.fullWidth ? double.infinity : null,
      padding: EdgeInsets.symmetric(horizontal: _horizontalPadding),
      decoration: BoxDecoration(
        color: colors.background,
        borderRadius: BorderRadius.circular(JackRadius.s),
        border: Border.all(
          color: colors.border,
          width: _focused ? JackBorderWidth.focus : JackBorderWidth.thin,
        ),
      ),
      child: Row(
        mainAxisSize: widget.fullWidth ? MainAxisSize.max : MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          if (widget.icon != null) ...<Widget>[
            Icon(widget.icon, size: _iconSize, color: colors.foreground),
            const SizedBox(width: JackSpacing.s),
          ],
          Flexible(
            child: Text(
              widget.label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: _textStyle.copyWith(
                color: colors.foreground,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );

    Widget result = Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: widget.onPressed,
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
        canRequestFocus: widget._enabled,
        borderRadius: BorderRadius.circular(JackRadius.s),
        hoverColor: Colors.transparent,
        focusColor: Colors.transparent,
        splashColor: colors.foreground.withValues(alpha: 0.08),
        highlightColor: Colors.transparent,
        child: content,
      ),
    );

    result = Semantics(
      button: true,
      enabled: widget._enabled,
      label: widget.semanticLabel ?? widget.tooltip ?? widget.label,
      child: MouseRegion(
        cursor: widget._enabled
            ? SystemMouseCursors.click
            : SystemMouseCursors.basic,
        child: result,
      ),
    );

    if (widget.tooltip != null) {
      result = Tooltip(message: widget.tooltip!, child: result);
    }

    return result;
  }
}

/// Square icon button with a tooltip and an optional selected state.
class JackIconButton extends StatefulWidget {
  const JackIconButton({
    super.key,
    required this.icon,
    required this.tooltip,
    this.onPressed,
    this.selected = false,
    this.size = JackSizes.iconButtonSize,
    this.iconSize = 17,
    this.tone,
  });

  final IconData icon;
  final String tooltip;
  final VoidCallback? onPressed;
  final bool selected;
  final double size;
  final double iconSize;
  final Color? tone;

  bool get _enabled => onPressed != null;

  @override
  State<JackIconButton> createState() => _JackIconButtonState();
}

class _JackIconButtonState extends State<JackIconButton> {
  bool _hovered = false;
  bool _focused = false;

  @override
  Widget build(BuildContext context) {
    final accent = widget.tone ?? JackColors.amber;
    final foreground = !widget._enabled
        ? JackColors.textDisabled
        : widget.selected
        ? accent
        : _hovered || _focused
        ? JackColors.textPrimary
        : JackColors.textSecondary;
    final background = widget.selected
        ? accent.withValues(alpha: 0.12)
        : _hovered || _focused
        ? JackColors.highlight
        : Colors.transparent;
    final border = _focused
        ? JackColors.cyan
        : widget.selected
        ? accent.withValues(alpha: 0.32)
        : Colors.transparent;

    return Tooltip(
      message: widget.tooltip,
      child: Semantics(
        button: true,
        enabled: widget._enabled,
        selected: widget.selected ? true : null,
        label: widget.tooltip,
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: widget.onPressed,
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
            canRequestFocus: widget._enabled,
            borderRadius: BorderRadius.circular(JackRadius.s),
            hoverColor: Colors.transparent,
            focusColor: Colors.transparent,
            splashColor: accent.withValues(alpha: 0.08),
            highlightColor: Colors.transparent,
            child: AnimatedContainer(
              duration: JackMotion.fast(context),
              width: widget.size,
              height: widget.size,
              decoration: BoxDecoration(
                color: background,
                borderRadius: BorderRadius.circular(JackRadius.s),
                border: Border.all(
                  color: border,
                  width: _focused
                      ? JackBorderWidth.focus
                      : JackBorderWidth.thin,
                ),
              ),
              child: Icon(
                widget.icon,
                size: widget.iconSize,
                color: foreground,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
