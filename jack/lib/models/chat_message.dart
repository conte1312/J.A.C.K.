enum MessageAuthor { user, jack }

class ChatMessage {
  const ChatMessage({
    required this.text,
    required this.author,
    required this.time,
    this.id,
    this.createdAt,
    this.isDemo = false,
    this.providerLabel,
  });

  final String text;
  final MessageAuthor author;
  final String time;
  final String? id;
  final DateTime? createdAt;
  final bool isDemo;
  final String? providerLabel;

  bool get isUser => author == MessageAuthor.user;
}
