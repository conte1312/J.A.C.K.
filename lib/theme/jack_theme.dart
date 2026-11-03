import 'package:flutter/material.dart';

abstract final class JackPalette {
  static const canvas = Color(0xFF0D0F11);
  static const panel = Color(0xFF151719);
  static const panelRaised = Color(0xFF1D2023);
  static const panelHover = Color(0xFF25282B);
  static const border = Color(0xFF2C2F33);
  static const borderSoft = Color(0xFF24272A);
  static const text = Color(0xFFE5E2DE);
  static const muted = Color(0xFF88898B);
  static const dim = Color(0xFF5B5D60);
  static const amber = Color(0xFFEA9229);
  static const amberSoft = Color(0xFF9E6128);
  static const cyan = Color(0xFF67C8CD);
  static const blue = Color(0xFF77B2DE);
  static const lavender = Color(0xFF9BAFCC);
  static const green = Color(0xFF7FC69D);
}

abstract final class JackTheme {
  static final dark = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    scaffoldBackgroundColor: JackPalette.canvas,
    colorScheme:
        ColorScheme.fromSeed(
          seedColor: JackPalette.amber,
          brightness: Brightness.dark,
        ).copyWith(
          primary: JackPalette.amber,
          secondary: JackPalette.cyan,
          surface: JackPalette.panel,
          onSurface: JackPalette.text,
        ),
    textTheme: ThemeData.dark().textTheme.apply(
      bodyColor: JackPalette.text,
      displayColor: JackPalette.text,
    ),
    visualDensity: VisualDensity.standard,
    splashFactory: InkSparkle.splashFactory,
  );
}
