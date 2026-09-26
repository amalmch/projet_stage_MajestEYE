import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../models/complaint_model.dart';
import '../models/complaint_status.dart';
import '../../../core/config/api_config.dart';

class ComplaintProvider extends ChangeNotifier {
  bool _isLoading = false;
  bool _isSubmitting = false;
  String? _errorMessage;

  List<ComplaintModel> _complaints = [];

  bool get isLoading => _isLoading;
  bool get isSubmitting => _isSubmitting;
  String? get errorMessage => _errorMessage;

  // Plaintes les plus récentes en premier.
  List<ComplaintModel> get complaints => List.unmodifiable(_complaints);

  ComplaintModel? getById(String id) {
    try {
      return _complaints.firstWhere((c) => c.id == id);
    } catch (_) {
      return null;
    }
  }

  Future<void> fetchUserComplaints(String userEmail) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final uri = Uri.parse('${ApiConfig.baseUrl}/complaints?user_email=${Uri.encodeQueryComponent(userEmail)}');
      final response = await http.get(uri);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final List<dynamic> results = data['results'] ?? [];
        
        _complaints = results.map<ComplaintModel>((json) {
          final statusStr = json['statut'] ?? 'nouveau';
          final status = ComplaintStatus.values.firstWhere(
            (e) => e.name == statusStr,
            orElse: () => ComplaintStatus.recue,
          );

          List<StatusEvent> history = [];
          if (json['historique_statuts'] != null) {
            for (var ev in json['historique_statuts']) {
              final evStatusStr = ev['statut'] ?? 'recue';
              final evStatus = ComplaintStatus.values.firstWhere(
                (e) => e.name == evStatusStr,
                orElse: () => ComplaintStatus.recue,
              );
              final evDate = DateTime.tryParse(ev['horodatage'] ?? '') ?? DateTime.now();
              history.add(StatusEvent(status: evStatus, date: evDate));
            }
          }

          return ComplaintModel(
            id: json['id_plainte'] ?? '',
            categorie: json['categorie'] ?? 'autre',
            texte: json['texte_plainte'] ?? json['description'] ?? '',
            dateCreation: DateTime.tryParse(json['date_signalement'] ?? '') ?? DateTime.now(),
            status: status,
            statusHistory: history.isNotEmpty ? history : null,
          );
        }).toList();
      } else {
        _errorMessage = 'Failed to load complaints';
      }
    } catch (e) {
      _errorMessage = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> submitComplaint(ComplaintModel complaint) async {
    _isSubmitting = true;
    _errorMessage = null;
    notifyListeners();

    try {
      // NOTE : simulation en attendant le vrai endpoint POST /api/complaints
      await Future.delayed(const Duration(seconds: 1));
      print('Plainte envoyée : ${complaint.toJson()}');

      _complaints.insert(0, complaint);
      _isSubmitting = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = "Échec de l'envoi. Réessayez.";
      _isSubmitting = false;
      notifyListeners();
      return false;
    }
  }

  void trackFromChat(ComplaintModel complaint) {
    if (getById(complaint.id) != null) return;
    _complaints.insert(0, complaint);
    notifyListeners();
  }

  void advanceStatus(String id) {
    final complaint = getById(id);
    if (complaint == null) return;

    final nextIndex = complaint.status.stepIndex + 1;
    if (nextIndex >= ComplaintStatus.values.length) return;

    final nextStatus = ComplaintStatus.values[nextIndex];
    complaint.status = nextStatus;
    complaint.statusHistory.add(StatusEvent(status: nextStatus, date: DateTime.now()));
    notifyListeners();
  }
}