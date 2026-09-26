import 'complaint_status.dart';

class StatusEvent {
  final ComplaintStatus status;
  final DateTime date;

  StatusEvent({required this.status, required this.date});
}

class ComplaintModel {
  final String id;
  final String categorie;
  final String texte;
  final double? latitude;
  final double? longitude;
  final DateTime dateCreation;
  final String? photoPath;

  ComplaintStatus status;
  final List<StatusEvent> statusHistory;

  ComplaintModel({
    required this.id,
    required this.categorie,
    required this.texte,
    this.latitude,
    this.longitude,
    required this.dateCreation,
    this.photoPath,
    this.status = ComplaintStatus.recue,
    List<StatusEvent>? statusHistory,
  }) : statusHistory = statusHistory ?? [StatusEvent(status: ComplaintStatus.recue, date: dateCreation)];

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'categorie': categorie,
      'texte': texte,
      'latitude': latitude,
      'longitude': longitude,
      'dateCreation': dateCreation.toIso8601String(),
      'hasPhoto': photoPath != null,
      'status': status.name,
    };
  }
}

typedef XFilePath = String;