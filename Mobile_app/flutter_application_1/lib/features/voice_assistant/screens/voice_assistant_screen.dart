import 'dart:convert';
import 'dart:io' show File;
import 'dart:math';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:provider/provider.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:http/http.dart' as http;

import '../../../core/theme/app_theme.dart';
import '../../auth/providers/auth_provider.dart';
import '../services/voice_assistant_service.dart';

class VoiceAssistantScreen extends StatefulWidget {
  const VoiceAssistantScreen({super.key});

  @override
  State<VoiceAssistantScreen> createState() => _VoiceAssistantScreenState();
}

class _VoiceAssistantScreenState extends State<VoiceAssistantScreen> with SingleTickerProviderStateMixin {
  final _voiceService = VoiceAssistantService();
  final _audioRecorder = AudioRecorder();
  final _audioPlayer = AudioPlayer();

  late final String _sessionId = _generateSessionId();

  bool _isRecording = false;
  bool _isProcessing = false;
  bool _isPlaying = false;
  String _statusMessage = 'Appuyez pour parler';

  // Animation for the central orb
  late AnimationController _orbAnimationController;

  @override
  void initState() {
    super.initState();
    _orbAnimationController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    _audioPlayer.onPlayerStateChanged.listen((state) {
      if (mounted) {
        setState(() {
          _isPlaying = state == PlayerState.playing;
          if (state == PlayerState.completed) {
            _statusMessage = 'Appuyez pour parler';
          } else if (state == PlayerState.playing) {
            _statusMessage = 'L\'IA vous répond...';
          }
        });
      }
    });
  }

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
    _audioRecorder.dispose();
    _audioPlayer.dispose();
    _orbAnimationController.dispose();
    super.dispose();
  }

  Future<void> _toggleRecording() async {
    if (_isPlaying) {
      await _audioPlayer.stop();
    }
    
    if (_isRecording) {
      await _stopRecordingAndSend();
    } else {
      await _startRecording();
    }
  }

  Future<void> _startRecording() async {
    try {
      if (await _audioRecorder.hasPermission()) {
        String path = '';
        if (!kIsWeb) {
          final tempDir = await getTemporaryDirectory();
          path = '${tempDir.path}/voice_assistant_${DateTime.now().millisecondsSinceEpoch}.wav';
        }
        // Use 16kHz PCM to prevent cutoff issues with Vosk
        await _audioRecorder.start(
          const RecordConfig(
            encoder: AudioEncoder.wav,
            sampleRate: 16000,
            numChannels: 1,
          ), 
          path: path
        );
        setState(() {
          _isRecording = true;
          _statusMessage = 'L\'IA écoute...';
        });
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Permission microphone refusée')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erreur: $e')),
        );
      }
    }
  }

  Future<void> _stopRecordingAndSend() async {
    try {
      final path = await _audioRecorder.stop();
      setState(() {
        _isRecording = false;
        _isProcessing = true;
        _statusMessage = 'Analyse en cours...';
      });

      if (path != null) {
        List<int> bytes;
        if (kIsWeb) {
          final response = await http.get(Uri.parse(path));
          bytes = response.bodyBytes;
        } else {
          final audioFile = File(path);
          if (await audioFile.exists()) {
            bytes = await audioFile.readAsBytes();
          } else {
            throw Exception('Fichier audio introuvable');
          }
        }
        final audioBase64 = base64Encode(bytes);
        await _sendToBackend(audioBase64);
      }
    } catch (e) {
      setState(() {
        _isProcessing = false;
        _statusMessage = 'Erreur d\'envoi';
      });
    }
  }

  Future<void> _sendToBackend(String audioBase64) async {
    final auth = context.read<AuthProvider>();
    final userId = auth.userEmail;

    try {
      final response = await _voiceService.sendVoiceMessage(
        sessionId: _sessionId,
        audioBase64: audioBase64,
        userId: userId,
      );

      setState(() {
        _isProcessing = false;
      });

      if (response.audioBase64.isNotEmpty) {
        final audioBytes = base64Decode(response.audioBase64);
        await _audioPlayer.play(BytesSource(audioBytes));
      } else {
        setState(() {
          _statusMessage = 'Appuyez pour parler';
        });
      }
      
    } catch (e) {
      setState(() {
        _isProcessing = false;
        _statusMessage = 'Erreur serveur';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    
    // Background colors matching the smooth, aesthetic vibe
    final bgColor = isDark ? const Color(0xFF1A1A2E) : const Color(0xFFE8F1F8);
    final orbCoreColor = isDark ? const Color(0xFF4A90E2) : const Color(0xFF5AB9EA);
    
    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_new, color: isDark ? Colors.white : Colors.black87),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: isDark ? Colors.white.withOpacity(0.1) : Colors.white,
            borderRadius: BorderRadius.circular(20),
            boxShadow: isDark ? [] : [
              BoxShadow(
                color: Colors.black.withOpacity(0.05),
                blurRadius: 10,
                offset: const Offset(0, 2),
              )
            ],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.graphic_eq, size: 16, color: isDark ? Colors.white : Colors.black87),
              const SizedBox(width: 8),
              Text(
                'Voice Chat',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: isDark ? Colors.white : Colors.black87,
                ),
              ),
            ],
          ),
        ),
        centerTitle: true,
        actions: [
          IconButton(
            icon: Icon(Icons.chat_bubble_outline, color: isDark ? Colors.white : Colors.black87),
            onPressed: () => Navigator.of(context).pop(), // Transition back to text chat
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Spacer(),
            
            // Central Orb
            Center(
              child: AnimatedBuilder(
                animation: _orbAnimationController,
                builder: (context, child) {
                  double scale = 1.0;
                  if (_isRecording || _isPlaying) {
                    scale = 1.0 + (_orbAnimationController.value * 0.15);
                  } else if (_isProcessing) {
                    scale = 0.9 + (_orbAnimationController.value * 0.05);
                  }

                  return Transform.scale(
                    scale: scale,
                    child: Container(
                      width: 200,
                      height: 200,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: RadialGradient(
                          colors: [
                            orbCoreColor.withOpacity(0.8),
                            orbCoreColor.withOpacity(0.3),
                            orbCoreColor.withOpacity(0.0),
                          ],
                          stops: const [0.4, 0.7, 1.0],
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: orbCoreColor.withOpacity(_isRecording || _isPlaying ? 0.4 : 0.1),
                            blurRadius: 40 * scale,
                            spreadRadius: 10 * scale,
                          )
                        ],
                      ),
                      child: Center(
                        child: Container(
                          width: 120,
                          height: 120,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [
                                Colors.white,
                                orbCoreColor,
                              ],
                            ),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.1),
                                blurRadius: 10,
                                offset: const Offset(0, 5),
                              )
                            ],
                          ),
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
            
            const SizedBox(height: 40),
            
            // Status Text
            Text(
              _statusMessage,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w500,
                color: isDark ? Colors.white70 : Colors.black54,
              ),
            ),
            
            const Spacer(),
            
            // Bottom Controls
            Padding(
              padding: const EdgeInsets.only(bottom: 40),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  // Volume/Mute placeholder
                  IconButton(
                    icon: Icon(Icons.volume_up_outlined, color: isDark ? Colors.white54 : Colors.black38, size: 28),
                    onPressed: () {
                       _audioPlayer.stop();
                    },
                  ),
                  
                  // Main Action Button
                  GestureDetector(
                    onTap: _toggleRecording,
                    child: Container(
                      width: 70,
                      height: 70,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.white,
                        border: Border.all(
                          color: _isRecording ? Colors.red : AppTheme.primary.withOpacity(0.3),
                          width: 2,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.05),
                            blurRadius: 10,
                            offset: const Offset(0, 5),
                          )
                        ],
                      ),
                      child: Icon(
                        _isRecording ? Icons.stop_rounded : Icons.mic_none_rounded,
                        color: _isRecording ? Colors.red : AppTheme.primary,
                        size: 32,
                      ),
                    ),
                  ),
                  
                  // Settings/Other placeholder
                  IconButton(
                    icon: Icon(Icons.public, color: isDark ? Colors.white54 : Colors.black38, size: 28),
                    onPressed: () {},
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
