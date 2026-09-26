import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/theme/app_theme.dart';
import '../models/message_model.dart';
import '../services/chat_service.dart';
import '../widgets/chat_bubble.dart';

class ChatHistoryScreen extends StatefulWidget {
  final String userId;
  const ChatHistoryScreen({super.key, required this.userId});

  @override
  State<ChatHistoryScreen> createState() => _ChatHistoryScreenState();
}

class _ChatHistoryScreenState extends State<ChatHistoryScreen> {
  final ChatService _chatService = ChatService();
  List<ConversationSummary> _conversations = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadConversations();
  }

  Future<void> _loadConversations() async {
    try {
      setState(() {
        _isLoading = true;
        _error = null;
      });
      final convs = await _chatService.fetchUserConversations(widget.userId);
      if (mounted) {
        setState(() {
          _conversations = convs;
          _isLoading = false;
        });
      }
    } on ChatServiceException catch (e) {
      if (mounted) {
        setState(() {
          _error = e.message;
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _deleteConversation(String sessionId) async {
    try {
      await _chatService.deleteConversation(sessionId);
      setState(() {
        _conversations.removeWhere((c) => c.sessionId == sessionId);
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Conversation supprimée')),
        );
      }
    } on ChatServiceException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erreur: ${e.message}')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Historique des conversations'),
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 48, color: AppTheme.error),
            const SizedBox(height: 16),
            Text(
              'Erreur: $_error',
              style: GoogleFonts.inter(color: AppTheme.error),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadConversations,
              child: const Text('Réessayer'),
            ),
          ],
        ),
      );
    }
    if (_conversations.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.chat_bubble_outline, size: 64, color: Colors.grey.shade400),
            const SizedBox(height: 16),
            Text(
              'Aucune conversation trouvée',
              style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 16),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadConversations,
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: _conversations.length,
        separatorBuilder: (context, index) => const SizedBox(height: 12),
        itemBuilder: (context, index) {
          final conv = _conversations[index];
          final title = conv.title.isNotEmpty ? conv.title : 'Nouvelle conversation';
          final sessionId = conv.sessionId;
          final date = conv.updatedAt;

          return Card(
            child: ListTile(
              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              leading: Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppTheme.surface,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.forum_outlined, color: AppTheme.primaryLight),
              ),
              title: Text(
                title,
                style: GoogleFonts.poppins(fontWeight: FontWeight.w500, fontSize: 15),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              subtitle: date != null
                  ? Text(
                      'Dernière activité: ${date.day}/${date.month}/${date.year} ${date.hour}:${date.minute.toString().padLeft(2, '0')}',
                      style: GoogleFonts.inter(fontSize: 12),
                    )
                  : null,
              trailing: IconButton(
                icon: const Icon(Icons.delete_outline, color: AppTheme.error),
                onPressed: () => _confirmDelete(context, sessionId),
              ),
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => ChatHistoryDetailScreen(
                      sessionId: sessionId,
                      title: title,
                    ),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }

  Future<void> _confirmDelete(BuildContext context, String sessionId) async {
    final bool? confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Supprimer', style: GoogleFonts.poppins(fontWeight: FontWeight.bold)),
        content: Text(
          'Voulez-vous vraiment supprimer cette conversation ?',
          style: GoogleFonts.inter(),
        ),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppTheme.radiusMd)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Annuler'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.error),
            child: const Text('Supprimer'),
          ),
        ],
      ),
    );

    if (confirm == true) {
      _deleteConversation(sessionId);
    }
  }
}

class ChatHistoryDetailScreen extends StatefulWidget {
  final String sessionId;
  final String title;

  const ChatHistoryDetailScreen({
    super.key,
    required this.sessionId,
    required this.title,
  });

  @override
  State<ChatHistoryDetailScreen> createState() => _ChatHistoryDetailScreenState();
}

class _ChatHistoryDetailScreenState extends State<ChatHistoryDetailScreen> {
  final ChatService _chatService = ChatService();
  List<MessageModel> _messages = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    try {
      final history = await _chatService.fetchConversationHistory(widget.sessionId);
      final List<MessageModel> messages = history.map((msg) {
        final isUser = msg['role'] == 'user';
        return MessageModel(
          text: msg['text'] ?? '',
          sender: isUser ? MessageSender.user : MessageSender.bot,
        );
      }).toList();
      if (mounted) setState(() => _messages = messages);
    } on ChatServiceException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.title,
          style: const TextStyle(fontSize: 16),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Text(
          'Erreur: $_error',
          style: GoogleFonts.inter(color: AppTheme.error),
        ),
      );
    }
    if (_messages.isEmpty) {
      return const Center(child: Text('La conversation est vide.'));
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(vertical: 16),
      itemCount: _messages.length,
      itemBuilder: (context, index) {
        return ChatBubble(message: _messages[index]);
      },
    );
  }
}
