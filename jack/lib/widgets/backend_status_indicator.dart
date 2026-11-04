import 'package:flutter/material.dart';

import '../services/backend_status_service.dart';
import '../theme/jack_theme.dart';
import 'jack_primitives.dart';

String backendStatusText(BackendConnectionState state) => switch (state) {
  BackendConnectionState.loading => 'Backend · verifica',
  BackendConnectionState.connected => 'Backend · connesso',
  BackendConnectionState.disconnected => 'Backend · offline',
};

String backendStatusShortText(BackendConnectionState state) => switch (state) {
  BackendConnectionState.loading => 'Verifica',
  BackendConnectionState.connected => 'Connesso',
  BackendConnectionState.disconnected => 'Offline',
};

Color backendStatusColor(BackendConnectionState state) => switch (state) {
  BackendConnectionState.loading => JackPalette.amber,
  BackendConnectionState.connected => JackPalette.green,
  BackendConnectionState.disconnected => JackPalette.muted,
};

class BackendStatusIndicator extends StatelessWidget {
  const BackendStatusIndicator({
    required this.state,
    required this.version,
    required this.onRetry,
    super.key,
  });

  final BackendConnectionState state;
  final String? version;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final color = backendStatusColor(state);
    final versionLabel = version ?? 'sconosciuta';
    final detail = switch (state) {
      BackendConnectionState.loading => 'Controllo il backend locale…',
      BackendConnectionState.connected =>
        'Backend locale attivo · v$versionLabel',
      BackendConnectionState.disconnected =>
        'Backend offline. Premi per riprovare.',
    };

    return Tooltip(
      message: detail,
      child: Material(
        color: JackPalette.panelRaised,
        shape: StadiumBorder(
          side: BorderSide(color: JackPalette.border.withValues(alpha: 0.9)),
        ),
        child: InkWell(
          onTap: onRetry,
          customBorder: const StadiumBorder(),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 8),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (state == BackendConnectionState.loading)
                  SizedBox(
                    width: 11,
                    height: 11,
                    child: CircularProgressIndicator(
                      strokeWidth: 1.5,
                      color: color,
                    ),
                  )
                else
                  StatusDot(color: color, size: 6),
                const SizedBox(width: 7),
                Text(
                  backendStatusText(state),
                  style: TextStyle(color: color, fontSize: 9),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
