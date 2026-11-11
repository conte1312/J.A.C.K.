/// Inputs, filters and preference controls shared by the screens.
library;

import 'package:flutter/material.dart';

import '../jack_motion.dart';
import '../tokens.dart';
import 'jack_buttons.dart';

/// Search field with a leading icon and a clear action.
class JackSearchField extends StatelessWidget {
  const JackSearchField({
    super.key,
    required this.controller,
    this.hint = 'Cerca…',
    this.onChanged,
    this.width,
    this.autofocus = false,
  });

  final TextEditingController controller;
  final String hint;
  final ValueChanged<String>? onChanged;
  final double? width;
  final bool autofocus;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      height: JackSizes.inputHeight,
      child: ValueListenableBuilder<TextEditingValue>(
        valueListenable: controller,
        builder: (context, value, _) {
          return TextField(
            controller: controller,
            onChanged: onChanged,
            autofocus: autofocus,
            maxLines: 1,
            style: JackTypography.bodySecondary.copyWith(
              color: JackColors.textPrimary,
            ),
            decoration: InputDecoration(
              hintText: hint,
              prefixIcon: const Icon(
                JackIcons.search,
                size: 16,
                color: JackColors.textMuted,
              ),
              prefixIconConstraints: const BoxConstraints(
                minWidth: 38,
                minHeight: 38,
              ),
              suffixIcon: value.text.isEmpty
                  ? null
                  : Padding(
                      padding: const EdgeInsets.only(right: 5),
                      child: JackIconButton(
                        icon: JackIcons.close,
                        tooltip: 'Cancella ricerca',
                        size: 28,
                        iconSize: 14,
                        onPressed: () {
                          controller.clear();
                          onChanged?.call('');
                        },
                      ),
                    ),
              suffixIconConstraints: const BoxConstraints(
                minWidth: 36,
                minHeight: 36,
              ),
              contentPadding: const EdgeInsets.symmetric(
                horizontal: JackSpacing.s,
                vertical: JackSpacing.s,
              ),
            ),
          );
        },
      ),
    );
  }
}

/// Labelled text field used by forms.
class JackTextField extends StatelessWidget {
  const JackTextField({
    super.key,
    required this.controller,
    required this.label,
    this.hint,
    this.helper,
    this.errorText,
    this.maxLines = 1,
    this.minLines,
    this.enabled = true,
    this.autofocus = false,
    this.onChanged,
  });

  final TextEditingController controller;
  final String label;
  final String? hint;
  final String? helper;
  final String? errorText;
  final int maxLines;
  final int? minLines;
  final bool enabled;
  final bool autofocus;
  final ValueChanged<String>? onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Text(label, style: JackTypography.label),
        const SizedBox(height: JackSpacing.xs + 2),
        TextField(
          controller: controller,
          enabled: enabled,
          autofocus: autofocus,
          maxLines: maxLines,
          minLines: minLines,
          onChanged: onChanged,
          style: JackTypography.bodySecondary.copyWith(
            color: enabled ? JackColors.textPrimary : JackColors.textDisabled,
          ),
          decoration: InputDecoration(
            hintText: hint,
            errorText: errorText,
            helperText: helper,
            helperMaxLines: 3,
            errorMaxLines: 2,
          ),
        ),
      ],
    );
  }
}

/// One choice inside a [JackSegmentedControl].
class JackSegment<T> {
  const JackSegment({required this.value, required this.label, this.icon});

  final T value;
  final String label;
  final IconData? icon;
}

/// Compact segmented control for view modes and filters.
class JackSegmentedControl<T> extends StatelessWidget {
  const JackSegmentedControl({
    super.key,
    required this.segments,
    required this.selected,
    required this.onChanged,
    this.dense = false,
  });

  final List<JackSegment<T>> segments;
  final T selected;
  final ValueChanged<T>? onChanged;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: JackColors.surface,
        borderRadius: BorderRadius.circular(JackRadius.s),
        border: Border.all(
          color: JackColors.borderSubtle,
          width: JackBorderWidth.thin,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          for (final segment in segments)
            _JackSegmentButton<T>(
              segment: segment,
              selected: segment.value == selected,
              dense: dense,
              onTap: onChanged == null ? null : () => onChanged!(segment.value),
            ),
        ],
      ),
    );
  }
}

