enum MessageSender { user, bot }

class MessageModel {
  final String text;
  final MessageSender sender;

  final bool isError;
  final String? imagePath;

  MessageModel({
    required this.text,
    required this.sender,
    this.isError = false,
    this.imagePath,
  });
}
