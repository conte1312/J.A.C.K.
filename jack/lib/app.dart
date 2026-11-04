import 'package:flutter/material.dart';

import 'screens/jack_home_page.dart';
import 'services/ai_hub_demo_repository.dart';
import 'services/backend_status_service.dart';
import 'services/memory_api_service.dart';
import 'theme/jack_theme.dart';

class JackApp extends StatelessWidget {
  const JackApp({
    this.backendStatusReader,
    this.aiHubRepository,
    this.memoryRepository,
    super.key,
  });

  final BackendStatusReader? backendStatusReader;
  final AiHubDemoRepository? aiHubRepository;
  final MemoryRepository? memoryRepository;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'J.A.C.K.',
      debugShowCheckedModeBanner: false,
      theme: JackTheme.dark,
      home: JackHomePage(
        backendStatusReader: backendStatusReader,
        aiHubRepository: aiHubRepository,
        memoryRepository: memoryRepository,
      ),
    );
  }
}
