import 'package:flutter/material.dart';

import '../state/jack_preferences.dart';
import '../theme/jack_theme.dart';
import '../widgets/jack_primitives.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  JackPreferences? _preferences;
  bool _loading = true;
  String? _error;
  final _nameController = TextEditingController();
  final _roleController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _roleController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final preferences = await JackPreferences.load();
      if (!mounted) return;
      _nameController.text = preferences.profileName;
      _roleController.text = preferences.profileRole;
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

  Future<void> _save() async {
    if (_preferences == null) return;
    setState(() => _loading = true);
    try {
      _preferences!.setProfileName(_nameController.text.trim());
      _preferences!.setProfileRole(_roleController.text.trim());
      if (!mounted) return;
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Profilo salvato.'),
          backgroundColor: JackPalette.green,
          duration: const Duration(seconds: 2),
        ),
      );
    } on Exception catch (error) {
      if (!mounted) return;
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Errore salvataggio: $error'),
          backgroundColor: JackPalette.red,
          duration: const Duration(seconds: 4),
        ),
      );
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
                    const SectionEyebrow('Profilo e Account'),
                    const SizedBox(height: 12),
                    Text(
                      'Preferenze personali',
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
                            'Nome',
                            style: TextStyle(
                              color: JackPalette.muted,
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 1.2,
                            ),
                          ),
                          const SizedBox(height: 8),
                          TextField(
                            controller: _nameController,
                            decoration: const InputDecoration(
                              hintText: 'Il tuo nome',
                              isDense: true,
                            ),
                            style: const TextStyle(
                              color: JackPalette.text,
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Ruolo',
                            style: TextStyle(
                              color: JackPalette.muted,
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 1.2,
                            ),
                          ),
                          const SizedBox(height: 8),
                          TextField(
                            controller: _roleController,
                            decoration: const InputDecoration(
                              hintText: 'Ruolo o descrizione',
                              isDense: true,
                            ),
                            style: const TextStyle(
                              color: JackPalette.text,
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 20),
                          Text(
                            'Iniziali avatar: ${_preferences?.initials ?? 'J'}',
                            style: TextStyle(
                              color: JackPalette.muted,
                              fontSize: 13,
                            ),
                          ),
                          const SizedBox(height: 16),
                          FilledButton.icon(
                            onPressed: _loading ? null : _save,
                            icon: const Icon(Icons.save, size: 16),
                            label: const Text('Salva modifiche'),
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
