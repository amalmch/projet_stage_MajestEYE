import 'dart:io';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/theme/app_theme.dart';
import '../models/message_model.dart';

final _arabicCharRegExp = RegExp(r'[\u0600-\u06FF]');

class ChatBubble extends StatelessWidget {
  final MessageModel message;

  const ChatBubble({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    final isUser = message.sender == MessageSender.user;
    final isArabic = _arabicCharRegExp.hasMatch(message.text);

    final bubbleColor = message.isError
        ? AppTheme.error.withOpacity(0.1)
        : (isUser ? AppTheme.primary : Colors.white);
        
    final textColor = message.isError
        ? AppTheme.error
        : Colors.black;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser) ...[
            // Bot Avatar
            Container(
              width: 32,
              height: 32,
              decoration: const BoxDecoration(
                color: AppTheme.primaryLight,
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.water_drop_rounded,
                color: Colors.white,
                size: 18,
              ),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.75,
              ),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: bubbleColor,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(AppTheme.radiusLg),
                  topRight: const Radius.circular(AppTheme.radiusLg),
                  bottomLeft: Radius.circular(isUser ? AppTheme.radiusLg : 4),
                  bottomRight: Radius.circular(isUser ? 4 : AppTheme.radiusLg),
                ),
                boxShadow: isUser ? [] : AppTheme.softShadow,
                border: message.isError
                    ? Border.all(color: AppTheme.error.withOpacity(0.3))
                    : null,
              ),
              child: Column(
                crossAxisAlignment:
                    isArabic ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                children: [
                  if (message.imagePath != null) ...[
                    ClipRRect(
                      borderRadius: BorderRadius.circular(10),
                      child: kIsWeb
                          ? Image.network(
                              message.imagePath!,
                              height: 160,
                              width: double.infinity,
                              fit: BoxFit.cover,
                            )
                          : Image.file(
                              File(message.imagePath!),
                              height: 160,
                              width: double.infinity,
                              fit: BoxFit.cover,
                            ),
                    ),
                    if (message.text.isNotEmpty) const SizedBox(height: 8),
                  ],
                  if (message.text.isNotEmpty)
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (message.isError) ...[
                          Icon(Icons.error_outline,
                              size: 16, color: AppTheme.error),
                          const SizedBox(width: 6),
                        ],
                        Flexible(
                          child: Text(
                            message.text,
                            textDirection:
                                isArabic ? TextDirection.rtl : TextDirection.ltr,
                            textAlign: isArabic ? TextAlign.right : TextAlign.left,
                            style: GoogleFonts.inter(
                              color: textColor,
                              height: 1.4,
                              fontSize: 15,
                            ),
                          ),
                        ),
                      ],
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
