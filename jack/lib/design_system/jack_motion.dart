/// Motion helpers for J.A.C.K. 2.0.
///
/// Every animation in the app must respect the operating-system "reduce
/// motion" preference (surfaced by [MediaQuery.disableAnimations]) and the
/// in-app preference managed by [JackPreferences].
library;

import 'package:flutter/widgets.dart';

import 'tokens.dart';

/// Central access to motion durations that respect reduced-motion settings.
class JackMotion {
  JackMotion._();

  /// Whether non-essential animations should be disabled.
  static bool reduced(BuildContext context) {
    return MediaQuery.maybeOf(context)?.disableAnimations ?? false;
  }

  /// Returns [base], or [Duration.zero] when motion is reduced.
  static Duration duration(BuildContext context, Duration base) {
    return reduced(context) ? Duration.zero : base;
  }

  static Duration fast(BuildContext context) =>
      duration(context, JackDuration.fast);

  static Duration normal(BuildContext context) =>
      duration(context, JackDuration.normal);

  static Duration slow(BuildContext context) =>
      duration(context, JackDuration.slow);
}
