/// J.A.C.K. 2.0 design tokens.
///
/// Single source of truth for every visual value used by the application.
/// Components and screens reference these tokens instead of hard-coded
/// values, so the ten screens share one coherent visual language.
///
/// Identity: graphite and black surfaces, amber/gold primary accent,
/// cyan secondary accent, translucent layers, thin borders and controlled
/// motion. Premium, quiet, Apple-inspired — not a generic admin dashboard.
library;

import 'package:flutter/material.dart';

/// Core palette — primary source of all color values.
/// Every screen and component should reference JackColors rather than
/// hard‑coded constants; this keeps the ten screens sharing one visual language.
class JackColors {
  JackColors._();

  // Backgrounds and surfaces.
  static const Color backgroundDeep = Color(0xFF060608);
  static const Color background = Color(0xFF09090B);
  static const Color surface = Color(0xFF101114);
  static const Color surfaceElevated = Color(0xFF14161A);
  static const Color surfaceCard = Color(0xFF17191E);
  static const Color surfaceOverlay = Color(0xFF1C1F25);
  static const Color surfaceHover = Color(0xFF1A1D22);
  static const Color surfaceTranslucent = Color(0xE614161A);

  // Compatibility aliases used by the M1 theme layer.
  static const Color surfaceBackground = background;

  // Borders.
  static const Color borderSubtle = Color(0xFF23252B);
  static const Color border = Color(0xFF2D3037);
  static const Color borderStrong = Color(0xFF3A3E47);
  static const Color borderFocus = Color(0xCC6FD8E8);

  // Text.
  static const Color textPrimary = Color(0xFFF3F1EC);
  static const Color textSecondary = Color(0xFFB0ADA5);
  static const Color textMuted = Color(0xFF8A877F);
  static const Color textDisabled = Color(0xFF5E5C57);

  // Brand: amber / gold.
  static const Color amber = Color(0xFFF0B45C);
  static const Color amberBright = Color(0xFFFFC978);
  static const Color amberDeep = Color(0xFFC98D3A);
  static const Color amberSoft = Color(0x1FF0B45C);
  static const Color gold = Color(0xFFFFD98F);

  // Secondary accent: cyan.
  static const Color cyan = Color(0xFF6FD8E8);
  static const Color cyanBright = Color(0xFF9AEAF4);
  static const Color cyanSoft = Color(0x1A6FD8E8);

  // Semantic status.
  static const Color success = Color(0xFF5BD6A0);
  static const Color warning = Color(0xFFF0B45C);
  static const Color error = Color(0xFFFF7A7A);
  static const Color info = Color(0xFF6FD8E8);

  // Selection and overlays.
  static const Color selection = Color(0x1FF0B45C);
  static const Color scrim = Color(0xCC050506);
  static const Color highlight = Color(0x0DFFFFFF);
}

/// Spacing scale (4pt rhythm).
class JackSpacing {
  JackSpacing._();

  static const double xxs = 2;
  static const double xs = 4;
  static const double s = 8;
  static const double m = 12;
  static const double l = 16;
  static const double xl = 24;
  static const double xxl = 32;
  static const double xxxl = 48;
}

/// Corner radius scale.
class JackRadius {
  JackRadius._();

  static const double xs = 6;
  static const double s = 8;
  static const double m = 12;
  static const double l = 16;
  static const double xl = 20;
  static const double xxl = 28;
  static const double full = 999;
}

/// Border widths.
class JackBorderWidth {
  JackBorderWidth._();

  static const double thin = 1;
  static const double focus = 1.5;
  static const double accent = 2;
}

/// Controlled elevation. J.A.C.K. prefers borders and surfaces over heavy
/// drop shadows. All values are expressed in logical pixels.
class JackShadows {
  JackShadows._();

  /// A small shadow for elevated interactive elements.
  static const BoxShadow floating = BoxShadow(
    color: Color(0x26000000),
    offset: Offset(0, 2),
    blurRadius: 4,
    spreadRadius: 0,
  );

  /// A medium shadow for cards and modals.
  static const BoxShadow medium = BoxShadow(
    color: Color(0x32000000),
    offset: Offset(0, 4),
    blurRadius: 8,
    spreadRadius: 0,
  );

  /// A large shadow for modal backdrops.
  static const BoxShadow large = BoxShadow(
    color: Color(0x40000000),
    offset: Offset(0, 8),
    blurRadius: 16,
    spreadRadius: 0,
  );
}

/// Typography scale. All text styles use the J.A.C.K. color system.
class JackTypography {
  JackTypography._();

  /// Display large - page titles, section headers.
  static const TextStyle display = TextStyle(
    fontSize: 32,
    fontWeight: FontWeight.w400,
    letterSpacing: -0.8,
    color: JackColors.textPrimary,
  );

  /// Headline medium - section titles.
  static const TextStyle headline = TextStyle(
    fontSize: 24,
    fontWeight: FontWeight.w500,
    letterSpacing: -0.45,
    color: JackColors.textPrimary,
  );

  /// Title large - page titles.
  static const TextStyle title = TextStyle(
    fontSize: 20,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.2,
    color: JackColors.textPrimary,
  );

  /// Title medium - card section titles.
  static const TextStyle titleSmall = TextStyle(
    fontSize: 16,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.1,
    color: JackColors.textPrimary,
  );

  /// Label - button and widget labels.
  static const TextStyle label = TextStyle(
    fontSize: 13,
    fontWeight: FontWeight.w500,
    color: JackColors.textPrimary,
  );