class _JackSegmentButton<T> extends StatefulWidget {
  const _JackSegmentButton({
    required this.segment,
    required this.selected,
    required this.dense,
    required this.onTap,
  });

  final JackSegment<T> segment;
  final bool selected;
  final bool dense;
  final VoidCallback? onTap;

  @override
  State<_JackSegmentButton<T>> createState() => _JackSegmentButtonState<T>();
}

class _JackSegmentButtonState<T> extends State<_JackSegmentButton<T>> {
  bool _hovered = false;
  bool _focused = false;

  @override
  Widget build(BuildContext context) {
    final enabled = widget.onTap != null;
    final foreground = !enabled
        ? JackColors.textDisabled
        : widget.selected
        ? JackColors.amber
        : _hovered || _focused
        ? JackColors.textPrimary
        : JackColors.textSecondary;
    final background = widget.selected
        ? JackColors.amberSoft
        : _hovered || _focused
        ? JackColors.highlight
        : Colors.transparent;
    final border = _focused
        ? JackColors.cyan
        : widget.selected
        ? JackColors.amber.withValues(alpha: 0.28)
        : Colors.transparent;

    return Semantics(
      button: true,
      selected: widget.selected,
      enabled: enabled,
      label: widget.segment.label,
      child: Material(
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
          canRequestFocus: enabled,
          borderRadius: BorderRadius.circular(JackRadius.xs + 1),
          hoverColor: Colors.transparent,
          focusColor: Colors.transparent,
          splashColor: JackColors.amber.withValues(alpha: 0.08),
          highlightColor: Colors.transparent,
          child: AnimatedContainer(
            duration: JackMotion.fast(context),
            height: widget.dense ? 26 : 30,
            padding: EdgeInsets.symmetric(
              horizontal: widget.dense ? JackSpacing.s + 1 : JackSpacing.m,
            ),
            decoration: BoxDecoration(
              color: background,
              borderRadius: BorderRadius.circular(JackRadius.xs + 1),
              border: Border.all(
                color: border,
                width: _focused ? JackBorderWidth.focus : JackBorderWidth.thin,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                if (widget.segment.icon != null) ...<Widget>[
                  Icon(
                    widget.segment.icon,
                    size: widget.dense ? 13 : 14,
                    color: foreground,
                  ),
                  const SizedBox(width: JackSpacing.xs + 1),
                ],
                Text(
                  widget.segment.label,
                  style:
                      (widget.dense
                              ? JackTypography.micro
                              : JackTypography.caption)
                          .copyWith(
                            color: foreground,
                            fontWeight: widget.selected
                                ? FontWeight.w600
                                : FontWeight.w500,
                          ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Filter pill with an optional count.
class JackFilterChip extends StatefulWidget {
  const JackFilterChip({
    super.key,
    required this.label,
    required this.selected,
    required this.onTap,
    this.count,
    this.icon,
  });

  final String label;
  final bool selected;
  final VoidCallback? onTap;
  final int? count;
  final IconData? icon;

  @override
  State<JackFilterChip> createState() => _JackFilterChipState();
}

class _JackFilterChipState extends State<JackFilterChip> {
  bool _hovered = false;
  bool _focused = false;

  @override
  Widget build(BuildContext context) {
    final enabled = widget.onTap != null;
    final foreground = !enabled
        ? JackColors.textDisabled
        : widget.selected
        ? JackColors.amber
        : _hovered || _focused
        ? JackColors.textPrimary
        : JackColors.textSecondary;
    final background = widget.selected
        ? JackColors.amberSoft
        : _hovered || _focused
        ? JackColors.highlight
        : JackColors.surface;
    final border = _focused
        ? JackColors.cyan
        : widget.selected
        ? JackColors.amber.withValues(alpha: 0.3)
        : JackColors.borderSubtle;

    return Semantics(
      button: true,
      selected: widget.selected,
      enabled: enabled,
      label: widget.count == null
          ? widget.label
          : '${widget.label}, ${widget.count} elementi',
      child: Material(
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
          canRequestFocus: enabled,
          borderRadius: BorderRadius.circular(JackRadius.full),
          hoverColor: Colors.transparent,
          focusColor: Colors.transparent,
          splashColor: JackColors.amber.withValues(alpha: 0.08),
          highlightColor: Colors.transparent,
          child: AnimatedContainer(
            duration: JackMotion.fast(context),
            height: 28,
            padding: const EdgeInsets.symmetric(
              horizontal: JackSpacing.m,
              vertical: JackSpacing.xs,
            ),
            decoration: BoxDecoration(
              color: background,
              borderRadius: BorderRadius.circular(JackRadius.full),
              border: Border.all(
                color: border,
                width: _focused ? JackBorderWidth.focus : JackBorderWidth.thin,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                if (widget.icon != null) ...<Widget>[
                  Icon(widget.icon, size: 12, color: foreground),
                  const SizedBox(width: JackSpacing.xs + 1),
                ],
                Text(
                  widget.label,
                  style: JackTypography.caption.copyWith(
                    color: foreground,
                    fontWeight: widget.selected
                        ? FontWeight.w600
                        : FontWeight.w400,
                  ),
                ),
                if (widget.count != null) ...<Widget>[
                  const SizedBox(width: JackSpacing.xs + 2),
                  Text(
                    '${widget.count}',
                    style: JackTypography.micro.copyWith(
                      color: widget.selected
                          ? JackColors.amber
                          : JackColors.textMuted,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Preference row with a title, description and switch.
class JackToggleRow extends StatelessWidget {
  const JackToggleRow({
    super.key,
    required this.title,
    required this.value,
    this.description,
    this.onChanged,
    this.locked = false,
    this.lockLabel,
  });

  final String title;
  final bool value;
  final String? description;
  final ValueChanged<bool>? onChanged;
  final bool locked;
  final String? lockLabel;

  @override
  Widget build(BuildContext context) {
    final effectiveOnChanged = locked ? null : onChanged;
    return MergeSemantics(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: JackSpacing.s),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Row(
                    children: <Widget>[
                      Flexible(
                        child: Text(
                          title,
                          style: JackTypography.titleSmall.copyWith(
                            fontSize: 13,
                            color: locked
                                ? JackColors.textSecondary
                                : JackColors.textPrimary,
                          ),
                        ),
                      ),
                      if (locked) ...<Widget>[
                        const SizedBox(width: JackSpacing.s),
                        const Icon(
                          JackIcons.lock,
                          size: 12,
                          color: JackColors.textMuted,
                        ),
                      ],
                    ],
                  ),
                  if (description != null || lockLabel != null) ...<Widget>[
                    const SizedBox(height: 3),
                    Text(
                      lockLabel ?? description!,
                      style: JackTypography.caption.copyWith(
                        color: JackColors.textMuted,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: JackSpacing.l),
            Switch(value: value, onChanged: effectiveOnChanged),
          ],
        ),
      ),
    );
  }
}

/// Labelled slider used by view controls.
class JackSliderRow extends StatelessWidget {
  const JackSliderRow({
    super.key,
    required this.label,
    required this.value,
    required this.onChanged,
    this.min = 0,
    this.max = 1,
    this.displayValue,
    this.width = 150,
  });

  final String label;
  final double value;
  final ValueChanged<double>? onChanged;
  final double min;
  final double max;
  final String? displayValue;
  final double width;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: <Widget>[
        Text(label, style: JackTypography.caption),
        SizedBox(
          width: width,
          child: Slider(
            value: value.clamp(min, max),
            min: min,
            max: max,
            onChanged: onChanged,
          ),
        ),
        SizedBox(
          width: 38,
          child: Text(
            displayValue ?? '${(value * 100).round()}%',
            textAlign: TextAlign.right,
            style: JackTypography.mono.copyWith(
              color: JackColors.textSecondary,
            ),
          ),
        ),
      ],
    );
  }
}
