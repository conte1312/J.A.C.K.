/// Real backend health state for J.A.C.K. 2.0.
///
/// The controller performs a genuine HTTP check against the local FastAPI
/// backend (`GET /health` and `GET /api/v2/info`). It never fabricates an
/// online state: when the backend is unreachable the snapshot is offline.
library;

import 'dart:async';

import 'package:flutter/widgets.dart';

import '../services/api_client.dart';

/// Immutable result of one backend check.
class JackBackendSnapshot {
  const JackBackendSnapshot({
    required this.online,
    required this.checkedAt,
    this.version,
    this.product,
    this.bind,
    this.latency,
    this.error,
  });

  factory JackBackendSnapshot.online({
    required DateTime checkedAt,
    required Duration latency,
    String? version,
    String? product,
    String? bind,
  }) {
    return JackBackendSnapshot(
      online: true,
      checkedAt: checkedAt,
      latency: latency,
      version: version,
      product: product,
      bind: bind,
    );
  }

  factory JackBackendSnapshot.offline({
    required DateTime checkedAt,
    required Duration latency,
    required String error,
  }) {
    return JackBackendSnapshot(
      online: false,
      checkedAt: checkedAt,
      latency: latency,
      error: error,
    );
  }

  final bool online;
  final DateTime checkedAt;
  final String? version;
  final String? product;
  final String? bind;
  final Duration? latency;
  final String? error;
}

/// One entry in the in-session check history.
class JackBackendCheck {
  const JackBackendCheck({required this.at, required this.snapshot});

  final DateTime at;
  final JackBackendSnapshot snapshot;
}

/// Abstraction used by the UI; tests inject a deterministic fake.
abstract interface class JackBackendReader {
  Future<JackBackendSnapshot> check();
}

/// Genuine HTTP reader against the loopback backend.
class JackBackendHttpReader implements JackBackendReader {
  JackBackendHttpReader({
    JackApiClient? client,
    this.timeout = const Duration(seconds: 3),
  }) : _client = client ?? JackApiClient();

  final JackApiClient _client;
  final Duration timeout;

  @override
  Future<JackBackendSnapshot> check() async {
    final stopwatch = Stopwatch()..start();
    try {
      final health = await _client.get('/health').timeout(timeout);
      if (health['status'] != 'ok') {
        stopwatch.stop();
        return JackBackendSnapshot.offline(
          checkedAt: DateTime.now(),
          latency: stopwatch.elapsed,
          error: 'Il backend ha risposto ma lo stato non è valido.',
        );
      }
      final info = await _client.get('/api/v2/info').timeout(timeout);
      stopwatch.stop();
      return JackBackendSnapshot.online(
        checkedAt: DateTime.now(),
        latency: stopwatch.elapsed,
        version: info['version']?.toString(),
        product: info['product']?.toString(),
        bind: info['bind']?.toString(),
      );
    } on TimeoutException {
      stopwatch.stop();
      return JackBackendSnapshot.offline(
        checkedAt: DateTime.now(),
        latency: stopwatch.elapsed,
        error: 'Timeout della verifica (${timeout.inSeconds}s).',
      );
    } on BackendUnavailableException {
      stopwatch.stop();
      return JackBackendSnapshot.offline(
        checkedAt: DateTime.now(),
        latency: stopwatch.elapsed,
        error: 'Backend non raggiungibile su $kBackendBaseUrl.',
      );
    } on ApiErrorException catch (error) {
      stopwatch.stop();
      return JackBackendSnapshot.offline(
        checkedAt: DateTime.now(),
        latency: stopwatch.elapsed,
        error: 'Il backend ha risposto ${error.statusCode}.',
      );
    } catch (_) {
      stopwatch.stop();
      return JackBackendSnapshot.offline(
        checkedAt: DateTime.now(),
        latency: stopwatch.elapsed,
        error: 'Verifica non riuscita.',
      );
    }
  }
}

/// Observable backend status with an in-session history of checks.
class BackendStatusController extends ChangeNotifier {
  BackendStatusController({JackBackendReader? reader})
    : _reader = reader ?? JackBackendHttpReader();

  final JackBackendReader _reader;
  JackBackendSnapshot? _snapshot;
  bool _checking = false;
  final List<JackBackendCheck> _history = <JackBackendCheck>[];

  JackBackendSnapshot? get snapshot => _snapshot;
  bool get checking => _checking;
  List<JackBackendCheck> get history =>
      List<JackBackendCheck>.unmodifiable(_history);
  bool get hasChecked => _snapshot != null;

  Future<void> check() async {
    if (_checking) {
      return;
    }
    _checking = true;
    notifyListeners();
    JackBackendSnapshot snapshot;
    try {
      snapshot = await _reader.check();
    } catch (_) {
      snapshot = JackBackendSnapshot.offline(
        checkedAt: DateTime.now(),
        latency: Duration.zero,
        error: 'Verifica non riuscita.',
      );
    }
    _snapshot = snapshot;
    _checking = false;
    _history.insert(
      0,
      JackBackendCheck(at: snapshot.checkedAt, snapshot: snapshot),
    );
    if (_history.length > 8) {
      _history.removeLast();
    }
    notifyListeners();
  }
}

/// Provides the backend controller to the widget tree.
class JackBackendScope extends InheritedNotifier<BackendStatusController> {
  const JackBackendScope({
    super.key,
    required BackendStatusController controller,
    required super.child,
  }) : super(notifier: controller);

  static BackendStatusController of(BuildContext context) {
    final scope = context
        .dependOnInheritedWidgetOfExactType<JackBackendScope>();
    assert(scope != null, 'JackBackendScope is missing above this widget.');
    return scope!.notifier!;
  }
}
