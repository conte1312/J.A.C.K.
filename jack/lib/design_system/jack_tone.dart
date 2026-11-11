/// Semantic colour tones shared by badges, notices and status indicators.
library;

import 'package:flutter/material.dart';

import 'tokens.dart';

/// Semantic tone for badges, notices and status elements.
enum JackTone { neutral, amber, cyan, success, warning, error, info }

extension JackToneColors on JackTone {
  /// Foreground colour of the tone.
  Color get color => switch (this) {
    JackTone.neutral => JackColors.textSecondary,
    JackTone.amber => JackColors.amber,
    JackTone.cyan => JackColors.cyan,
    JackTone.success => JackColors.success,
    JackTone.warning => JackColors.warning,
    JackTone.error => JackColors.error,
    JackTone.info => JackColors.info,
  };

  /// Tinted background used by badges and notices.
  Color get background => color.withValues(alpha: 0.11);

  /// Border colour used by badges and notices.
  Color get border => color.withValues(alpha: 0.32);
}

/// Connection / availability state.
enum JackStatus { online, offline, checking, pending, unavailable }

extension JackStatusTone on JackStatus {
  JackTone get tone => switch (this) {
    JackStatus.online => JackTone.success,
    JackStatus.offline => JackTone.error,
    JackStatus.checking => JackTone.cyan,
    JackStatus.pending => JackTone.amber,
    JackStatus.unavailable => JackTone.neutral,
  };

  String get defaultLabel => switch (this) {
    JackStatus.online => 'Online',
    JackStatus.offline => 'Offline',
    JackStatus.checking => 'Verifica…',
    JackStatus.pending => 'In attesa',
    JackStatus.unavailable => 'Non disponibile',
  };

  IconData get icon => switch (this) {
    JackStatus.online => JackIcons.success,
    JackStatus.offline => JackIcons.offline,
    JackStatus.checking => JackIcons.refresh,
    JackStatus.pending => JackIcons.schedule,
    JackStatus.unavailable => JackIcons.lock,
  };
}
