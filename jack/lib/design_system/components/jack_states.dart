/// Shared loading, empty, error and unavailable states.
library;

import 'package:flutter/material.dart';

import '../tokens.dart';
import 'jack_badges.dart';

/// Centered empty state with an optional action.
class JackEmptyState extends StatelessWidget {
  const JackEmptyState({
    super.key,
    required this.title,
    required this.message,
    this.icon = Icons.inbox_outlined,
    this.action,
    this.compact = false,
  });

  final String title;
  final String message;
  final IconData icon;
  final Widget? action;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 360),
        child: Padding(
          padding: EdgeInsets.all(compact ? JackSpacing.l : JackSpacing.xxl),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Container(
                width: compact ? 40 : 52,
                height: compact ? 40 : 52,
                decoration: BoxDecoration(
                  color: JackColors.surface,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: JackColors.borderSubtle,
                    width: JackBorderWidth.thin,
                  ),
                ),
                child: Icon(
                  icon,
                  size: compact ? 18 : 22,
                  color: JackColors.textMuted,
                ),
              ),
              const SizedBox(height: JackSpacing.l),
              Text(
                title,
                textAlign: TextAlign.center,
                style: JackTypography.titleSmall,
              ),
              const SizedBox(height: JackSpacing.s),
              Text(
                message,
                textAlign: TextAlign.center,
                style: JackTypography.bodySecondary,
              ),
              if (action != null) ...<Widget>[
                const SizedBox(height: JackSpacing.l),
                action!,
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Compact loading indicator with a message.
class JackLoadingState extends StatelessWidget {
  const JackLoadingState({
    super.key,
    this.message = 'Caricamento…',
    this.compact = false,
  });

  final String message;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(compact ? JackSpacing.l : JackSpacing.xxl),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(width: JackSpacing.m),
            Text(message, style: JackTypography.bodySecondary),
          ],
        ),
      ),
    );
  }
}

/// Error state with an optional retry action.
class JackErrorState extends StatelessWidget {
  const JackErrorState({
    super.key,
    required this.title,
    required this.message,
    this.onRetry,
    this.retryLabel = 'Riprova',
    this.compact = false,
  });

  final String title;
  final String message;
  final VoidCallback? onRetry;
  final String retryLabel;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 380),
        child: Padding(
          padding: EdgeInsets.all(compact ? JackSpacing.l : JackSpacing.xxl),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Container(
                width: compact ? 40 : 52,
                height: compact ? 40 : 52,
                decoration: BoxDecoration(
                  color: JackColors.error.withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: JackColors.error.withValues(alpha: 0.3),
                    width: JackBorderWidth.thin,
                  ),
                ),
                child: Icon(
                  JackIcons.warning,
                  size: compact ? 18 : 22,
                  color: JackColors.error,
                ),
              ),
              const SizedBox(height: JackSpacing.l),
              Text(
                title,
                textAlign: TextAlign.center,
                style: JackTypography.titleSmall,
              ),
              const SizedBox(height: JackSpacing.s),
              Text(
                message,
                textAlign: TextAlign.center,
                style: JackTypography.bodySecondary,
              ),
              if (onRetry != null) ...<Widget>[
                const SizedBox(height: JackSpacing.l),
                OutlinedButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(JackIcons.refresh, size: 15),
                  label: Text(retryLabel),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Honest "not available yet" state used until the dedicated milestone ships.
class JackUnavailableState extends StatelessWidget {
  const JackUnavailableState({
    super.key,
    required this.title,
    required this.message,
    required this.milestone,
    this.icon = JackIcons.schedule,
    this.compact = false,
  });

  final String title;
  final String message;
  final String milestone;
  final IconData icon;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: Padding(
          padding: EdgeInsets.all(compact ? JackSpacing.l : JackSpacing.xxl),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Container(
                width: compact ? 40 : 52,
                height: compact ? 40 : 52,
                decoration: BoxDecoration(
                  color: JackColors.cyanSoft,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: JackColors.cyan.withValues(alpha: 0.3),
                    width: JackBorderWidth.thin,
                  ),
                ),
                child: Icon(
                  icon,
                  size: compact ? 18 : 22,
                  color: JackColors.cyan,
                ),
              ),
              const SizedBox(height: JackSpacing.l),
              Text(
                title,
                textAlign: TextAlign.center,
                style: JackTypography.titleSmall,
              ),
              const SizedBox(height: JackSpacing.s),
              Text(
                message,
                textAlign: TextAlign.center,
                style: JackTypography.bodySecondary,
              ),
              const SizedBox(height: JackSpacing.m),
              JackMilestoneBadge(milestone: milestone),
            ],
          ),
        ),
      ),
    );
  }
}
