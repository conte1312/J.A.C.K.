import 'package:flutter/material.dart';

import '../state/jack_preferences.dart';
import '../theme/jack_theme.dart';
import '../widgets/jack_primitives.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  JackPreferences? _preferences;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final preferences = await JackPreferences.load();
      if (!mounted) return;
      setState(() {
        _preferences = preferences;
        _loading = false;
      });
    } on Exception catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: JackPalette.canvas,
      body: SafeArea(
        child: _loading
            ? const Center(
                child: CircularProgressIndicator(color: JackPalette.amber),
              )
            : _error != null
            ? Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.error_outline,
                        color: JackPalette.red, size: 48),
                    const SizedBox(height: 12),
                    Text(_error!,
                        style: TextStyle(color: JackPalette.text),
                        textAlign: TextAlign.center),
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: _load,
                      icon: const Icon(Icons.refresh, size: 16),
                      label: const Text('Riprova'),
                    ),
                  ],
                ),
              )
            : SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SectionEyebrow('Impostazioni'),
                    const SizedBox(height: 12),
                    Text(
                      'Preferenze locali',
                      style: TextStyle(
                        color: JackPalette.text,
                        fontSize: 24,
                        fontWeight: FontWeight.w300,
                      ),
                    ),
                    const SizedBox(height: 24),
                    JackPanel(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Profilo',
                            style: TextStyle(
                              color: JackPalette.muted,
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 1.2,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            _preferences?.profileName ?? 'Utente locale',
                            style: const TextStyle(
                              color: JackPalette.text,
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _preferences?.profileRole ?? 'Profilo locale',
                            style: TextStyle(
                              color: JackPalette.muted,
                              fontSize: 13,
                            ),
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: _PreferenceTile(
                                  icon: Icons.reduce_capacity_rounded,
                                  title: 'Riduci movimento',
                                  subtitle: 'Animazioni più sobrie',
                                  value: _preferences?.reduceMotion ?? false,
                                  onChanged: (value) async {
                                    if (_preferences == null) return;
                                    _preferences!.setReduceMotion(value);
                                    if (mounted) setState(() {});
                                  },
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
      ),
    );
  }
}

class _PreferenceTile extends StatelessWidget {
  const _PreferenceTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: JackPalette.panelHover,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: JackPalette.border),
            ),
            child: Icon(icon, color: JackPalette.cyan, size: 20),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: const TextStyle(
                      color: JackPalette.text,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    )),
                const SizedBox(height: 2),
                Text(subtitle,
                    style: TextStyle(
                      color: JackPalette.muted,
                      fontSize: 12,
                    )),
              ],
            ),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
            activeThumbColor: JackPalette.amber,
          ),
        ],
      ),
    );
  }
}
