/// Banners, dialogs and snackbars shared by the screens.
library;

import 'package:flutter/material.dart';

import '../jack_tone.dart';
import '../tokens.dart';
import 'jack_badges.dart';

/// Inline banner used for demo data, planned capabilities and warnings.
class JackNotice extends StatelessWidget {
  const JackNotice({
    super.key,
    required this.title,
    required this.message,
    this.tone = JackTone.info,
    this.icon,
    this.action,
  });

  final String title;
  final String message;
  final JackTone tone;
  final IconData? icon;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: JackSpacing.l,
        vertical: JackSpacing.m,
      ),
      decoration: BoxDecoration(
        color: tone.background,
        borderRadius: BorderRadius.circular(JackRadius.s),
        border: Border.all(color: tone.border, width: JackBorderWidth.thin),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.only(top: 1),
            child: Icon(icon ?? JackIcons.info, size: 15, color: tone.color),
          ),
          const SizedBox(width: JackSpacing.m),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Text(
                  title,
                  style: JackTypography.label.copyWith(color: tone.color),
                ),
                const SizedBox(height: 2),
                Text(message, style: JackTypography.caption),
              ],
            ),
          ),
          if (action != null) ...<Widget>[
            const SizedBox(width: JackSpacing.m),
            action!,
          ],
        ],
      ),
    );
  }
}

/// Banner preset for demonstration datasets.
class JackDemoNotice extends StatelessWidget {
  const JackDemoNotice({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return JackNotice(
      title: 'Dati dimostrativi',
      message: message,
      tone: JackTone.amber,
      icon: JackIcons.demo,
    );
  }
}

/// Explains that an action will be enabled in a later milestone.
Future<void> showJackInfoDialog(
  BuildContext context, {
  required String title,
  required String message,
  String? milestone,
  IconData icon = JackIcons.info,
  String closeLabel = 'Ho capito',
}) {
  return showDialog<void>(
    context: context,
    builder: (dialogContext) {
      return AlertDialog(
        icon: Icon(icon, color: JackColors.cyan, size: 22),
        title: Text(title, textAlign: TextAlign.center),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Text(message, textAlign: TextAlign.center),
            if (milestone != null) ...<Widget>[
              const SizedBox(height: JackSpacing.l),
              JackMilestoneBadge(milestone: milestone),
            ],
          ],
        ),
        actionsAlignment: MainAxisAlignment.center,
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: Text(closeLabel),
          ),
        ],
      );
    },
  );
}

/// Shows arbitrary content inside a floating, themed panel.
Future<void> showJackPanelDialog(
  BuildContext context, {
  required String title,
  required Widget child,
  String? subtitle,
  double width = 420,
  double height = 560,
}) {
  return showDialog<void>(
    context: context,
    builder: (dialogContext) {
      return Dialog(
        insetPadding: const EdgeInsets.all(JackSpacing.xl),
        backgroundColor: JackColors.surfaceElevated,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(JackRadius.l),
          side: const BorderSide(
            color: JackColors.border,
            width: JackBorderWidth.thin,
          ),
        ),
        child: SizedBox(
          width: width,
          height: height,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  JackSpacing.l,
                  JackSpacing.m,
                  JackSpacing.s,
                  JackSpacing.m,
                ),
                child: Row(
                  children: <Widget>[
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: <Widget>[
                          Text(title, style: JackTypography.titleSmall),
                          if (subtitle != null) ...<Widget>[
                            const SizedBox(height: 2),
                            Text(subtitle, style: JackTypography.caption),
                          ],
                        ],
                      ),
                    ),
                    IconButton(
                      tooltip: 'Chiudi',
                      onPressed: () => Navigator.of(dialogContext).pop(),
                      icon: const Icon(JackIcons.close, size: 18),
                    ),
                  ],
                ),
              ),
              const Divider(),
              Expanded(child: child),
            ],
          ),
        ),
      );
    },
  );
}

/// Themed floating snackbar.
void showJackSnack(
  BuildContext context,
  String message, {
  JackTone tone = JackTone.neutral,
  IconData? icon,
}) {
  final messenger = ScaffoldMessenger.maybeOf(context);
  if (messenger == null) {
    return;
  }
  messenger
    ..hideCurrentSnackBar()
    ..showSnackBar(
      SnackBar(
        content: Row(
          children: <Widget>[
            Icon(icon ?? JackIcons.info, size: 15, color: tone.color),
            const SizedBox(width: JackSpacing.m),
            Expanded(
              child: Text(
                message,
                style: JackTypography.caption.copyWith(
                  color: JackColors.textPrimary,
                ),
              ),
            ),
          ],
        ),
      ),
    );
}
