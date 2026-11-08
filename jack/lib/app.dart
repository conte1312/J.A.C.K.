import 'package:flutter/material.dart';

import 'screens/jack_home_page.dart';
import 'services/ai_provider_service.dart';
import 'services/backend_status_service.dart';
import 'services/conversation_api_service.dart';
import 'services/memory_api_service.dart';
import 'theme/jack_theme.dart';

class JackApp extends StatelessWidget {
  const JackApp({
    this.backendStatusReader,
    this.memoryRepository,
    this.aiProviderGateway,
    this.conversationRepository,
    super.key,
  });

  final BackendStatusReader? backendStatusReader;
  final MemoryRepository? memoryRepository;
  final AiProviderGateway? aiProviderGateway;
  final ConversationRepository? conversationRepository;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'J.A.C.K.',
      debugShowCheckedModeBanner: false,
      theme: JackTheme.dark,
      home: JackHomePage(
        backendStatusReader: backendStatusReader,
        memoryRepository: memoryRepository,
        aiProviderGateway: aiProviderGateway,
        conversationRepository: conversationRepository ??
            ConversationApiService(),
      ),
    );
  }
}