  /// Body body - primary body text.
  static const TextStyle body = TextStyle(
    fontSize: 16,
    fontWeight: FontWeight.w400,
    height: 1.5,
    color: JackColors.textPrimary,
  );

  /// Body secondary - secondary body text.
  static const TextStyle bodySecondary = TextStyle(
    fontSize: 13,
    fontWeight: FontWeight.w400,
    height: 1.5,
    color: JackColors.textSecondary,
  );

  /// Caption - meta information, small text.
  static const TextStyle caption = TextStyle(
    fontSize: 11,
    fontWeight: FontWeight.w400,
    height: 1.4,
    color: JackColors.textMuted,
  );

  /// Micro - tiny text, hints, metadata.
  static const TextStyle micro = TextStyle(
    fontSize: 9,
    fontWeight: FontWeight.w400,
    color: JackColors.textMuted,
  );

  /// Eyebrow - uppercase section labels.
  static const TextStyle eyebrow = TextStyle(
    fontSize: 10,
    fontWeight: FontWeight.w600,
    letterSpacing: 1.5,
    color: JackColors.textSecondary,
  );

  /// Body large - 18pt body.
  static const TextStyle bodyLarge = TextStyle(
    fontSize: 18,
    fontWeight: FontWeight.w500,
    height: 1.5,
    color: JackColors.textPrimary,
  );

  /// Body medium - 15pt body.
  static const TextStyle bodyMedium = TextStyle(
    fontSize: 15,
    fontWeight: FontWeight.w400,
    height: 1.5,
    color: JackColors.textSecondary,
  );

  /// Mono-spaced family for code and logs.
  static const TextStyle mono = TextStyle(
    fontFamily: 'Menlo',
    fontFamilyFallback: <String>['SF Mono', 'Consolas', 'monospace'],
    fontSize: 12,
    height: 1.4,
    fontWeight: FontWeight.w400,
    color: JackColors.textSecondary,
  );
}

/// Icon set for J.A.C.K. components.
class JackIcons {
  JackIcons._();

  /// Search magnifier.
  static const IconData search = Icons.search;

  /// Close cross mark.
  static const IconData close = Icons.close;

  /// Information circle.
  static const IconData info = Icons.info;

  /// Delete/trash.
  static const IconData trash = Icons.delete;

  /// Warning triangle.
  static const IconData warning = Icons.warning;

  /// Refresh arrow.
  static const IconData refresh = Icons.refresh;

  /// Success check mark.
  static const IconData success = Icons.check;

  /// Schedule/calendar.
  static const IconData schedule = Icons.calendar_today;

  /// Lock secured.
  static const IconData lock = Icons.lock;

  /// Arrow back.
  static const IconData arrowBack = Icons.arrow_back;

  /// Arrow forward.
  static const IconData arrowForward = Icons.arrow_forward;

  /// Menu.
  static const IconData menu = Icons.menu;

  /// More horizontal dots.
  static const IconData more_vert = Icons.more_vert;

  /// Demo/catalog.
  static const IconData demo = Icons.article;

  /// Mono font.
  static const IconData mono = Icons.accessibility;

  /// Offline status.
  static const IconData offline = Icons.cloud_off;

  /// Conversations.
  static const IconData conversations = Icons.forum;

  /// Memory.
  static const IconData memory = Icons.memory;

  /// Exploration.
  static const IconData exploration = Icons.explore;

  /// Planning.
  static const IconData planning = Icons.event_note;

  /// Modules.
  static const IconData modules = Icons.widgets;

  /// AI Hub.
  static const IconData aiHub = Icons.psychology;

  /// Agency.
  static const IconData agency = Icons.groups;

  /// Settings.
  static const IconData settings = Icons.settings;

  /// Profile.
  static const IconData profile = Icons.person;

  /// System status.
  static const IconData systemStatus = Icons.monitor_heart;
}

/// Button and layout sizes.
class JackSizes {
  JackSizes._();

  // Input heights.
  static const double inputHeight = 40;
  static const double inputHeightLarge = 48;

  // Button heights.
  static const double buttonHeight = 36;
  static const double buttonHeightLarge = 48;
  static const double iconButtonSize = 32;

  // Layout dimensions.
  static const double pagePadding = 24;
  static const double contentMaxWidth = 600;
  static const double detailPanelWidth = 300;
  static const double avatarSmall = 24;
  static const double avatarMedium = 40;
}

/// Transition curves.
class JackCurves {
  JackCurves._();

  /// Standard easing curve.
  static const Curve standard = Curves.ease;

  /// Fast entry, slow exit.
  static const Curve fastSlow = Curves.easeOut;

  /// Slow entry, fast exit.
  static const Curve slowFast = Curves.easeIn;

  /// Linear transition.
  static const Curve linear = Curves.linear;
}

/// Breakpoints for responsive layout.
class JackBreakpoints {
  JackBreakpoints._();

  static const double mobile = 360;
  static const double tablet = 600;
  static const double desktop = 1024;

  /// Breakpoint for detail panels (tablet size).
  static const double detail = tablet;
}

/// Duration constants for J.A.C.K. motion.
class JackDuration {
  JackDuration._();

  static const Duration fast = Duration(milliseconds: 150);
  static const Duration normal = Duration(milliseconds: 250);
  static const Duration slow = Duration(milliseconds: 400);
}

/// Spacing scale (4pt rhythm).