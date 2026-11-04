import 'package:flutter/material.dart';

import '../../theme/jack_theme.dart';

/// Core colors aligned to the HSL tokens in the Base44 blueprint.
abstract final class JackCorePalette {
  static const graphite = Color(0xFF0D0F12); // HSL 218 18% 6%
  static const surface = JackPalette.panel;
  static const foreground = Color(0xFFEFECE6); // HSL 38 22% 92%
  static const amber = Color(0xFFF2952C); // HSL 32 88% 56%
  static const amberSoft = Color(0xFFF0BB75); // HSL 34 80% 70%
  static const amberDeep = Color(0xFFA7531B); // HSL 24 72% 38%
  static const gold = Color(0xFFF3D286); // HSL 42 82% 74%
  static const glacier = Color(0xFF61C4D1); // HSL 187 55% 60%
  static const abyss = Color(0xFF244061); // HSL 212 46% 26%
  static const hairline = Color(0xFF2D3139); // HSL 218 12% 20%
  static const saved = JackPalette.green;
  static const retrieved = JackPalette.blue;
  static const inferred = JackPalette.dim;
  static const error = Color(0xFFD97872);
}
