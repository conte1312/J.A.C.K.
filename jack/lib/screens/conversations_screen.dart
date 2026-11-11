import 'package:flutter/material.dart';

/// Conversazioni — placeholder shell (implementato in M2, dati demo).
class ConversationsScreen extends StatefulWidget {
  const ConversationsScreen({super.key});
  @override
  State<ConversationsScreen> createState() => _ConversationsScreenState;
}

class _ConversationsScreenState extends State<ConversationsScreen> {
  @override
  Widget build(BuildContext context) => const Scaffold(
    body: Center(child: Text('Conversazioni M2 - Demo conversations'))
  );
