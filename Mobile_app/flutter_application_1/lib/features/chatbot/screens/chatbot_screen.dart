import 'dart:convert';
import 'dart:io' show File;
import 'dart:math';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';
import 'package:http/http.dart' as http;

import '../../../core/theme/app_theme.dart';
import '../../auth/providers/auth_provider.dart';
import '../../complaints/models/complaint_model.dart';
import '../../complaints/providers/complaint_provider.dart';
import '../models/message_model.dart';
import '../services/chat_service.dart';
import '../widgets/chat_bubble.dart';
import 'chat_history_screen.dart';
import '../../voice_assistant/screens/voice_assistant_screen.dart';

class ChatbotScreen extends StatefulWidget {
  const ChatbotScreen({super.key});

  @override
  State<ChatbotScreen> createState() => _ChatbotScreenState();
}

class _ChatbotScreenState extends State<ChatbotScreen> {
  final _textController = TextEditingController();
  final _scrollController = ScrollController();
  final _chatService = ChatService();
  final _imagePicker = ImagePicker();
  final _audioRecorder = AudioRecorder();

  final List<MessageModel> _messages = [
    MessageModel(
      text: 'Bonjour ! Décrivez-moi votre problème (coupure, fuite, '
          'qualité de l\'eau, facturation...). Vous pouvez aussi joindre '
          'une photo ou partager votre position avec les boutons ci-dessous.',
      sender: MessageSender.bot,
    ),
  ];

  late final String _sessionId = _generateSessionId();

  bool _isSending = false;
  bool _isLocating = false;
  bool _isRecording = false;
  bool _conversationDone = false;
  XFile? _pendingImage;

  String? _firstUserText;

