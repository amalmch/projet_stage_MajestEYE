import 'dart:convert';
import 'package:http/http.dart' as http;

import '../../../core/config/api_config.dart';

class VoiceAssistantResponse {
  final String sessionId;
  final String transcription;
  final String reply;
  final String audioBase64;
  final String state;
  final bool done;
  final String? idPlainte;

  VoiceAssistantResponse({
    required this.sessionId,
    required this.transcription,
    required this.reply,
    required this.audioBase64,
    required this.state,
    required this.done,
    this.idPlainte,
  });

  factory VoiceAssistantResponse.fromJson(Map<String, dynamic> json) {
    return VoiceAssistantResponse(
      sessionId: json['session_id'] as String? ?? '',
      transcription: json['transcription'] as String? ?? '',
      reply: json['reply'] as String? ?? '',
      audioBase64: json['audio_base64'] as String? ?? '',
      state: json['state'] as String? ?? '',
      done: json['done'] as bool? ?? false,
      idPlainte: json['id_plainte'] as String?,
    );
  }
}

class VoiceAssistantServiceException implements Exception {
  final String message;
  VoiceAssistantServiceException(this.message);

  @override
  String toString() => message;
}

class VoiceAssistantService {
  Future<VoiceAssistantResponse> sendVoiceMessage({
    required String sessionId,
    required String audioBase64,
    String? userId,
  }) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/voice_assistant');

    final body = <String, dynamic>{
      'session_id': sessionId,
      'audio_base64': audioBase64,
      if (userId != null) 'user_id': userId,
    };

    http.Response response;
    try {
      response = await http
          .post(
            uri,
            headers: {'Content-Type': 'application/json; charset=utf-8'},
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 45)); 
    } catch (e) {
      throw VoiceAssistantServiceException(
        'Impossible de contacter le serveur. Vérifiez la connexion réseau.',
      );
    }

    if (response.statusCode != 200) {
      throw VoiceAssistantServiceException(
        'Erreur serveur (${response.statusCode}).',
      );
    }

    try {
      final decoded = jsonDecode(utf8.decode(response.bodyBytes))
          as Map<String, dynamic>;
      if (decoded.containsKey('error')) {
        throw VoiceAssistantServiceException(decoded['error'].toString());
      }
      return VoiceAssistantResponse.fromJson(decoded);
    } catch (e) {
      if (e is VoiceAssistantServiceException) rethrow;
      throw VoiceAssistantServiceException('Réponse du serveur illisible.');
    }
  }
}
