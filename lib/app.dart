import 'package:flutter/material.dart';

import 'screens/jack_home_page.dart';
import 'theme/jack_theme.dart';

class JackApp extends StatelessWidget {
  const JackApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'J.A.C.K.',
      debugShowCheckedModeBanner: false,
      theme: JackTheme.dark,
      home: const JackHomePage(),
    );
  }
}
