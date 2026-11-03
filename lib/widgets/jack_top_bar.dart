import 'package:flutter/material.dart';

import '../theme/jack_theme.dart';

class JackTopBar extends StatelessWidget {
  const JackTopBar({
    required this.isListening,
    required this.onToggleListening,
    required this.onExplore,
    required this.onSettings,
    required this.onProfile,
    required this.showIdentity,
    super.key,
  });

  final bool isListening;
  final VoidCallback onToggleListening;
  final VoidCallback onExplore;
  final VoidCallback onSettings;
  final VoidCallback onProfile;
  final bool showIdentity;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 58,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24),
        child: Row(
          children: [
            const _JackIdentity(),
            const Spacer(),
            _ListeningStatus(
              isListening: isListening,
              onTap: onToggleListening,
            ),
            const Spacer(),
            IconButton(
              tooltip: 'Esplorazione',
              onPressed: onExplore,
              icon: const Icon(Icons.explore_outlined, size: 17),
              color: JackPalette.muted,
            ),
            IconButton(
              tooltip: 'Impostazioni',
              onPressed: onSettings,
              icon: const Icon(Icons.tune_rounded, size: 17),
              color: JackPalette.muted,
            ),
            if (showIdentity) ...[
              const SizedBox(width: 10),
              Container(width: 1, height: 24, color: JackPalette.border),
              const SizedBox(width: 16),
              const Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    'Francesco Conte',
                    style: TextStyle(fontSize: 11, color: JackPalette.text),
                  ),
                  SizedBox(height: 2),
                  Text(
                    'LOCALE · PRIVATO',
                    style: TextStyle(
                      fontSize: 8,
                      color: JackPalette.dim,
                      letterSpacing: 1.2,
                    ),
                  ),
                ],
              ),
              const SizedBox(width: 10),
              const CircleAvatar(
                radius: 15,
                backgroundColor: JackPalette.panelRaised,
                child: Text(
                  'FC',
                  style: TextStyle(fontSize: 9, color: JackPalette.muted),
                ),
              ),
            ],
            const SizedBox(width: 12),
            IconButton(
              tooltip: 'Profilo locale dimostrativo',
              onPressed: onProfile,
              icon: const Icon(Icons.logout_rounded, size: 15),
              color: JackPalette.dim,
            ),
          ],
        ),
      ),
    );
  }
}

class _JackIdentity extends StatelessWidget {
  const _JackIdentity();

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 38,
          height: 38,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: JackPalette.amber.withValues(alpha: 0.4)),
            boxShadow: [
              BoxShadow(
                color: JackPalette.amber.withValues(alpha: 0.08),
                blurRadius: 18,
              ),
            ],
          ),
          child: Center(
            child: Container(
              width: 17,
              height: 17,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: JackPalette.amber,
                border: Border.all(
                  color: JackPalette.amber.withValues(alpha: 0.35),
                  width: 5,
                ),
                boxShadow: [
                  BoxShadow(
                    color: JackPalette.amber.withValues(alpha: 0.45),
                    blurRadius: 12,
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(width: 13),
        const Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'J.A.C.K.',
              style: TextStyle(
                color: JackPalette.text,
                fontSize: 13,
                letterSpacing: 3,
                fontWeight: FontWeight.w400,
              ),
            ),
            SizedBox(height: 3),
            Text(
              'JUST ANOTHER CHILL KERNEL',
              style: TextStyle(
                color: JackPalette.dim,
                fontSize: 8,
                letterSpacing: 1.7,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _ListeningStatus extends StatelessWidget {
  const _ListeningStatus({required this.isListening, required this.onTap});

  final bool isListening;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: 'Stato dimostrativo: nessun microfono è collegato',
      child: Material(
        color: JackPalette.panelRaised,
        shape: StadiumBorder(
          side: BorderSide(color: JackPalette.border.withValues(alpha: 0.9)),
        ),
        child: InkWell(
          onTap: onTap,
          customBorder: const StadiumBorder(),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  isListening
                      ? Icons.graphic_eq_rounded
                      : Icons.mic_none_rounded,
                  size: 13,
                  color: JackPalette.amber,
                ),
                const SizedBox(width: 9),
                Text(
                  isListening ? 'In ascolto · demo' : 'In attesa · demo',
                  style: const TextStyle(color: JackPalette.text, fontSize: 10),
                ),
                const SizedBox(width: 9),
                _WaveMark(active: isListening),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _WaveMark extends StatelessWidget {
  const _WaveMark({required this.active});

  final bool active;

  @override
  Widget build(BuildContext context) {
    const heights = [7.0, 12.0, 9.0, 14.0, 6.0];
    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        for (final height in heights)
          Container(
            width: 2,
            height: active ? height : height * 0.72,
            margin: const EdgeInsets.symmetric(horizontal: 1),
            decoration: BoxDecoration(
              color: JackPalette.amber.withValues(alpha: active ? 0.72 : 0.42),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
      ],
    );
  }
}
