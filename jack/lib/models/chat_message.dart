enum MessageAuthor { user, jack }

class ChatMessage {
  const ChatMessage({
    required this.text,
    required this.author,
    required this.time,
  });

  final String text;
  final MessageAuthor author;
  final String time;

  bool get isUser => author == MessageAuthor.user;
}
