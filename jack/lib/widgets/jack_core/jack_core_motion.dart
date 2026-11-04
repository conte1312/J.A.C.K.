import 'dart:math' as math;

import 'jack_core_state.dart';

enum JackCoreIntensity { low, medium, high }

class JackCoreOrbit {
  const JackCoreOrbit({
    required this.radius,
    required this.opacity,
    required this.tiltX,
    required this.tiltY,
    required this.speed,
  });

  final double radius;
  final double opacity;
  final double tiltX;
  final double tiltY;
  final double speed;
}

/// The radius/opacity values are taken directly from blueprint §6.
/// Plane tilts and speed multipliers are local rendering defaults.
const jackCoreDefaultOrbits = <JackCoreOrbit>[
  JackCoreOrbit(
    radius: 1.16,
    opacity: 0.30,
    tiltX: 0.42,
    tiltY: -0.18,
    speed: 0.72,
  ),
  JackCoreOrbit(
    radius: 1.34,
    opacity: 0.20,
    tiltX: -0.66,
    tiltY: 0.24,
    speed: -0.46,
  ),
  JackCoreOrbit(
    radius: 1.03,
    opacity: 0.24,
    tiltX: 0.88,
    tiltY: 0.62,
    speed: 0.56,
  ),
  JackCoreOrbit(
    radius: 1.52,
    opacity: 0.13,
    tiltX: -0.34,
    tiltY: -0.82,
    speed: -0.34,
  ),
];

class JackCoreMotionProfile {
  const JackCoreMotionProfile({
    required this.spin,
    required this.glow,
    required this.breathe,
    required this.cluster,
    required this.scan,
    required this.pulse,
    required this.jitter,
    required this.dim,
  });

  final double spin;
  final double glow;
  final double breathe;
  final double cluster;
  final double scan;
  final double pulse;
  final double jitter;
  final double dim;

  /// The blueprint gives endpoint pairs for waiting/executing but does not
  /// name their axes. This implementation interprets each pair as spin/glow.
  /// All other profiles below are conservative implementation defaults, not
  /// official Base44 values.
  static const profiles = <JackCognitiveState, JackCoreMotionProfile>{
    JackCognitiveState.idle: JackCoreMotionProfile(
      spin: 0.045,
      glow: 0.32,
      breathe: 0.10,
      cluster: 0.06,
      scan: 0.00,
      pulse: 0.08,
      jitter: 0.00,
      dim: 0.00,
    ),
    JackCognitiveState.listening: JackCoreMotionProfile(
      spin: 0.060,
      glow: 0.48,
      breathe: 0.19,
      cluster: 0.10,
      scan: 0.14,
      pulse: 0.24,
      jitter: 0.00,
      dim: 0.00,
    ),
    JackCognitiveState.understanding: JackCoreMotionProfile(
      spin: 0.075,
      glow: 0.50,
      breathe: 0.16,
      cluster: 0.20,
      scan: 0.34,
      pulse: 0.17,
      jitter: 0.00,
      dim: 0.00,
    ),
    JackCognitiveState.retrieving: JackCoreMotionProfile(
      spin: 0.090,
      glow: 0.58,
      breathe: 0.16,
      cluster: 0.42,
      scan: 0.42,
      pulse: 0.26,
      jitter: 0.00,
      dim: 0.00,
    ),
    JackCognitiveState.planning: JackCoreMotionProfile(
      spin: 0.082,
      glow: 0.54,
      breathe: 0.20,
      cluster: 0.52,
      scan: 0.24,
      pulse: 0.22,
      jitter: 0.00,
      dim: 0.00,
    ),
    JackCognitiveState.executing: JackCoreMotionProfile(
      spin: 0.22,
      glow: 0.88,
      breathe: 0.28,
      cluster: 0.42,
      scan: 0.68,
      pulse: 0.48,
      jitter: 0.00,
      dim: 0.00,
    ),
    JackCognitiveState.responding: JackCoreMotionProfile(
      spin: 0.13,
      glow: 0.68,
      breathe: 0.32,
      cluster: 0.25,
      scan: 0.32,
      pulse: 0.58,
      jitter: 0.00,
      dim: 0.00,
    ),
    JackCognitiveState.saving: JackCoreMotionProfile(
      spin: 0.072,
      glow: 0.62,
      breathe: 0.22,
      cluster: 0.30,
      scan: 0.14,
      pulse: 0.36,
      jitter: 0.00,
      dim: 0.00,
    ),
    JackCognitiveState.waiting: JackCoreMotionProfile(
      spin: 0.028,
      glow: 0.44,
      breathe: 0.07,
      cluster: 0.04,
      scan: 0.00,
      pulse: 0.06,
      jitter: 0.00,
      dim: 0.03,
    ),
    JackCognitiveState.error: JackCoreMotionProfile(
      spin: 0.105,
      glow: 0.66,
      breathe: 0.16,
      cluster: 0.10,
      scan: 0.18,
      pulse: 0.20,
      jitter: 1.00,
      dim: 0.08,
    ),
  };

  static JackCoreMotionProfile forState(JackCognitiveState state) =>
      profiles[state]!;

  JackCoreMotionProfile scaled(JackCoreIntensity intensity) {
    final scale = switch (intensity) {
      JackCoreIntensity.low => 0.72,
      JackCoreIntensity.medium => 1.0,
      JackCoreIntensity.high => 1.18,
    };
    return JackCoreMotionProfile(
      spin: spin,
      glow: (glow * scale).clamp(0.0, 1.0),
      breathe: (breathe * scale).clamp(0.0, 0.45),
      cluster: (cluster * scale).clamp(0.0, 1.0),
      scan: (scan * scale).clamp(0.0, 1.0),
      pulse: (pulse * scale).clamp(0.0, 1.0),
      jitter: (jitter * scale).clamp(0.0, 1.0),
      dim: dim,
    );
  }

  static JackCoreMotionProfile lerp(
    JackCoreMotionProfile a,
    JackCoreMotionProfile b,
    double t,
  ) => JackCoreMotionProfile(
    spin: _mix(a.spin, b.spin, t),
    glow: _mix(a.glow, b.glow, t),
    breathe: _mix(a.breathe, b.breathe, t),
    cluster: _mix(a.cluster, b.cluster, t),
    scan: _mix(a.scan, b.scan, t),
    pulse: _mix(a.pulse, b.pulse, t),
    jitter: _mix(a.jitter, b.jitter, t),
    dim: _mix(a.dim, b.dim, t),
  );

  static double _mix(double a, double b, double t) {
    final clamped = t.clamp(0.0, 1.0);
    final eased = clamped * clamped * (3 - 2 * clamped);
    return a + (b - a) * eased;
  }

  double sample(double phase, double offset, {double frequency = 1}) =>
      math.sin(phase * frequency + offset);
}