  String _generateSessionId() {
    final rand = Random();
    final bytes = List<int>.generate(16, (_) => rand.nextInt(256));
    final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-'
        '${hex.substring(12, 16)}-${hex.substring(16, 20)}-'
        '${hex.substring(20, 32)}';
  }

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    _audioRecorder.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    });
  }

  Future<void> _pickImage(ImageSource source) async {
    final image = await _imagePicker.pickImage(source: source, imageQuality: 80);
    if (image == null) return;
    setState(() => _pendingImage = image);
  }

  void _showAttachSheet() {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Wrap(
            children: [
              ListTile(
                leading: const Icon(Icons.photo_library_outlined, color: AppTheme.primary),
                title: const Text('Choisir dans la galerie'),
                onTap: () {
                  Navigator.pop(context);
                  _pickImage(ImageSource.gallery);
                },
              ),
              ListTile(
                leading: const Icon(Icons.camera_alt_outlined, color: AppTheme.primary),
                title: const Text('Prendre une photo'),
                onTap: () {
                  Navigator.pop(context);
                  _pickImage(ImageSource.camera);
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _shareLocation() async {
    setState(() => _isLocating = true);
    try {
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        throw Exception('Le service de localisation est désactivé sur votre appareil.');
      }

      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          throw Exception('Permission de localisation refusée.');
        }
      }
      if (permission == LocationPermission.deniedForever) {
        throw Exception(
            'Permission refusée définitivement. Autorisez-la dans les paramètres de votre téléphone.');
      }

      final position = await Geolocator.getCurrentPosition();
      await _sendMessage(
        overrideText: 'Voici ma position actuelle.',
        latitude: position.latitude,
        longitude: position.longitude,
      );
    } catch (e) {
      setState(() {
        _messages.add(
          MessageModel(
            text: e.toString().replaceFirst('Exception: ', ''),
            sender: MessageSender.bot,
            isError: true,
          ),
        );
      });
      _scrollToBottom();
    } finally {
      if (mounted) setState(() => _isLocating = false);
    }
  }

  Future<void> _toggleRecording() async {
    try {
      if (_isRecording) {
        final path = await _audioRecorder.stop();
        setState(() => _isRecording = false);
        if (path != null) {
          List<int> bytes;
          if (kIsWeb) {
            // Sur le Web, path est une URL blob (blob:http://...)
            final response = await http.get(Uri.parse(path));
            bytes = response.bodyBytes;
          } else {
            final audioFile = File(path);
            if (await audioFile.exists()) {
              bytes = await audioFile.readAsBytes();
            } else {
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Erreur: Fichier audio introuvable')),
                );
              }
              return;
            }
          }
          final audioBase64 = base64Encode(bytes);
          await _sendMessage(audioBase64: audioBase64, overrideText: '🎤 Message vocal');
        }
      } else {
        if (await _audioRecorder.hasPermission()) {
          String path = '';
          if (!kIsWeb) {
            final tempDir = await getTemporaryDirectory();
            path = '${tempDir.path}/voice_message_${DateTime.now().millisecondsSinceEpoch}.wav';
          }
          await _audioRecorder.start(const RecordConfig(encoder: AudioEncoder.wav), path: path);
          setState(() => _isRecording = true);
        } else {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Permission microphone refusée')),
            );
          }
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erreur d\'enregistrement: $e')),
        );
      }
      setState(() => _isRecording = false);
    }
  }

  Future<void> _sendMessage({
    String? overrideText,
    String? audioBase64,
    double? latitude,
    double? longitude,
  }) async {
    final text = overrideText ?? _textController.text.trim();
    final image = _pendingImage;
    if (text.isEmpty && image == null && audioBase64 == null) return;
    if (_isSending) return;

    _firstUserText ??= text.isNotEmpty ? text : null;

    String? imagePath = image?.path;
    String? imageBase64;
    if (image != null) {
      final bytes = await image.readAsBytes();
      imageBase64 = base64Encode(bytes);
    }

    setState(() {
      _messages.add(MessageModel(
        text: text,
        sender: MessageSender.user,
        imagePath: imagePath,
      ));
      _isSending = true;
      _pendingImage = null;
    });
    _textController.clear();
    _scrollToBottom();

    final auth = context.read<AuthProvider>();
    final userId = auth.userEmail;
    try {
      final response = await _chatService.sendMessage(
        sessionId: _sessionId,
        message: text,
        imageBase64: imageBase64,
        audioBase64: audioBase64,
        userId: userId,
        latitude: latitude,
        longitude: longitude,
      );

      setState(() {
        _messages.add(
          MessageModel(text: response.reply, sender: MessageSender.bot),
        );
        _conversationDone = response.done;
      });

      if (response.action == 'REQUEST_GPS') {
        _shareLocation();
      }

      if (response.idPlainte != null && mounted) {
        context.read<ComplaintProvider>().trackFromChat(
              ComplaintModel(
                id: response.idPlainte!,
                categorie: response.categorie ?? 'Réclamation (assistant)',
                texte: _firstUserText ?? text,
                latitude: latitude,
                longitude: longitude,
                dateCreation: DateTime.now(),
                photoPath: imagePath,
              ),
            );
      }
    } on ChatServiceException catch (e) {
      setState(() {
        _messages.add(
          MessageModel(
            text: e.toString(),
            sender: MessageSender.bot,
            isError: true,
          ),
        );
      });
    } finally {
      if (mounted) setState(() => _isSending = false);
      _scrollToBottom();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.water_drop_rounded, size: 20),
            ),
            const SizedBox(width: 12),
            const Text('Assistant SONEDE'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.graphic_eq),
            tooltip: 'Assistant Vocal',
            onPressed: () {
              Navigator.of(context).push(
                PageRouteBuilder(
                  pageBuilder: (context, animation, secondaryAnimation) => const VoiceAssistantScreen(),
                  transitionsBuilder: (context, animation, secondaryAnimation, child) {
                    return FadeTransition(opacity: animation, child: child);
                  },
                ),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.add_comment_rounded),
            tooltip: 'Nouvelle discussion',
            onPressed: () {
              setState(() {
                _messages.clear();
                _messages.add(
                  MessageModel(
                    text: 'Bonjour ! Décrivez-moi votre problème (coupure, fuite, '
                        'qualité de l\'eau, facturation...). Vous pouvez aussi joindre '
                        'une photo ou partager votre position avec les boutons ci-dessous.',
                    sender: MessageSender.bot,
                  ),
                );
                _conversationDone = false;
                _pendingImage = null;
                _firstUserText = null;
              });
            },
          ),
          IconButton(
            icon: const Icon(Icons.history_rounded),
            tooltip: 'Historique des chats',
            onPressed: () {
              final auth = context.read<AuthProvider>();
              final userId = auth.userEmail ?? 'anonymous';
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => ChatHistoryScreen(userId: userId),
                ),
              );
            },
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.symmetric(vertical: 16),
              itemCount: _messages.length + (_isSending ? 1 : 0),
              itemBuilder: (context, index) {
                if (index == _messages.length) {
                  return const _TypingIndicator();
                }
                return ChatBubble(message: _messages[index]);
              },
            ),
          ),
          if (_conversationDone)
            Container(
              width: double.infinity,
              color: Colors.green.shade50,
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.check_circle_outline, color: Colors.green.shade800, size: 20),
                  const SizedBox(width: 8),
                  Text(
                    'Conversation terminée.',
                    style: TextStyle(color: Colors.green.shade800, fontWeight: FontWeight.w500),
                  ),
                ],
              ),
            ),
          if (_pendingImage != null)
            Container(
              margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                boxShadow: AppTheme.softShadow,
                border: Border.all(color: AppTheme.primaryLight.withOpacity(0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.image, size: 20, color: AppTheme.primaryLight),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Text(
                      'Photo jointe prête à être envoyée',
                      style: TextStyle(fontSize: 13, color: AppTheme.textPrimary),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, size: 20),
                    onPressed: () => setState(() => _pendingImage = null),
                    constraints: const BoxConstraints(),
                    padding: EdgeInsets.zero,
                  ),
                ],
              ),
            ),
          SafeArea(
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.05),
                    blurRadius: 10,
                    offset: const Offset(0, -2),
                  ),
                ],
              ),
              child: Row(
                children: [
                  IconButton(
                    tooltip: 'Joindre une photo',
                    onPressed: _isSending ? null : _showAttachSheet,
                    icon: const Icon(Icons.add_photo_alternate_outlined),
                    color: AppTheme.primaryLight,
                  ),
                  IconButton(
                    tooltip: 'Partager ma position',
                    onPressed: (_isSending || _isLocating) ? null : _shareLocation,
                    icon: _isLocating
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.location_on_outlined),
                    color: AppTheme.primaryLight,
                  ),
                  Expanded(
                    child: TextField(
                      controller: _textController,
                      enabled: !_isSending && !_isRecording,
                      style: const TextStyle(color: Colors.black),
                      textCapitalization: TextCapitalization.sentences,
                      onChanged: (val) => setState(() {}),
                      decoration: InputDecoration(
                        hintText: _isRecording ? 'Enregistrement en cours...' : 'Écrivez votre message...',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide.none,
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide.none,
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide.none,
                        ),
                        filled: true,
                        fillColor: AppTheme.background,
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 12,
                        ),
                      ),
                      onSubmitted: (_) => _sendMessage(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    decoration: BoxDecoration(
                      gradient: _isRecording ? null : AppTheme.primaryGradient,
                      color: _isRecording ? Colors.red : null,
                      shape: BoxShape.circle,
                    ),
                    child: IconButton(
                      onPressed: _isSending ? null : ((_textController.text.isNotEmpty || _pendingImage != null) ? () => _sendMessage() : _toggleRecording),
                      icon: _isSending
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : Icon(
                              (_textController.text.isNotEmpty || _pendingImage != null) ? Icons.send_rounded : (_isRecording ? Icons.stop_circle : Icons.mic),
                              color: Colors.white,
                              size: 20,
                            ),
                    ),
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

class _TypingIndicator extends StatefulWidget {
  const _TypingIndicator();

  @override
  State<_TypingIndicator> createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<_TypingIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 16, bottom: 16),
      child: Row(
        children: [
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
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: const BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(AppTheme.radiusLg),
                topRight: Radius.circular(AppTheme.radiusLg),
                bottomRight: Radius.circular(AppTheme.radiusLg),
                bottomLeft: Radius.circular(4),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(3, (index) {
                return AnimatedBuilder(
                  animation: _controller,
                  builder: (context, child) {
                    final delay = index * 0.2;
                    final value = (_controller.value - delay) % 1.0;
                    final offset = value < 0.5 ? Curves.easeOut.transform(value * 2) * -5 : 0.0;
                    return Transform.translate(
                      offset: Offset(0, offset),
                      child: Container(
                        margin: const EdgeInsets.symmetric(horizontal: 2),
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(
                          color: AppTheme.primaryLight.withOpacity(0.6),
                          shape: BoxShape.circle,
                        ),
                      ),
                    );
                  },
                );
              }),
            ),
          ),
        ],
      ),
    );
  }
}
