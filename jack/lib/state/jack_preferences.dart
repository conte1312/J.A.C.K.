/// Local user preferences for J.A.C.K. 2.0.
///
/// Preferences are stored on this Mac with `shared_preferences`. No data is
/// sent anywhere. Tests can construct an instance without a store, in which
/// case values live only for the lifetime of the object.
library;

import 'package:flutter/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Observable local preferences.
class JackPreferences extends ChangeNotifier {
  JackPreferences({
    SharedPreferences? store,
    bool reduceMotion = false,
    String profileName = defaultProfileName,
    String profileRole = defaultProfileRole,
  }) : _store = store,
       _reduceMotion = reduceMotion,
       _profileName = profileName,
       _profileRole = profileRole;

  static const String defaultProfileName = 'Utente locale';
  static const String defaultProfileRole = 'Profilo locale';

  static const String _reduceMotionKey = 'jack.reduce_motion';
  static const String _profileNameKey = 'jack.profile_name';
  static const String _profileRoleKey = 'jack.profile_role';

  final SharedPreferences? _store;
  bool _reduceMotion;
  String _profileName;
  String _profileRole;

  bool get reduceMotion => _reduceMotion;
  String get profileName => _profileName;
  String get profileRole => _profileRole;

  /// Loads persisted preferences, falling back to defaults if the platform
  /// store is unavailable.
  static Future<JackPreferences> load() async {
    try {
      final store = await SharedPreferences.getInstance();
      return JackPreferences(
        store: store,
        reduceMotion: store.getBool(_reduceMotionKey) ?? false,
        profileName: store.getString(_profileNameKey) ?? defaultProfileName,
        profileRole: store.getString(_profileRoleKey) ?? defaultProfileRole,
      );
    } catch (_) {
      return JackPreferences();
    }
  }

  void setReduceMotion(bool value) {
    if (_reduceMotion == value) {
      return;
    }
    _reduceMotion = value;
    _store?.setBool(_reduceMotionKey, value);
    notifyListeners();
  }

  void setProfileName(String value) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || trimmed == _profileName) {
      return;
    }
    _profileName = trimmed;
    _store?.setString(_profileNameKey, trimmed);
    notifyListeners();
  }

  void setProfileRole(String value) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || trimmed == _profileRole) {
      return;
    }
    _profileRole = trimmed;
    _store?.setString(_profileRoleKey, trimmed);
    notifyListeners();
  }

  void reset() {
    _reduceMotion = false;
    _profileName = defaultProfileName;
    _profileRole = defaultProfileRole;
    _store?.remove(_reduceMotionKey);
    _store?.remove(_profileNameKey);
    _store?.remove(_profileRoleKey);
    notifyListeners();
  }

  /// Initials used by the avatar.
  String get initials {
    final words = _profileName
        .split(RegExp(r'\s+'))
        .where((word) => word.isNotEmpty)
        .toList();
    if (words.isEmpty) {
      return 'J';
    }
    if (words.length == 1) {
      return words.first.length > 1 ? words.first.substring(0, 2) : words.first;
    }
    return '${words.first[0]}${words.last[0]}';
  }
}

/// Provides [JackPreferences] to the widget tree.
class JackPreferencesScope extends InheritedNotifier<JackPreferences> {
  const JackPreferencesScope({
    super.key,
    required JackPreferences preferences,
    required super.child,
  }) : super(notifier: preferences);

  static JackPreferences of(BuildContext context) {
    final scope = context
        .dependOnInheritedWidgetOfExactType<JackPreferencesScope>();
    assert(scope != null, 'JackPreferencesScope is missing above this widget.');
    return scope!.notifier!;
  }
}
