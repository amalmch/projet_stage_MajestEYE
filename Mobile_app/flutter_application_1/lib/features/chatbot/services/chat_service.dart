import 'dart:convert';
import 'package:http/http.dart' as http;

import '../../../core/config/api_config.dart';

/// Réponse renvoyée par POST /chat sur le backend Flask.
class ChatResponse {
  final String reply;
  final String sessionId;
  final String state;
  final bool done;
  final String? idPlainte;
  final String? categorie;
  final String? action;

  ChatResponse({
    required this.reply,
    required this.sessionId,
    required this.state,
    required this.done,
    this.idPlainte,
    this.categorie,
    this.action,
  });

  factory ChatResponse.fromJson(Map<String, dynamic> json) {
    return ChatResponse(
      reply: json['reply'] as String? ?? '',
      sessionId: json['session_id'] as String? ?? '',
      state: json['state'] as String? ?? '',
      done: json['done'] as bool? ?? false,
      idPlainte: json['id_plainte'] as String?,
      categorie: json['categorie'] as String?,
      action: json['action'] as String?,
    );
  }
}

/// Exception levée quand le backend est injoignable ou renvoie une erreur.
class ChatServiceException implements Exception {
  final String message;
  ChatServiceException(this.message);

  @override
  String toString() => message;
}

/// A lightweight summary of a past conversation for the history sidebar.
class ConversationSummary {
  final String sessionId;
  final String title;
  final String? state;
  final DateTime? updatedAt;

  ConversationSummary({
    required this.sessionId,
    required this.title,
    this.state,
    this.updatedAt,
  });

  factory ConversationSummary.fromJson(Map<String, dynamic> json) {
    DateTime? updated;
    if (json['updated_at'] != null) {
      try {
        updated = DateTime.parse(json['updated_at'] as String);
      } catch (_) {
        // MongoDB ISODate may come as a map via $date
        if (json['updated_at'] is Map && json['updated_at']['\$date'] != null) {
          updated = DateTime.tryParse(json['updated_at']['\$date'].toString());
        }
      }
    }
    return ConversationSummary(
      sessionId: json['session_id'] as String? ?? '',
      title: json['title'] as String? ?? 'Conversation',
      state: json['state'] as String?,
      updatedAt: updated,
    );
  }
}

class ChatService {
  /// Envoie un message utilisateur au chatbot et retourne sa réponse.
  Future<ChatResponse> sendMessage({
    required String sessionId,
    required String message,
    String? imageBase64,
    String? audioBase64,
    String? userId,
    double? latitude,
    double? longitude,
  }) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/chat');

    final body = <String, dynamic>{
      'session_id': sessionId,
      'message': message,
      if (userId != null) 'user_id': userId,
      if (imageBase64 != null) 'image_base64': imageBase64,
      if (audioBase64 != null) 'audio_base64': audioBase64,
      if (latitude != null && longitude != null) 'location': {'lat': latitude, 'lng': longitude},
    };

    http.Response response;
    try {
      response = await http
          .post(
            uri,
            headers: {'Content-Type': 'application/json; charset=utf-8'},
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 30));
    } catch (e) {
      throw ChatServiceException(
        'Impossible de contacter le serveur. Vérifiez que le backend '
        'tourne bien sur ${ApiConfig.baseUrl} et que votre appareil est '
        'sur le même réseau.',
      );
    }

    if (response.statusCode != 200) {
      throw ChatServiceException(
        'Le serveur a répondu avec une erreur (${response.statusCode}).',
      );
    }

    try {
      final decoded = jsonDecode(utf8.decode(response.bodyBytes))
          as Map<String, dynamic>;
      return ChatResponse.fromJson(decoded);
    } catch (e) {
      throw ChatServiceException('Réponse du serveur illisible.');
    }
  }

  /// Fetches all past conversations for a given user (for the history sidebar).
  Future<List<ConversationSummary>> fetchUserConversations(String userId) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/users/$userId/conversations');
    http.Response response;
    try {
      response = await http.get(uri).timeout(const Duration(seconds: 15));
    } catch (e) {
      throw ChatServiceException('Impossible de charger l\'historique.');
    }
    if (response.statusCode != 200) {
      throw ChatServiceException('Erreur serveur (${response.statusCode}).');
    }
    final decoded = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    final list = (decoded['conversations'] as List<dynamic>?) ?? [];
    return list
        .map((e) => ConversationSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Fetches the full message history for a specific conversation.
  Future<List<Map<String, String>>> fetchConversationHistory(String sessionId) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/conversations/$sessionId');
    http.Response response;
    try {
      response = await http.get(uri).timeout(const Duration(seconds: 15));
    } catch (e) {
      throw ChatServiceException('Impossible de charger la conversation.');
    }
    if (response.statusCode != 200) {
      throw ChatServiceException('Conversation introuvable.');
    }
    final decoded = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    final history = (decoded['history'] as List<dynamic>?) ?? [];
    return history.map((item) {
      final m = item as Map<String, dynamic>;
      return {
        'role': (m['role'] ?? 'user').toString(),
        'text': (m['text'] ?? '').toString(),
      };
    }).toList();
  }

  /// Deletes a conversation from the user's history.
  Future<void> deleteConversation(String sessionId) async {
    final uri = Uri.parse('${ApiConfig.baseUrl}/conversations/$sessionId');
    try {
      await http.delete(uri).timeout(const Duration(seconds: 10));
    } catch (_) {
      // Silently fail — not critical
    }
  }
}
