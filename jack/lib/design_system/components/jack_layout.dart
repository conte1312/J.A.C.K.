/// Layout primitives: page headers, content padding, split views and side
/// panels. These keep the ten screens structurally consistent.
library;

import 'package:flutter/material.dart';

import '../tokens.dart';
import 'jack_badges.dart';
import 'jack_buttons.dart';

/// Standard screen header with eyebrow, title, description and actions.
class JackScreenHeader extends StatelessWidget {
  const JackScreenHeader({
    super.key,
    required this.eyebrow,
    required this.title,
    required this.description,
    this.actions = const <Widget>[],
    this.badges = const <Widget>[],
  });

  final String eyebrow;
  final String title;
  final String description;
  final List<Widget> actions;
  final List<Widget> badges;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 760;
        final titleBlock = Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            JackEyebrow(eyebrow),
            const SizedBox(height: JackSpacing.s),
            Wrap(
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: JackSpacing.m,
              runSpacing: JackSpacing.s,
              children: <Widget>[
                Text(title, style: JackTypography.headline),
                ...badges,
              ],
            ),
            const SizedBox(height: JackSpacing.s),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Text(description, style: JackTypography.bodySecondary),
            ),
          ],
        );

        if (actions.isEmpty) {
          return titleBlock;
        }

        if (compact) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              titleBlock,
              const SizedBox(height: JackSpacing.l),
              Wrap(
                spacing: JackSpacing.s,
                runSpacing: JackSpacing.s,
                children: actions,
              ),
            ],
          );
        }

        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(child: titleBlock),
            const SizedBox(width: JackSpacing.xl),
            Wrap(
              spacing: JackSpacing.s,
              runSpacing: JackSpacing.s,
              alignment: WrapAlignment.end,
              children: actions,
            ),
          ],
        );
      },
    );
  }
}

/// Page padding and maximum content width.
class JackScreenBody extends StatelessWidget {
  const JackScreenBody({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.fromLTRB(
      JackSizes.pagePadding,
      JackSpacing.xl,
      JackSizes.pagePadding,
      JackSizes.pagePadding,
    ),
    this.maxWidth = JackSizes.contentMaxWidth,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: padding,
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxWidth),
          child: child,
        ),
      ),
    );
  }
}

/// Master/detail layout: side-by-side on wide windows, single column with a
/// back affordance on narrow windows.
class JackSplitView extends StatelessWidget {
  const JackSplitView({
    super.key,
    required this.master,
    this.detail,
    this.onCloseDetail,
    this.detailWidth = JackSizes.detailPanelWidth,
    this.breakpoint = JackBreakpoints.detail,
  });

  final Widget master;
  final Widget? detail;
  final VoidCallback? onCloseDetail;
  final double detailWidth;
  final double breakpoint;

  @override
  Widget build(BuildContext context) {
    if (detail == null) {
      return master;
    }
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth >= breakpoint) {
          return Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              Expanded(child: master),
              const SizedBox(width: JackSpacing.l),
              SizedBox(width: detailWidth, child: detail),
            ],
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            _BackBar(onBack: onCloseDetail),
            const SizedBox(height: JackSpacing.m),
            Expanded(child: detail!),
          ],
        );
      },
    );
  }
}

class _BackBar extends StatelessWidget {
  const _BackBar({this.onBack});

  final VoidCallback? onBack;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: JackButton(
        label: 'Indietro',
        icon: JackIcons.arrowBack,
        variant: JackButtonVariant.ghost,
        size: JackButtonSize.small,
        onPressed: onBack,
      ),
    );
  }
}

/// Detail panel used beside a master list or inside a dialog.
class JackSidePanel extends StatelessWidget {
  const JackSidePanel({
    super.key,
    required this.title,
    required this.child,
    this.subtitle,
    this.onClose,
    this.actions = const <Widget>[],
    this.scrollable = true,
    this.padding = const EdgeInsets.all(JackSpacing.l),
  });

  final String title;
  final String? subtitle;
  final Widget child;
  final VoidCallback? onClose;
  final List<Widget> actions;
  final bool scrollable;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final body = scrollable
        ? SingleChildScrollView(padding: padding, child: child)
        : Padding(padding: padding, child: child);

    return Container(
      decoration: BoxDecoration(
        color: JackColors.surface,
        borderRadius: BorderRadius.circular(JackRadius.m),
        border: Border.all(
          color: JackColors.borderSubtle,
          width: JackBorderWidth.thin,
        ),
      ),
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
                        Text(subtitle!, style: JackTypography.caption),
                      ],
                    ],
                  ),
                ),
                ...actions,
                if (onClose != null)
                  JackIconButton(
                    icon: JackIcons.close,
                    tooltip: 'Chiudi pannello',
                    onPressed: onClose,
                  ),
              ],
            ),
          ),
          const Divider(),
          Expanded(child: body),
        ],
      ),
    );
  }
}
